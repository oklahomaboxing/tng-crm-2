import { API, authHeaders } from '../services/api';

// Both workspaces use the same viewer. Signature evidence is a separate artifact.
export async function openContractFile(contractId, { signed = false, download = false, record = false } = {}) {
  if (!contractId) throw new Error('Choose a contract first.');
  const popup = download ? null : window.open('', '_blank');
  if (!download && !popup) throw new Error('Please allow popups for TNGOS to view the contract.');
  if (popup) {popup.opener = null;popup.document?.write('<p style="font-family:Arial;padding:24px">Loading contract document…</p>');}
  try {
    const response = await fetch(`${API.replace(/\/$/, '')}/api/boxing/contracts/${contractId}/${signed ? 'signed-file' : 'official-pdf'}`, {
      headers: authHeaders(), cache: 'no-store'
    });
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(typeof data.detail === 'string' ? data.detail : 'The contract PDF could not be loaded.');
    }
    if (!response.headers.get('content-type')?.includes('application/pdf')) throw new Error('The server did not return a contract PDF.');
    const url = URL.createObjectURL(await response.blob());
    if (download) {
      const link = document.createElement('a');
      link.href = url;
      link.download = `contract-${contractId}-${signed ? (record ? 'signature-record' : 'signed-contract') : 'current-document'}.pdf`;
      link.click();
    } else popup.location.href = url;
    setTimeout(() => URL.revokeObjectURL(url), 60000);
  } catch (error) { popup?.close(); throw error; }
}
