"""Commission-workbook results, final judges' totals and review-only career records."""
import hashlib, io, json, re, zipfile
from datetime import datetime
from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from sqlalchemy import Column, Integer, String, Text, DateTime, LargeBinary, ForeignKey, UniqueConstraint
from app.database import Base, get_db
from app.core.dependencies import current_user, staff_user
from app.models import SecurityLog
from app.matchmaker.models import BoxingEvent, BoxingBout, BoxingFighter
from app.fighter_portal.models import FighterAccount
from .recap import CANCELLED, event_for
router = APIRouter(prefix='/api/events', tags=['Boxing results'])

class BoxingResultSource(Base):
    __tablename__ = 'boxing_result_sources'
    __table_args__ = (UniqueConstraint('event_id', 'sha256', name='uq_boxing_result_event_source'),)
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey('boxing_events.id'), nullable=False, index=True)
    filename = Column(String(200), nullable=False)
    sha256 = Column(String(64), nullable=False)
    content = Column(LargeBinary, nullable=False)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class BoxingBoutResult(Base):
    __tablename__ = 'boxing_bout_results'
    bout_id = Column(Integer, ForeignKey('boxing_bouts.id'), primary_key=True)
    event_id = Column(Integer, ForeignKey('boxing_events.id'), index=True, nullable=False)
    source_id = Column(Integer, ForeignKey('boxing_result_sources.id'), nullable=False)
    official_order = Column(Integer, nullable=False)
    winner_id = Column(Integer, ForeignKey('boxing_fighters.id'), nullable=False)
    red_fighter_id = Column(Integer, ForeignKey('boxing_fighters.id'), nullable=False)
    blue_fighter_id = Column(Integer, ForeignKey('boxing_fighters.id'), nullable=False)
    method = Column(String(20), nullable=False)
    round = Column(Integer, nullable=True)
    elapsed = Column(String(10), nullable=True)
    scores_json = Column(Text, nullable=False, default='[]')
    fighters_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

def record_tuple(value):
    text = str(value or '').strip().strip('.').lower()
    if text in ('debut', 'debutant'):
        return (0, 0, 0)
    m = re.fullmatch('(\\d+)\\s*-\\s*(\\d+)(?:\\s*-\\s*(\\d+))?', text)
    return (int(m[1]), int(m[2]), int(m[3] or 0)) if m else None

def parse_workbook(raw):
    if len(raw) > 2 * 1024 * 1024:
        raise HTTPException(413, 'Results workbook exceeds 2 MB')
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            if len(z.infolist()) > 200 or sum((i.file_size for i in z.infolist())) > 10 * 1024 * 1024:
                raise ValueError('Workbook is too large when expanded')
        from openpyxl import load_workbook
        book = load_workbook(io.BytesIO(raw), read_only=True, data_only=True, keep_links=False)
        try:
            sheet = book.worksheets[0]
            if 'OKLAHOMA STATE ATHLETIC COMMISSION' not in str(sheet['A1'].value).upper():
                raise ValueError('Expected Oklahoma commission boxing results workbook')
            rawdate = sheet['A9'].value
            event_date = rawdate.date().isoformat() if isinstance(rawdate, datetime) else datetime.strptime(str(rawdate).strip(), '%m.%d.%y').date().isoformat()
            judges = [str(sheet[f'L{i}'].value or '').strip() for i in (6, 7, 8)]
            grouped = {}
            for cells in sheet.iter_rows(min_row=14, max_row=min(sheet.max_row, 500), max_col=12, values_only=True):
                number = cells[0]
                if not isinstance(number, (int, float)) or not float(number).is_integer() or (not cells[2]) or (not cells[10]):
                    continue
                fid = re.search('\\d+', str(cells[5] or ''))
                if not fid:
                    raise ValueError('A fighter is missing the source ID required for exact matching')
                grouped.setdefault(int(number), []).append({'source_name': str(cells[2]).strip(), 'boxrec_id': fid[0], 'reported_record': str(cells[9] or '').strip(), 'outcome': str(cells[10]).strip().upper(), 'comment': str(cells[11] or '').strip(), 'rounds': int(cells[7]) if cells[7] else None})
            if not grouped or len(grouped) > 50:
                raise ValueError('No valid bouts or too many bouts')
            result = []
            for number, rows in sorted(grouped.items()):
                if len(rows) != 2 or len({r['boxrec_id'] for r in rows}) != 2:
                    raise ValueError(f'Bout {number} requires two distinct fighters')
                winners = [r for r in rows if r['outcome'] == 'WON']
                losers = [r for r in rows if r['outcome'].startswith('LOST')]
                if len(winners) != 1 or len(losers) != 1:
                    raise ValueError(f'Bout {number} needs one winner and one loser; review unsupported or ambiguous result')
                winner, loser = (winners[0], losers[0])
                scheduled = winner['rounds'] or loser['rounds']
                method = 'TKO' if 'TKO' in loser['outcome'] else 'KO' if 'KO' in loser['outcome'] else 'UD'
                scores = []
                round_number = None
                elapsed = None
                if method == 'UD':
                    score = re.search('\\b(\\d{2})\\s*[-–]\\s*(\\d{2})\\b', winner['comment'])
                    if not score or not all(judges) or int(score[1]) <= int(score[2]):
                        raise ValueError(f'Bout {number}: final judges totals need review')
                    if not all((j.split()[0].lower() in winner['comment'].lower() for j in judges)):
                        raise ValueError(f'Bout {number}: judge names do not match the comments')
                    scores = [{'judge': j, 'winner_total': int(score[1]), 'loser_total': int(score[2])} for j in judges]
                    round_number = scheduled
                else:
                    stop = re.search('RD\\s*(\\d+)\\s*[-–]?\\s*(\\d+):([0-5]\\d)', winner['comment'], re.I)
                    if not stop:
                        raise ValueError(f'Bout {number}: stoppage round and time missing')
                    round_number = int(stop[1])
                    elapsed = f'{int(stop[2])}:{stop[3]}'
                    if round_number < 1 or (scheduled and round_number > scheduled) or int(stop[2]) >= 3:
                        raise ValueError(f'Bout {number}: invalid stoppage time/round')
                result.append({'order': number, 'fighters': rows, 'winner_boxrec_id': winner['boxrec_id'], 'method': method, 'round': round_number, 'elapsed': elapsed, 'scores': scores})
            return (event_date, result)
        finally:
            book.close()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(422, f'Could not read commission results: {str(e)[:180]}')

