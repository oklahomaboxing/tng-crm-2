import React, { useState } from 'react';
import { Alert, Box, Button, Dialog, DialogTitle, DialogContent, DialogActions, Stack, TextField, Typography } from '@mui/material';
const API = (import.meta.env.VITE_API_URL || 'https://sea-lion-app-2-gxyfr.ondigitalocean.app').replace(/\/$/, '');
const headers = () => ({ Authorization: `Bearer ${localStorage.getItem('token')}`, 'Content-Type': 'application/json' });
export default function FighterWelcomeLetter({ eventId }) {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState(null);
  const [settings, setSettings] = useState({});
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  async function request(suffix = '', options = {}) {
    const r = await fetch(`${API}/api/boxing/events/${eventId}/fighter-welcome${suffix}`, { ...options, headers: headers() });
    const body = await r.json();
    if (!r.ok) throw Error(typeof body.detail === 'string' ? body.detail : Array.isArray(body.detail) ? body.detail.map(item => item.msg).join(' ') : 'Could not load fighter letter');
    return body;
  }
  async function load() {
    setOpen(true); setBusy(true); setData(null); setMessage(''); setDirty(false);
    try { const body = await request(); setData(body); setSettings(body.settings); } catch (e) { setMessage(e.message); } finally { setBusy(false); }
  }
  async function save() {
    setBusy(true); setMessage('');
    try { const body = await request('', { method: 'PUT', body: JSON.stringify(settings) }); setData(body); setSettings(body.settings); setDirty(false); setMessage('Letter saved. Review the preview before emailing.'); } catch (e) { setMessage(e.message); } finally { setBusy(false); }
  }
  async function download() {
    setBusy(true); setMessage('');
    try {
      const r = await fetch(`${API}/api/boxing/events/${eventId}/fighter-welcome.pdf`, { headers: headers() });
      if (!r.ok) throw Error('Could not download welcome letter');
      const url = URL.createObjectURL(await r.blob()); const a = document.createElement('a'); a.href = url; a.download = `TNG_${eventId}_Fighter_Welcome.pdf`; document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url), 60000);
    } catch (e) { setMessage(e.message); } finally { setBusy(false); }
  }
  async function send(retryUnconfirmed = false, useMicrosoftForRejected = false) {
    setBusy(true); setMessage('');
    try {
      const body = await request('/send', { method: 'POST', body: JSON.stringify({ preview_hash: data.preview_hash, retry_unconfirmed: retryUnconfirmed, use_microsoft_for_rejected: useMicrosoftForRejected }) });
      setData(await request());
      setMessage(`${body.accepted} email(s) accepted by the provider; ${body.already_submitted} previously submitted; ${body.needs_review} need review. Provider acceptance does not confirm inbox delivery. ${(body.issues || []).join(' ')}`);
    } catch (e) { setMessage(e.message); } finally { setBusy(false); }
  }
  return <>
    <Button variant="outlined" onClick={load}>Fighter welcome letter</Button>
    <Dialog open={open} onClose={() => { if (!busy) setOpen(false); }} maxWidth="md" fullWidth>
      <DialogTitle>Fighter welcome letter</DialogTitle>
      <DialogContent dividers>
        <Stack spacing={2}>
          <Typography>Emails use {data?.email_provider === 'microsoft365' ? 'Microsoft 365 / Outlook' : 'Resend'} and are sent from marketing@tngboxinggym.com. Download a PDF for teams, or email it individually to booked fighters and additional recipients. Cancelled bouts are excluded and shared email addresses receive one copy.</Typography>
          {message && <Alert severity="info">{message}</Alert>}
          {!data && busy && <Typography>Loading letter…</Typography>}
          {data && <>
            <Alert severity={data.missing_fields.length ? 'warning' : 'success'}>{data.missing_fields.length ? `Complete before sending: ${data.missing_fields.join(', ')}. You can download a marked draft now.` : 'Schedule details are filled in. Review the letter below before sending.'}</Alert>
            {[['weigh_in_datetime','Weigh-in date and time (Oklahoma time)'],['weigh_in_location','Weigh-in venue and street address'],['fighter_arrival','Fight-day fighter / team arrival time'],['contact_name','Promoter contact'],['contact_phone','Contact phone'],['contact_email','Contact email'],['additional_notes','Additional event instructions']].map(([key,label]) => <TextField key={key} label={label} value={settings[key] || ''} disabled={busy} multiline={key === 'additional_notes'} minRows={key === 'additional_notes' ? 3 : undefined} onChange={e => { setSettings(old => ({ ...old, [key]: e.target.value })); setDirty(true); }} />)}
            <TextField label="Additional email recipients" value={Array.isArray(settings.additional_emails) ? settings.additional_emails.join('\n') : settings.additional_emails || ''} multiline minRows={3} disabled={busy} onChange={e => { setSettings(old => ({ ...old, additional_emails: e.target.value })); setDirty(true); }} helperText="Add coaches, managers or other recipients. Separate addresses with commas, semicolons or new lines (up to 100). Save to update the recipient preview. Already accepted copies of this letter are skipped." />
            <Button variant="outlined" disabled={busy || !dirty} onClick={save}>Save & update preview</Button>
            {dirty && <Alert severity="warning">Save your changes to update the preview and PDF.</Alert>}
            {data.email_provider === 'microsoft365' && !!data.rejected_resend && <Alert severity="warning">{data.rejected_resend} earlier Resend submissions were rejected. Use the Microsoft button below to send only those entries; accepted emails are skipped. An earlier unconfirmed attempt may still have arrived, so sending through another provider can produce another copy.</Alert>}
            <Typography variant="subtitle2">Recipients: {data.recipients.length} unique email addresses · Previously accepted: {data.accepted} · Submission status needs review: {data.needs_review}</Typography>
            <Box sx={{ maxHeight: 120, overflow: 'auto', bgcolor: 'action.hover', p: 1, borderRadius: 1 }}>{data.recipients.map(r => <Typography key={r.email} variant="body2">{r.fighters.join(', ')} — {r.email}</Typography>)}</Box>
            {!!data.missing_email_fighters.length && <Alert severity="warning">Missing or invalid email: {data.missing_email_fighters.join(', ')}. Update their fighter profiles to include them.</Alert>}
            <Typography variant="h6">Letter preview</Typography>
            <Box component="pre" sx={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit', bgcolor: '#fafafa', border: '1px solid #ddd', p: 2, maxHeight: 480, overflow: 'auto', m: 0 }}>{data.text}</Box>
          </>}
        </Stack>
      </DialogContent>
      <DialogActions sx={{ flexWrap: 'wrap', gap: 1 }}>
        <Button disabled={busy} onClick={() => setOpen(false)}>Close</Button>
        <Button disabled={busy || dirty || !data} onClick={download}>Download PDF</Button>
        {data?.email_provider === 'microsoft365' && !!data?.rejected_resend && <Button variant="contained" disabled={busy || dirty || !!data.missing_fields.length} onClick={() => send(false, true)}>Send {data.rejected_resend} rejected emails through Microsoft</Button>}
        {!!data?.needs_review && !(data.email_provider === 'microsoft365' && data.rejected_resend === data.needs_review) && <Button disabled={busy || dirty || !!data.missing_fields.length} onClick={() => send(true)}>Retry unconfirmed emails safely</Button>}
        <Button variant="contained" disabled={busy || dirty || !data || !!data.missing_fields.length || !data.recipients.length || data.accepted + data.needs_review >= data.recipients.length} onClick={() => send(false)}>Send welcome emails</Button>
      </DialogActions>
    </Dialog>
  </>;
}
