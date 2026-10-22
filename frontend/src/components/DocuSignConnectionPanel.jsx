import React, { useState } from 'react';
import { Alert, Box, Button, Stack, Typography } from '@mui/material';
const API = (import.meta.env.VITE_API_URL || 'https://sea-lion-app-2-gxyfr.ondigitalocean.app').replace(/\/$/, '');
const headers = () => ({ Authorization: `Bearer ${localStorage.getItem('token')}` });
export default function DocuSignConnectionPanel() {
  const [result, setResult] = useState(null), [busy, setBusy] = useState(false), [error, setError] = useState('');
  async function check() {
    setBusy(true); setError(''); setResult(null);
    try {
      const response = await fetch(`${API}/api/boxing/docusign/connection-check`, { method: 'POST', headers: headers() });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || 'Connection check failed');
      setResult(body);
    } catch (e) { setError(e.message || 'Connection check failed'); }
    finally { setBusy(false); }
  }
  async function downloadPublicKey() {
    setBusy(true); setError('');
    try {
      const response = await fetch(`${API}/api/boxing/docusign/public-key`, { headers: headers() });
      if (!response.ok) { const body = await response.json(); throw new Error(body.detail || 'Only an administrator can download the public key'); }
      const blob = await response.blob(), url = URL.createObjectURL(blob), a = document.createElement('a');
      a.href = url; a.download = 'TNG-DocuSign-PUBLIC-key.pem'; document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) { setError(e.message || 'Public key download failed'); }
    finally { setBusy(false); }
  }
  return <Box sx={{ p: 2, border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
    <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} justifyContent="space-between" alignItems={{ sm: 'center' }}>
      <Box><Typography variant="subtitle1" fontWeight={800}>DocuSign connection</Typography><Typography variant="body2" color="text.secondary">Verify authentication and sending-account access without sending a contract.</Typography></Box>
      <Button variant="outlined" disabled={busy} onClick={check}>{busy ? 'Working…' : 'Check DocuSign connection'}</Button>
    </Stack>
    {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}
    {result && <Alert severity={result.ready ? 'success' : 'error'} sx={{ mt: 2 }}>{result.message}{result.environment && <Typography variant="body2" sx={{ mt: 1 }}>Environment: {result.environment} · Integration key ending {result.integration_key_suffix}</Typography>}{result.account_api_host && <Typography variant="body2">Account API host: {result.account_api_host}</Typography>}</Alert>}
    {result && !result.ready && <Box sx={{ mt: 2 }}><Typography variant="body2">For an RSA key mismatch, a DocuSign administrator must register this server’s public key under the matching integration in Apps and Keys. Do not replace or share the private key. Recheck the connection after updating DocuSign.</Typography><Button disabled={busy} onClick={downloadPublicKey} sx={{ mt: 1 }}>Download public key (TNG admin)</Button></Box>}
  </Box>;
}
