import React, { useEffect, useRef, useState } from 'react';
import './CheckinKiosk.css';
import { QRCodeSVG } from 'qrcode.react';
const SIGNUP_URL = 'https://tngos.tngboxinggym.com/register';
const API = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
const KEY = 'tng_checkin_kiosk_device';
export default function CheckinKiosk({ staffMode = false, onExit }) {
  const [credential, setCredential] = useState(() => staffMode ? '' : localStorage.getItem(KEY) || '');
  const [setupCode]=useState(()=>new URLSearchParams(window.location.hash.slice(1)).get('pair')||'');
  const [pairCode, setPairCode] = useState(setupCode);
  const [enrollment,setEnrollment]=useState(!!setupCode);
  const [number, setNumber] = useState('');
  const [settings, setSettings] = useState(staffMode ? {enabled:true,confirmation_seconds:8} : null);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [connection, setConnection] = useState(staffMode ? 'Connected — staff check-in' : 'Connecting…');
  const [install, setInstall] = useState(null);
  const [seconds, setSeconds] = useState(0);
  const lock = useRef(false), wake = useRef(null), mounted = useRef(true), field = useRef(null);
  async function request(path, body, token = credential) {
    const controller = new AbortController(), timeout = setTimeout(() => controller.abort(), 12000);
    try {
      const response = await fetch(staffMode && path === 'checkin' ? `${API}/api/checkin` : `${API}/api/kiosk/${path}`, {method: 'POST', cache: 'no-store',
        headers: {'Content-Type': 'application/json', ...((staffMode ? localStorage.getItem('token') : token) ? {Authorization: `Bearer ${staffMode ? localStorage.getItem('token') : token}`} : {})},
        body: JSON.stringify(staffMode && path === 'checkin' ? {code:body.member_number,entry_method:'member_number'} : body || {}), signal: controller.signal});
      let data;try {data=await response.json();}catch {throw new Error('Unable to connect. Please visit the front desk or try again.');}
      if (!staffMode && response.status === 401 && token) { localStorage.removeItem(KEY); setCredential(''); setSettings(null); }
      if (!response.ok) {
        const error=new Error(typeof data.detail==='string'?data.detail:'Unable to check in. Please visit the front desk.');
        if(staffMode && response.status===403 && typeof data.detail==='string' && data.detail.startsWith('Membership is inactive or expired')) error.code='membership_inactive';
        throw error;
      }
      if(staffMode && path==='checkin') return {success:true,duplicate:!!data.duplicate,recorded:!data.duplicate,first_name:data.member.first_name || data.member.name.split(' ')[0],confirmation_seconds:8,status:'active',message:data.duplicate?'You are already checked in. No duplicate attendance recorded.':'Attendance recorded.'};
      return data;
    } finally { clearTimeout(timeout); }
  }
  function reset() { setResult(null); setNumber(''); setSeconds(0); }
  function clearCrmSession() {
    for (const key of ['token', 'role', 'name']) localStorage.removeItem(key);
    for (const key of ['fighterPreviewToken', 'memberPreviewToken']) sessionStorage.removeItem(key);
  }
  useEffect(() => {
    mounted.current = true;
    if(new URLSearchParams(window.location.hash.slice(1)).has('pair'))window.history.replaceState(null,'',window.location.pathname+window.location.search);
    const manifest = document.createElement('link'); manifest.rel = 'manifest'; manifest.href = '/kiosk/checkin.webmanifest'; document.head.appendChild(manifest);
    const meta = document.createElement('meta'); meta.name = 'theme-color'; meta.content = '#08090b'; document.head.appendChild(meta);
    if ('serviceWorker' in navigator) navigator.serviceWorker.register('/kiosk/sw.js', {scope: '/kiosk/'}).catch(() => {});
    const prompt = event => { event.preventDefault(); setInstall(event); };
    window.addEventListener('beforeinstallprompt', prompt);
    async function keepAwake() { if (document.visibilityState === 'visible') { try { if (!wake.current || wake.current.released) wake.current = await navigator.wakeLock?.request('screen'); } catch {} } }
    keepAwake(); document.addEventListener('visibilitychange', keepAwake);
    return () => {mounted.current = false; manifest.remove(); meta.remove(); window.removeEventListener('beforeinstallprompt', prompt); document.removeEventListener('visibilitychange', keepAwake); wake.current?.release();};
  }, []);
  useEffect(() => {
    if (staffMode || !credential) return;
    clearCrmSession();
    let active = true;
    async function ping() {
      try { const data = await request('heartbeat'); if (active) {setSettings(data); setConnection('Connected');} }
      catch { if (active) {setSettings(null); setConnection('Connection unavailable — please visit the front desk');} }
    }
    ping(); const timer = setInterval(ping, 30000);
    const visible = () => {if (document.visibilityState === 'visible') {reset(); ping();}};
    document.addEventListener('visibilitychange', visible);
    return () => {active = false; clearInterval(timer); document.removeEventListener('visibilitychange', visible);};
  }, [credential, staffMode]);
  useEffect(() => {
    if (!result) return;
    const duration = result.success ? (result.confirmation_seconds || 8) : 5;
    setSeconds(duration);
    const end = Date.now() + duration * 1000;
    const ticker = setInterval(() => setSeconds(Math.max(0, Math.ceil((end - Date.now()) / 1000))), 250);
    const timer = setTimeout(reset, duration * 1000);
    return () => {clearInterval(ticker); clearTimeout(timer);};
  }, [result]);
  useEffect(() => {
    if (!number || busy || result) return;
    const timer = setTimeout(() => setNumber(''), 30000);
    return () => clearTimeout(timer);
  }, [number, busy, result]);
  async function pair(event) {
    event.preventDefault(); if (lock.current) return; lock.current = true; setBusy(true);
    try {const data = await request('pair', {code: pairCode.trim()}, ''); localStorage.setItem(KEY, data.credential); clearCrmSession(); setCredential(data.credential); setEnrollment(false); setPairCode(''); reset();}
    catch (error) {setResult({success: false, message: error.message || 'Pairing failed.'});}
    finally {lock.current = false; if (mounted.current) setBusy(false);}
  }
  async function checkin(event) {
    event.preventDefault(); if (lock.current || !number || !settings?.enabled) return;
    lock.current = true; setBusy(true);
    try {const data = await request('checkin', {member_number: number}); if (mounted.current) {setNumber(''); setResult(data);}}
    catch (error) {if (mounted.current) {setNumber(''); setResult({success: false, code:error.code, message: error.name === 'AbortError' ? 'Connection timed out. Please try again or visit the front desk.' : error.message});}}
    finally {lock.current = false; if (mounted.current) setBusy(false);}
  }
  function key(value) {if (busy) return; setNumber(previous => value === 'clear' ? '' : value === 'back' ? previous.slice(0, -1) : (previous + value).slice(0, 32));}
  return <main className="tng-kiosk">
    <header><img src="/tng-ticket-logo.jpg" alt="TNG Boxing"/><p className="kiosk-tagline">THE NEXT GENERATION</p></header>
    <div className="kiosk-tools">{staffMode && onExit && <button onClick={onExit}>Back to TNGOS</button>}<button onClick={async () => {try {await document.documentElement.requestFullscreen?.(); if (!wake.current || wake.current.released) wake.current = await navigator.wakeLock?.request('screen');} catch {}}}>Full screen</button>{install && <button onClick={async () => {await install.prompt(); setInstall(null);}}>Install kiosk</button>}</div>
    {result ? <section className={`kiosk-result ${result.success ? 'kiosk-success' : 'kiosk-error'}`} aria-live="assertive">
      <div className="kiosk-result-icon" aria-hidden="true">{result.success ? '✓' : '!'}</div>
      <h1>{result.success ? (result.duplicate ? 'ALREADY CHECKED IN' : 'CHECK-IN SUCCESSFUL') : result.code === 'membership_inactive' ? 'MEMBERSHIP INACTIVE' : 'PLEASE TRY AGAIN'}</h1>
      {result.success && <><h2>WELCOME BACK, {result.first_name}!</h2><p className="kiosk-status">Membership: Active</p></>}
      <p>{result.code === 'membership_inactive' ? 'Please visit the front desk.' : result.message}</p><button className="kiosk-submit" onClick={reset}>Next Member</button><p className="kiosk-countdown">Clearing in {seconds} seconds</p>
    </section> : (!credential || enrollment) && !staffMode ? <section className="kiosk-pair"><h1>TNG BOXING CHECK-IN</h1><p>Staff: pair this device using the code from TNGOS → Check-In Kiosk. Pairing signs this browser out of TNGOS administration. No admin sign-in is needed on this screen.</p><form onSubmit={pair}><label htmlFor="pair-code">Device pairing code</label><input id="pair-code" autoComplete="off" autoCapitalize="characters" value={pairCode} onChange={e => setPairCode(e.target.value)} maxLength={32}/><button className="kiosk-submit" disabled={busy || pairCode.trim().length < 8}>{busy ? 'Connecting…' : 'Connect kiosk'}</button></form>{credential&&<button onClick={()=>{setEnrollment(false);setPairCode('');}}>Keep current connection</button>}</section>
    : !settings?.enabled ? <section aria-live="polite"><h1>{settings ? 'CHECK-IN UNAVAILABLE' : 'CONNECTING TO TNG BOXING'}</h1><p>{settings ? 'Please visit the front desk.' : connection}</p></section>
    : <section><h1>WELCOME TO TNG BOXING<span>MEMBER CHECK-IN</span></h1><form onSubmit={checkin}>
      <label htmlFor="member-number">Enter your membership number</label>
      <input ref={field} id="member-number" value={number} readOnly inputMode="none" autoComplete="off" placeholder="MEMBER NUMBER" aria-describedby="kiosk-number-help" onKeyDown={event => {if (/^[0-9]$/.test(event.key)) {event.preventDefault(); key(event.key);} else if (event.key === 'Backspace') {event.preventDefault(); key('back');} else if (event.key === 'Escape') key('clear');}}/>
      <p id="kiosk-number-help" className="kiosk-help">Use the keypad below. Keep any leading zeros.</p>
      <div className="kiosk-keypad">{['1','2','3','4','5','6','7','8','9','clear','0','back'].map(value => <button key={value} type="button" disabled={busy} onClick={() => key(value)} aria-label={value === 'back' ? 'Backspace' : value === 'clear' ? 'Clear number' : value}>{value === 'back' ? '⌫' : value === 'clear' ? 'CLEAR' : value}</button>)}</div>
      <button className="kiosk-submit" disabled={busy || !number}>{busy ? 'CHECKING IN…' : 'CHECK IN'}</button>
    </form></section>}
    {!result && <aside className="kiosk-join" aria-label="New member signup">
      <div className="kiosk-join-qr"><QRCodeSVG value={SIGNUP_URL} size={192} level="M" marginSize={4} title="Scan with your phone to sign up for TNG Boxing"/></div>
      <div><h2>NOT A MEMBER YET?</h2><p>Scan to join TNG Boxing</p><small>Use your phone camera to register, sign the waiver and choose your membership.</small><span>tngos.tngboxinggym.com/register</span></div>
    </aside>}
    <footer><span>TNG BOXING · MEMBER CHECK-IN</span><span>{credential || staffMode ? connection : 'Device setup'}</span><small>Need help? Visit the front desk.</small></footer>
  </main>;
}
