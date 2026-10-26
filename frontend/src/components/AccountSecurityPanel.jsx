import React, {useState} from 'react';
import {Alert, Box, Button, Stack, TextField, Typography} from '@mui/material';
import {QRCodeSVG} from 'qrcode.react';
const API=import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
export default function AccountSecurityPanel({enabled}) {
 const [password,setPassword]=useState(''); const [code,setCode]=useState('');
 const [setup,setSetup]=useState(null); const [result,setResult]=useState(null);
 const [error,setError]=useState(''); const [busy,setBusy]=useState(false);
 async function action(path) {
  setBusy(true);setError('');
  try {
   const r=await fetch(API+'/api/auth/security/'+path,{method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+localStorage.getItem('token')},body:JSON.stringify({password,code:code.trim()})});
   const d=await r.json();if(!r.ok)throw Error(d.detail || 'Could not update account security');
   if(path==='mfa/setup')setSetup(d);
   else {setResult(d);setSetup(null);setPassword('');setCode('');localStorage.removeItem('token');}
  }catch(e){setError(e.message);}finally{setBusy(false);}
 }
 return <Box sx={{my:3,p:3,border:'1px solid',borderColor:'divider',borderRadius:2}}>
  <Stack spacing={2}>
   <Typography variant="h6">Protect your administrator account</Typography>
   <Alert severity={enabled?'success':'warning'}>{enabled?'Authenticator protection is enabled.':'Enable an authenticator app to require a second factor at login.'}</Alert>
   {error && <Alert severity="error">{error}</Alert>}
   {result ? <><Alert severity="success">{result.message}</Alert>
    {result.recovery_codes && <><Typography>Save these one-time recovery codes in your password manager before leaving this page.</Typography><Box component="pre" sx={{userSelect:'all',whiteSpace:'pre-wrap'}}>{result.recovery_codes.join('\n')}</Box></>}
    <Button onClick={()=>window.location.reload()}>Return to sign in</Button></> : <>
    <TextField label="Current password" type="password" autoComplete="current-password" value={password} onChange={e=>setPassword(e.target.value)} />
    {(enabled || setup) && <TextField label="Authenticator or recovery code" autoComplete="one-time-code" value={code} onChange={e=>setCode(e.target.value)} />}
    {setup && <><Typography>Scan this QR with your authenticator app, then enter its six-digit code. Setup expires in 10 minutes.</Typography><Box sx={{background:'white',p:2,alignSelf:'flex-start'}}><QRCodeSVG value={setup.uri} size={180}/></Box><Typography sx={{overflowWrap:'anywhere'}}>Manual setup key: {setup.secret}</Typography><Button disabled={busy || !password || !code} onClick={()=>action('mfa/confirm')}>Enable authenticator and sign out all sessions</Button></>}
    {!enabled && !setup && <Button disabled={busy || !password} onClick={()=>action('mfa/setup')}>Set up authenticator</Button>}
    <Button color="warning" disabled={busy || !password || (enabled && !code)} onClick={()=>action('revoke-sessions')}>Sign out all devices</Button>
   </>}
  </Stack>
 </Box>;
}
