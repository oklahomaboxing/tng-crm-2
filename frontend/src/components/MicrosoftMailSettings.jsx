import React, { useEffect, useState } from 'react';
import { Alert, Box, Button, Card, CardContent, Stack, TextField, Typography } from '@mui/material';
const API = (import.meta.env.VITE_API_URL || 'https://sea-lion-app-2-gxyfr.ondigitalocean.app').replace(/\/$/, '');
const auth = () => ({ Authorization: `Bearer ${localStorage.getItem('token')}`, 'Content-Type': 'application/json' });
export default function MicrosoftMailSettings() {
  const [status, setStatus] = useState(null), [tenant, setTenant] = useState(''), [client, setClient] = useState(''), [secret, setSecret] = useState('');
  const [busy, setBusy] = useState(false), [error, setError] = useState(''), [help, setHelp] = useState(false);
  async function call(path, method = 'GET', body) {
    const r = await fetch(`${API}/api/mail/microsoft365/${path}`, { method, headers: auth(), ...(body ? { body: JSON.stringify(body) } : {}) });
    const data = await r.json(); if (!r.ok) throw Error(typeof data.detail === 'string' ? data.detail : 'Could not update the Microsoft connection'); return data;
  }
  useEffect(() => { let alive = true; call('status').then(data => { if (alive) { setStatus(data); setTenant(data.tenant_id); setClient(data.client_id); } }).catch(e => { if (alive) setError(e.message); }); return () => { alive = false; }; }, []);
  async function connect() {
    setBusy(true); setError('');
    try {
      if (!status?.configured || tenant !== status.tenant_id || client !== status.client_id || secret) {
        const data = await call('config', 'PUT', { tenant_id: tenant.trim(), client_id: client.trim(), client_secret: secret || null }); setStatus(data); setSecret('');
      }
      const data = await call('connect', 'POST'); window.location.assign(data.authorization_url);
    } catch (e) { setError(e.message); setBusy(false); }
  }
  async function disconnect() {
    setBusy(true); setError(''); try { setStatus(await call('disconnect', 'POST')); } catch (e) { setError(e.message); } finally { setBusy(false); }
  }
  return <Card id="microsoft-email"><CardContent><Stack spacing={2}>
    <Box><Typography variant="h6" fontWeight={900}>Microsoft 365 email</Typography><Typography color="text.secondary">Send fighter welcome letters from marketing@tngboxinggym.com through Outlook. Sent messages appear in that mailbox’s Sent Items.</Typography></Box>
    {error && <Alert severity="error">{error}</Alert>}
    <Alert severity={status?.connected ? 'success' : 'info'}>{status?.connected ? 'Microsoft mailbox connected. New welcome emails use Microsoft 365.' : 'Microsoft is not connected. Welcome emails continue through Resend until you connect.'}</Alert>
    <Button onClick={() => setHelp(!help)}>{help ? 'Hide setup instructions' : 'Microsoft administrator setup instructions'}</Button>
    {help && <Box sx={{ bgcolor: 'action.hover', p: 2, borderRadius: 2 }}>
      <Typography paragraph>1. In Microsoft Entra → App registrations, create “TNGOS Mail” for your organization only.</Typography>
      <Typography paragraph>2. Add a Web redirect URI with this exact address:</Typography>
      <Typography component="code" sx={{ display: 'block', overflowWrap: 'anywhere', mb: 2 }}>{status?.redirect_uri || `${API}/api/mail/microsoft365/callback`}</Typography>
      <Typography paragraph>3. Add Microsoft Graph delegated permissions Mail.Send, User.Read and offline_access, then grant your organization’s administrator consent.</Typography>
      <Typography paragraph>4. Create a client secret under Certificates & secrets. Copy its Value, not its Secret ID. Enter it only in the secure field below.</Typography>
      <Typography>5. Copy the Directory (tenant) ID and Application (client) ID from Overview. Connect below, then sign in as marketing@tngboxinggym.com. Shared mailboxes require a separate Send As setup.</Typography>
    </Box>}
    <TextField label="Directory (tenant) ID" value={tenant} onChange={e => setTenant(e.target.value)} disabled={busy} autoComplete="off" />
    <TextField label="Application (client) ID" value={client} onChange={e => setClient(e.target.value)} disabled={busy} autoComplete="off" />
    <TextField label="Client secret value" type="password" value={secret} onChange={e => setSecret(e.target.value)} disabled={busy} autoComplete="new-password" helperText={status?.has_client_secret ? 'A secret is securely saved. Leave blank to keep it.' : 'Stored encrypted on the server. Never paste the secret into chat.'} />
    <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap' }}><Button variant="contained" disabled={busy || !tenant.trim() || !client.trim() || (!secret && !status?.has_client_secret)} onClick={connect}>{busy ? 'Connecting…' : status?.connected ? 'Reconnect Microsoft 365' : 'Save & connect Microsoft 365'}</Button>{status?.connected && <Button disabled={busy} onClick={disconnect}>Disconnect Microsoft — use Resend for new welcome emails</Button>}</Stack>
    <Typography variant="caption" color="text.secondary">Connecting does not send any email. Existing unconfirmed emails retain their original provider for duplicate protection. Other TNGOS email workflows keep their existing configuration.</Typography>
  </Stack></CardContent></Card>;
}