def serialize_result(db, row, owner_id=None):
    fighters = json.loads(row.fighters_json)
    names = {f['fighter_id']: f['legal_name_at_import'] for f in fighters}
    data = {'bout_id': row.bout_id, 'event_id': row.event_id, 'official_order': row.official_order, 'winner_id': row.winner_id, 'winner_name': names.get(row.winner_id, ''), 'method': row.method, 'round': row.round, 'elapsed': row.elapsed, 'red': {'id': row.red_fighter_id, 'name': names.get(row.red_fighter_id, '')}, 'blue': {'id': row.blue_fighter_id, 'name': names.get(row.blue_fighter_id, '')}, 'judges': json.loads(row.scores_json), 'score_detail': 'Final totals only; round-by-round scores were not supplied.' if row.method == 'UD' else 'No judges scorecards were supplied for this stoppage.'}
    data['record_review'] = [f for f in fighters if owner_id is None or f['fighter_id'] == owner_id]
    return data

@router.get('/{event_id}/results')
def get_results(event_id: int, response: Response, db=Depends(get_db), user=Depends(current_user)):
    if user.role not in ('admin', 'staff', 'matchmaker'):
        raise HTTPException(403, 'Event staff access required')
    event = event_for(db, event_id)
    rows = db.query(BoxingBoutResult).filter_by(event_id=event_id).order_by(BoxingBoutResult.official_order).all()
    response.headers['Cache-Control'] = 'private, no-store'
    return {'event': {'id': event.id, 'name': event.name, 'date': event.event_date}, 'results': [serialize_result(db, r) for r in rows], 'source_available': bool(rows), 'career_records_mode': 'review_only'}

