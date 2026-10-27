"""Private signed downloads, including legacy TNG electronic signature records."""
import hashlib
import hmac
import io
import json
from pathlib import Path
from xml.sax.saxutils import escape

from fastapi import HTTPException, Response
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

from .models import BoxingContractSignature, BoxingSignedContractDocument


def signed_contract_response(db, contract):
    document = db.query(BoxingSignedContractDocument).filter_by(contract_id=contract.id).first()
    if document:
        content = bytes(document.file_data or b'')
        if not content.startswith(b'%PDF-'):
            raise HTTPException(409, 'The stored signed PDF is damaged. Restore or re-sync the original signed document.')
    else:
        signature = db.query(BoxingContractSignature).filter_by(contract_id=contract.id).first()
        if not signature:
            if contract.signature_provider == 'docusign':
                raise HTTPException(409, 'The signed DocuSign PDF is not stored yet. Check the DocuSign connection and sync this contract.')
            raise HTTPException(404, 'This contract has no saved signed document or electronic signature yet.')
        raw = signature.contract_snapshot or ''
        try:
            snapshot = json.loads(raw)
            valid = (isinstance(snapshot, dict) and signature.agreed
                     and bool((signature.typed_legal_name or '').strip())
                     and snapshot.get('contract_id') == contract.id
                     and snapshot.get('fighter_id') == signature.fighter_id == contract.fighter_id
                     and hmac.compare_digest(hashlib.sha256(raw.encode('utf-8')).hexdigest(), signature.snapshot_sha256 or ''))
        except (ValueError, TypeError):
            valid = False
        if not valid:
            raise HTTPException(409, 'The saved electronic signature could not be verified. Contact support; the original signing record has been preserved.')
        font = 'TNGSignedRecord'
        if font not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(font, str(Path(__file__).resolve().parents[1] / 'ticketing/assets/DejaVuSansCondensed.ttf')))
        styles = getSampleStyleSheet()
        for style in styles.byName.values():
            style.fontName = font
        def paragraph(value, style='BodyText'):
            return Paragraph(escape(str(value)).replace('\n', '<br/>'), styles[style])
        story = [paragraph('TNGOS Electronic Signature Record', 'Title'), Spacer(1, 12),
                 paragraph('This record reproduces the terms saved at signing and the recorded electronic signature. It is not a DocuSign completion certificate. Legacy records contain the saved terms below; no current or replacement clauses have been added.'), Spacer(1, 12)]
        for label, value in [('Contract', contract.id), ('Signed by', signature.typed_legal_name),
                             ('Signed at (UTC)', signature.signed_at), ('Agreement accepted', 'Yes'),
                             ('Template version', signature.template_version), ('Snapshot SHA-256', signature.snapshot_sha256)]:
            story.append(paragraph(f'{label}: {value}'))
        story.extend([Spacer(1, 14), paragraph('Terms saved at signing', 'Heading2')])
        for key, value in sorted(snapshot.items()):
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False, indent=2)
            story.append(paragraph(f'{key.replace("_", " ").title()}: {value if value is not None else "Not recorded"}'))
            story.append(Spacer(1, 5))
        output = io.BytesIO()
        SimpleDocTemplate(output, title=f'Contract {contract.id} electronic signature record').build(story)
        content = output.getvalue()
    return Response(content, media_type='application/pdf', headers={
        'Content-Disposition': f'attachment; filename="contract-{contract.id}-signed.pdf"',
        'Cache-Control': 'private, no-store, max-age=0', 'X-Content-Type-Options': 'nosniff'})
