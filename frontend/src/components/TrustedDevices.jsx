import React, { useEffect, useState } from 'react';
import { Alert, Box, Button, Card, CardContent, Chip, Stack, TextField, Typography } from '@mui/material';
import DevicesRoundedIcon from '@mui/icons-material/DevicesRounded';
import { API, authHeaders } from '../services/api';
const names = {
  current: 'This device',
  remembered: 'Remembered access',
  revoked: 'Revoked',
  invalidated: 'Security credentials changed',
  unverified: 'Earlier session · status unverified'
};
export default function TrustedDevices() {
  const [data, setData] = useState(null),
    [error, setError] = useState(''),
    [busy, setBusy] = useState(null),
    [editing, setEditing] = useState(null),
    [label, setLabel] = useState('');
  async function load(signal) {
    const r = await fetch(`${API}/api/auth/devices`, {
      headers: authHeaders(),
      cache: 'no-store',
      signal
    });
    const d = await r.json();
    if (!r.ok) throw new Error(typeof d.detail === 'string' ? d.detail : 'Could not load device sessions.');
    setData(d);
  }
  useEffect(() => {
    const abort = new AbortController();
    load(abort.signal).catch(e => {
      if (!abort.signal.aborted) setError(e.message);
    });
    return () => abort.abort();
  }, []);
  async function action(device, rename = false) {
    if (busy !== null) return;
    setBusy(device.id);
    setError('');
    try {
      const r = await fetch(`${API}/api/auth/devices/${device.id}${rename ? '' : '/revoke'}`, {
        method: rename ? 'PATCH' : 'POST',
        headers: {
          ...authHeaders(),
          'Content-Type': 'application/json'
        },
        body: rename ? JSON.stringify({
          label
        }) : undefined
      });
      const d = await r.json();
      if (!r.ok) throw new Error(typeof d.detail === 'string' ? d.detail : 'Could not update device.');
      if (d.current) {
        window.dispatchEvent(new Event('tng-session-revoked'));
        return;
      }
      setEditing(null);
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(null);
    }
  }
  return <Card sx={{
    mt: 3
  }}><CardContent><Stack direction="row" sx={{
        alignItems: "center",
        gap: 1.5,
        mb: 1
      }}><DevicesRoundedIcon color="secondary" /><Typography variant="h6">Your trusted devices</Typography><Chip size="small" label={data ? `${data.total} saved` : 'Loading…'} sx={{
          ml: 'auto'
        }} /></Stack><Typography color="text.secondary" variant="body2" sx={{
        mb: 2
      }}>Name your remembered sign-ins and revoke devices you no longer use. These are saved access sessions, not an online-device monitor. Public check-in kiosk pairings are managed separately.</Typography>
 {error && <Alert severity="error" sx={{
        mb: 2
      }}>{error}</Alert>}
 <Stack spacing={1}>{data?.devices?.map(d => <Box key={d.id} sx={{
          p: 2,
          border: '1px solid',
          borderColor: 'divider',
          borderRadius: 3
        }}><Stack direction={{
            xs: 'column',
            sm: 'row'
          }} sx={{
            gap: 1.5,
            alignItems: {
              sm: 'center'
            }
          }}><Box sx={{
              flex: 1
            }}><Typography sx={{
                fontWeight: 800
              }}>{d.label}</Typography><Typography variant="caption" color="text.secondary">Created {new Date(d.created_at + (/(?:Z|[+-]\d\d:\d\d)$/.test(d.created_at) ? '' : 'Z')).toLocaleString('en-US', {
                  timeZone: 'America/Chicago'
                })} CT</Typography></Box><Chip size="small" color={d.status === 'current' ? 'success' : 'default'} label={names[d.status] || d.status} />{!['revoked', 'invalidated'].includes(d.status) && <><Button disabled={busy !== null} onClick={() => {
                setEditing(d.id);
                setLabel(d.label);
              }} sx={{
                display: d.renamable ? 'inline-flex' : 'none'
              }}>Rename</Button><Button variant="outlined" color="error" disabled={busy !== null} onClick={() => action(d)}>{busy === d.id ? 'Updating…' : d.current ? 'Log out this device' : 'Revoke access'}</Button></>}</Stack>{editing === d.id && <Stack direction="row" sx={{
            gap: 1,
            mt: 2
          }}><TextField size="small" fullWidth label="Device name" value={label} onChange={e => setLabel(e.target.value)} inputProps={{
              maxLength: 80
            }} /><Button variant="contained" disabled={busy !== null || !label.trim()} onClick={() => action(d, true)}>Save</Button><Button onClick={() => setEditing(null)}>Cancel</Button></Stack>}</Box>)}</Stack>
 {data && !data.devices.length && <Typography color="text.secondary">No remembered device sessions yet. You can enable remembered sign-in in TNG Assistant settings.</Typography>}
 {data?.total > data?.limit && <Typography variant="caption">Showing the most recent {data.limit} sessions.</Typography>}
 </CardContent></Card>;
}
