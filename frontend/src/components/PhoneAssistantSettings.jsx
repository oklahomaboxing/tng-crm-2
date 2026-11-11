import React, { useEffect, useState } from 'react';
import { Alert, Box, Button, Card, CardContent, Chip, FormControlLabel, Stack, Switch, TextField, MenuItem, Typography } from '@mui/material';
const API = (import.meta.env.VITE_API_URL || 'https://sea-lion-app-2-gxyfr.ondigitalocean.app').replace(/\/$/, '');
const headers = () => ({ Authorization: `Bearer ${localStorage.getItem('token')}`, 'Content-Type': 'application/json' });
export default function PhoneAssistantSettings({ onNavigate }) {
  const [data, setData] = useState(null), [settings, setSettings] = useState({}), [dirty, setDirty] = useState(false), [busy, setBusy] = useState(false), [error, setError] = useState(''), [message, setMessage] = useState(''), [charges, setCharges] = useState(false);
  async function request(path = '', method = 'GET', body) {
    const r = await fetch(`${API}/api/phone/admin${path}`, { method, headers: headers(), ...(body ? { body: JSON.stringify(body) } : {}) });
    const value = await r.json();
    if (!r.ok) throw Error(typeof value.detail === 'string' ? value.detail : 'Check the phone numbers and approved answer fields.');
    return value;
  }
  function apply(value) { setData(old => ({ ...old, ...value })); setSettings(value.settings); setDirty(false); }
  useEffect(() => { let alive = true; request().then(value => { if (alive) apply(value); }).catch(e => { if (alive) setError(e.message); }); return () => { alive = false; }; }, []);
  function update(key, value) { setSettings(old => ({ ...old, [key]: value })); setDirty(true); }
  async function save() { setBusy(true); setError(''); setMessage(''); try { apply(await request('', 'PUT', settings)); setMessage('Phone settings saved. No calls were placed.'); } catch (e) { setError(e.message); } finally { setBusy(false); } }
  async function connect() { setBusy(true); setError(''); setMessage(''); try { apply(await request('/connect', 'POST', { acknowledge_voice_charges: charges })); setMessage('Twilio voice connected. Test the forwarding number below, then set NumberBarn call forwarding to it.'); } catch (e) { setError(e.message); } finally { setBusy(false); } }
  async function connectTicketLinks() { setBusy(true); setError(''); try { const r = await fetch(`${API}/api/phone/admin/ticket-links/connect`, { method: 'POST', headers: headers() }); const value = await r.json(); if (!r.ok) throw Error(value.detail || 'Could not connect ticket texts'); setData(old => ({ ...old, ...value })); setMessage('Ticket checkout texts connected. Links are sent only after the caller requests one.'); } catch (e) { setError(e.message); } finally { setBusy(false); } }
  return <Card id="phone-assistant"><CardContent><Stack spacing={2}>
    <Box><Typography variant="h6" fontWeight={900}>TNG phone assistant</Typography><Typography color="text.secondary">405-TNG-4GYM · NumberBarn · Speech/keypad menu with approved answers and staff callbacks.</Typography></Box>
    {error && <Alert severity="error">{error}</Alert>}{message && <Alert severity="info">{message}</Alert>}
    {data && <>
      <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap' }}><Chip label={data.connected ? 'Twilio voice connected' : 'Voice setup pending'} color={data.connected ? 'success' : 'default'} /><Chip label={`${data.today_calls || 0} calls today · Central Time`} /></Stack>
      <Alert severity="info">Menu: 1 hours/location · 2 memberships · 3 events/tickets · 4 callback or gym visit · 5 buy tickets by text · 6 marketing · 0 staff. Callers can also say these choices. This version uses approved text, with no AI API credits or call recording.</Alert>
      <TextField label="NumberBarn public number" value={settings.public_number || ''} disabled={busy} onChange={e => update('public_number', e.target.value)} />
      <TextField label="Direct staff transfer number" value={settings.staff_number || ''} disabled={busy} onChange={e => update('staff_number', e.target.value)} helperText="Must ring staff directly and must not forward back to the NumberBarn or Twilio line." />
      <TextField label="Marketing transfer number" value={settings.marketing_number || ''} disabled={busy} onChange={e => update('marketing_number', e.target.value)} />
      <TextField select label="Receptionist voice" value={settings.voice || 'Polly.Joanna'} disabled={busy} onChange={e => update('voice',e.target.value)} helperText="Text-to-speech uses Twilio voice usage rates."><MenuItem value="Polly.Joanna">Joanna — natural US English</MenuItem><MenuItem value="Polly.Matthew">Matthew — natural US English</MenuItem><MenuItem value="woman">Standard voice</MenuItem></TextField>
      <FormControlLabel control={<Switch checked={!!settings.use_live_membership_prices} disabled={busy} onChange={e => update('use_live_membership_prices',e.target.checked)} />} label="Keep membership answers current from the public TNGOS signup catalog" />
      <FormControlLabel control={<Switch checked={!!settings.use_live_event_info} disabled={busy} onChange={e => update('use_live_event_info',e.target.checked)} />} label="Keep event dates and times current from published TNGOS events" />
      <FormControlLabel control={<Switch checked={!!settings.ticket_links_enabled} disabled={busy} onChange={e => update('ticket_links_enabled',e.target.checked)} />} label="Offer secure ticket checkout links by text after caller confirmation" />
      <Button disabled={busy || dirty || data.ticket_links_ready} onClick={connectTicketLinks}>{data.ticket_links_ready ? 'Ticket checkout texts connected' : 'Connect approved ticket-text service'}</Button>
      <FormControlLabel control={<Switch checked={!!settings.enabled} disabled={busy} onChange={e => update('enabled', e.target.checked)} />} label="Speech/keypad menu enabled — when off, connected calls go directly to staff" />
      {[['greeting','Greeting'],['hours_answer','Approved hours and location answer'],['membership_answer','Approved membership answer'],['events_answer','Approved events and tickets answer']].map(([key,label]) => <TextField key={key} label={label} value={settings[key] || ''} disabled={busy} multiline minRows={key === 'greeting' ? 2 : 3} onChange={e => update(key,e.target.value)} />)}
      {data.membership_preview && <Alert severity="info"><Typography fontWeight={800}>Current spoken membership information</Typography>{data.membership_preview}</Alert>}
      {data.events_preview && <Alert severity="info"><Typography fontWeight={800}>Current spoken event information</Typography>{data.events_preview}</Alert>}
      <Button variant="outlined" disabled={busy || !dirty} onClick={save}>Save approved answers & settings</Button>
      <Typography variant="subtitle2">Forwarding destination: {data.forwarding_number || 'Twilio number is not configured'}</Typography>
      <Typography variant="body2">After connecting, call this Twilio number to test the menu and staff transfer. Then open NumberBarn, select 405-TNG-4GYM, and set its call-forwarding destination to this number. Keep the public number with NumberBarn.</Typography>
      <FormControlLabel control={<Switch checked={charges} disabled={busy} onChange={e => setCharges(e.target.checked)} />} label="I understand inbound calls, speech recognition and staff transfers use paid voice services." />
      <Button variant="contained" disabled={busy || dirty || !charges || !data.twilio_configured} onClick={connect}>{busy ? 'Connecting…' : 'Connect Twilio voice menu'}</Button>
      <Typography variant="caption" color="text.secondary">Connecting configures voice webhooks on your assigned Twilio number. NumberBarn forwarding is changed in your NumberBarn account. SMS settings remain intact. Callback requests appear in Leads and do not create paid gym memberships.</Typography>
      <Box><Typography variant="subtitle1" fontWeight={800}>Recent calls</Typography>{!(data.calls || []).length ? <Typography color="text.secondary">No calls recorded yet.</Typography> : data.calls.map(call => <Box key={call.call_sid} sx={{ py: 1, borderBottom: '1px solid', borderColor: 'divider' }}><Typography variant="body2">{new Date(call.created_at).toLocaleString()} · Caller ending {call.caller_last_four || 'unknown'} · {call.status} · {call.stage.replaceAll('_',' ')}{call.lead_id ? ` · Lead #${call.lead_id}` : ''}{call.ticket_link_status ? ` · Ticket link: ${call.ticket_link_status}` : ''}</Typography></Box>)}<Button onClick={() => onNavigate?.('Leads')}>View callback requests in Leads</Button></Box>
    </>}
  </Stack></CardContent></Card>;
}