@router.post('/{event_id}/results/import')
async def import_results(event_id: int, file: UploadFile=File(...), db=Depends(get_db), user=Depends(staff_user)):
    raw = await file.read(2 * 1024 * 1024 + 1)
    event_date, parsed = parse_workbook(raw)
    event = event_for(db, event_id, True)
    if event.event_date != event_date:
        raise HTTPException(409, 'Workbook date does not match this event')
    sha = hashlib.sha256(raw).hexdigest()
    existing = db.query(BoxingResultSource).filter_by(event_id=event_id, sha256=sha).first()
    if existing:
        return {'imported': 0, 'already_imported': True, 'career_records_changed': 0}
    if db.query(BoxingBoutResult).filter_by(event_id=event_id).first():
        raise HTTPException(409, 'Results already exist for this event. Review corrections rather than overwriting the imported source.')
    bouts = [b for b in db.query(BoxingBout).filter_by(event_id=event_id) if str(b.status or '').strip().lower() not in CANCELLED]
    fighter_ids = {f for b in bouts for f in (b.red_fighter_id, b.blue_fighter_id)}
    fighters = db.query(BoxingFighter).filter(BoxingFighter.id.in_(fighter_ids)).all()
    by_source = {}
    for f in fighters:
        key = str(f.boxrec_id or '').strip()
        by_source.setdefault(key, []).append(f)
    planned = []
    seen = set()
    for item in parsed:
        matched = []
        for entry in item['fighters']:
            candidates = by_source.get(entry['boxrec_id'], [])
            if len(candidates) != 1:
                raise HTTPException(409, f"Exact source ID match required for {entry['source_name']}; no records changed")
            f = candidates[0]
            entry = {**entry, 'fighter_id': f.id, 'legal_name_at_import': f.legal_name, 'current_record_at_import': f.pro_record}
            reported = record_tuple(entry['reported_record'])
            current = record_tuple(f.pro_record)
            impossible = reported is None or (entry['outcome'] == 'WON' and reported[0] == 0) or (entry['outcome'].startswith('LOST') and reported[1] == 0)
            entry['career_review_required'] = impossible or reported != current
            matched.append(entry)
        ids = {r['fighter_id'] for r in matched}
        matches = [b for b in bouts if {b.red_fighter_id, b.blue_fighter_id} == ids]
        if len(matches) != 1 or matches[0].id in seen:
            raise HTTPException(409, f"Bout {item['order']} does not uniquely match the current card; no records changed")
        bout = matches[0]
        seen.add(bout.id)
        winner = next((r['fighter_id'] for r in matched if r['boxrec_id'] == item['winner_boxrec_id']))
        scores = [{'judge': s['judge'], 'red_total': s['winner_total'] if winner == bout.red_fighter_id else s['loser_total'], 'blue_total': s['winner_total'] if winner == bout.blue_fighter_id else s['loser_total']} for s in item['scores']]
        planned.append((bout, item, matched, winner, scores))
    if seen != {b.id for b in bouts}:
        raise HTTPException(409, 'Workbook does not cover the entire current card; review the event before importing')
    source = BoxingResultSource(event_id=event_id, filename=(file.filename or 'Boxing results.xlsx')[:200], sha256=sha, content=raw, created_by=user.id)
    db.add(source)
    db.flush()
    for bout, item, matched, winner, scores in planned:
        db.add(BoxingBoutResult(bout_id=bout.id, event_id=event_id, source_id=source.id, red_fighter_id=bout.red_fighter_id, blue_fighter_id=bout.blue_fighter_id, official_order=item['order'], winner_id=winner, method=item['method'], round=item['round'], elapsed=item['elapsed'], scores_json=json.dumps(scores), fighters_json=json.dumps(matched)))
        bout.status = 'completed'
        bout.bout_order = item['order']
    db.add(SecurityLog(user_id=user.id, action='BOXING_RESULTS_IMPORTED', description=json.dumps({'event_id': event_id, 'sha256': sha, 'bouts': len(planned), 'career_records_changed': 0, 'career_records_mode': 'review_only'}), success=True))
    db.commit()
    return {'imported': len(planned), 'already_imported': False, 'career_records_changed': 0, 'record_reviews': sum((f['career_review_required'] for _, _, fs, _, _ in planned for f in fs))}

@router.get('/{event_id}/results/source.xlsx')
def download_results_source(event_id: int, db=Depends(get_db), user=Depends(staff_user)):
    source = db.query(BoxingResultSource).filter_by(event_id=event_id).first()
    if not source:
        raise HTTPException(404, 'No results workbook imported')
    return Response(source.content, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', headers={'Cache-Control': 'private, no-store', 'Content-Disposition': f'attachment; filename="tng_event_{event_id}_boxing_results.xlsx"'})

@router.get('/fighters/{fighter_id}/results')
def fighter_results(fighter_id: int, response: Response, db=Depends(get_db), user=Depends(current_user)):
    if user.role not in ('admin', 'staff'):
        account = db.query(FighterAccount).filter_by(user_id=user.id).first() if user.role == 'fighter' else None
        if not account or account.fighter_id != fighter_id:
            raise HTTPException(403, 'Own fighter or staff access required')
    if not db.get(BoxingFighter, fighter_id):
        raise HTTPException(404, 'Fighter not found')
    query = db.query(BoxingBoutResult).filter((BoxingBoutResult.red_fighter_id == fighter_id) | (BoxingBoutResult.blue_fighter_id == fighter_id))
    total = query.count()
    wins = query.filter(BoxingBoutResult.winner_id == fighter_id).count()
    rows = query.join(BoxingEvent, BoxingEvent.id == BoxingBoutResult.event_id).order_by(BoxingEvent.event_date.desc(), BoxingBoutResult.official_order.asc()).limit(50).all()
    response.headers['Cache-Control'] = 'private, no-store'
    entries = []
    for r in rows:
        event = db.get(BoxingEvent, r.event_id)
        entries.append({**serialize_result(db, r, fighter_id), 'event_name': event.name, 'event_date': event.event_date, 'own_result': 'W' if r.winner_id == fighter_id else 'L'})
    return {'fighter_id': fighter_id, 'tng_record': {'wins': wins, 'losses': total - wins, 'total': total}, 'results': entries, 'record_scope': 'Imported TNG bouts only; career totals are not automatically changed.'}
