import React, { useEffect, useRef, useState } from 'react';
import { Alert, Box, Button, Card, CardContent, Chip, FormControlLabel, MenuItem, Select, Stack, Switch, TextField, Typography } from '@mui/material';
import { API, authHeaders } from '../services/api';
import { saveStaySignedIn, staySignedIn } from '../services/deviceSession';
function validFacts(data) {
  return data && data.members && Number.isInteger(data.members.active) && Array.isArray(data.events) && Array.isArray(data.updates);
}
const speechAPI = () => window.SpeechRecognition || window.webkitSpeechRecognition;
const wakePattern = /\bhey\s+(?:t\s*n\s*g|t\s*(?:and|&)\s*g)\b/i;
function persistent() {
  try {
    return !!JSON.parse(atob(localStorage.getItem('token').split('.')[1].replace(/-/g, '+').replace(/_/g, '/'))).persistent;
  } catch {
    return false;
  }
}
export default function TngAssistant({
  onWake,
  onListening
}) {
  const [facts, setFacts] = useState(null),
    [question, setQuestion] = useState(''),
    [answer, setAnswer] = useState(''),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(''),
    [status, setStatus] = useState('Ready'),
    [listening, setListening] = useState(false);
  const [event, setEvent] = useState(''),
    [speak, setSpeak] = useState(() => localStorage.getItem('tng_assistant_speak') !== 'false'),
    [autoOpen, setAutoOpen] = useState(() => localStorage.getItem('tng_assistant_open') !== 'false'),
    [remember, setRemember] = useState(persistent),
    [settingsBusy, setSettingsBusy] = useState(false);
  const alive = useRef(true),
    recognizer = useRef(null),
    wanted = useRef(false),
    mode = useRef('once'),
    waiting = useRef(false),
    pending = useRef(false),
    speaking = useRef(false),
    restart = useRef(null),
    wakeTimeout = useRef(null),
    speechVersion = useRef(0),
    lastTopic = useRef(null),
    send = useRef(null),
    eventRef = useRef(''),
    speakRef = useRef(speak),
    wakeHandler = useRef(onWake),
    listeningHandler = useRef(onListening),
    controller = useRef(null);
  eventRef.current = event;
  speakRef.current = speak;
  wakeHandler.current = onWake;
  listeningHandler.current = onListening;
  function stopVoice(clearPreference = true) {
    speechVersion.current++;
    wanted.current = false;
    waiting.current = false;
    clearTimeout(wakeTimeout.current);
    clearTimeout(restart.current);
    recognizer.current?.abort();
    window.speechSynthesis?.cancel();
    speaking.current = false;
    setListening(false);
    listeningHandler.current?.(false);
    setStatus('Ready');
    if (clearPreference) localStorage.removeItem('tng_assistant_wake');
  }
  function say(text) {
    if (!speakRef.current || !window.speechSynthesis || !alive.current || document.visibilityState !== 'visible') return;
    recognizer.current?.abort();
    speaking.current = true;
    setStatus('Speaking');
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'en-US';
    utterance.rate = 1;
    utterance.onend = utterance.onerror = () => {
      speaking.current = false;
      if (alive.current) {
        setStatus(wanted.current ? 'Listening for Hey TNG' : 'Ready');
        schedule();
      }
    };
    window.speechSynthesis.speak(utterance);
  }
  function schedule() {
    clearTimeout(restart.current);
    if (wanted.current && !pending.current && !speaking.current && document.visibilityState === 'visible') restart.current = setTimeout(() => {
      try {
        recognizer.current?.start();
      } catch {}
    }, 500);
  }
  function startVoice(handsFree = false) {
    if (!speechAPI()) {
      setError('Voice recognition is unavailable in this browser. Use Chrome on a computer or Android, or type a question.');
      return;
    }
    window.speechSynthesis?.cancel();
    speaking.current = false;
    mode.current = handsFree ? 'wake' : 'once';
    wanted.current = true;
    waiting.current = false;
    if (handsFree) localStorage.setItem('tng_assistant_wake', 'true');
    setError('');
    try {
      recognizer.current?.start();
    } catch {}
  }
  async function ask(text) {
    text = text.trim();
    if (!text || pending.current) return;
    const version = speechVersion.current;
    pending.current = true;
    setBusy(true);
    setError('');
    setQuestion(text);
    recognizer.current?.abort();
    window.speechSynthesis?.cancel();
    speaking.current = false;
    controller.current?.abort();
    const abort = new AbortController();
    controller.current = abort;
    const timeout = setTimeout(() => abort.abort(), 25000);
    try {
      const response = await fetch(`${API}/api/assistant/ask`, {
        method: 'POST',
        headers: {
          ...authHeaders(),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          question: text,
          event_id: eventRef.current ? Number(eventRef.current) : null,
          previous_topic: lastTopic.current
        }),
        signal: abort.signal
      });
      const data = await response.json();
      if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'TNG could not answer.');
      if (!validFacts(data.facts) || typeof data.answer !== 'string') throw new Error('Assistant data is unavailable. Try again.');
      if (!alive.current) return;
      setAnswer(data.answer);
      if (data.ai_notice) setError(data.ai_notice);
      setFacts(data.facts);
      lastTopic.current = data.topic;
      if (version === speechVersion.current) say(data.answer);
    } catch (e) {
      if (alive.current) setError(e.name === 'AbortError' ? 'Request timed out. Try again.' : e.message);
    } finally {
      clearTimeout(timeout);
      pending.current = false;
      if (alive.current) {
        setBusy(false);
        if (!speaking.current) schedule();
      }
    }
  }
  send.current = ask;
  useEffect(() => {
    alive.current = true;
    const abort = new AbortController();
    fetch(`${API}/api/assistant/snapshot`, {
      headers: authHeaders(),
      cache: 'no-store',
      signal: abort.signal
    }).then(async r => {
      const data = await r.json();
      if (!r.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Unable to load briefing.');
      if (!validFacts(data)) throw new Error('Assistant data is unavailable. Try again.');
      if (alive.current) {
        setFacts(data);
        setAnswer(data.briefing || 'Ask TNG for your daily briefing.');
      }
    }).catch(e => {
      if (alive.current && e.name !== 'AbortError') setError(e.message);
    });
    const Recognition = speechAPI();
    if (Recognition) {
      const r = new Recognition();
      recognizer.current = r;
      r.lang = 'en-US';
      r.continuous = true;
      r.interimResults = false;
      r.onstart = () => {
        if (!alive.current) return;
        setListening(true);
        listeningHandler.current?.(true);
        setStatus(mode.current === 'wake' && !waiting.current ? 'Listening for Hey TNG' : 'Listening for your question');
      };
      r.onresult = e => {
        for (let i = e.resultIndex; i < e.results.length; i++) {
          if (!e.results[i].isFinal) continue;
          const text = e.results[i][0].transcript.trim();
          if (!alive.current || !wanted.current || pending.current || speaking.current || document.visibilityState !== 'visible') continue;
          if (mode.current === 'once') {
            wanted.current = false;
            send.current(text);
            return;
          }
          const match = text.match(wakePattern);
          if (match) {
            wakeHandler.current?.();
            const rest = text.slice(match.index + match[0].length).replace(/^[, .:!-]+/, '').trim();
            if (rest) {
              waiting.current = false;
              send.current(rest);
            } else {
              waiting.current = true;
              setStatus('Yes—what would you like to know?');
              clearTimeout(wakeTimeout.current);
              wakeTimeout.current = setTimeout(() => {
                waiting.current = false;
                if (alive.current && wanted.current) setStatus('Listening for Hey TNG');
              }, 10000);
            }
            return;
          }
          if (waiting.current) {
            waiting.current = false;
            clearTimeout(wakeTimeout.current);
            send.current(text);
            return;
          }
        }
      };
      r.onerror = e => {
        if (['not-allowed', 'service-not-allowed', 'audio-capture', 'network'].includes(e.error)) {
          wanted.current = false;
          setListening(false);
          listeningHandler.current?.(false);
          setStatus('Voice paused');
          setError(e.error === 'network' ? 'Voice service could not connect. Type your question or retry.' : 'Microphone unavailable. Allow microphone access in your browser, then enable voice.');
        }
      };
      r.onend = () => {
        if (!alive.current) return;
        setListening(false);
        listeningHandler.current?.(false);
        schedule();
      };
      if (localStorage.getItem('tng_assistant_wake') === 'true') startVoice(true);
    }
    const visibility = () => {
      if (document.visibilityState === 'hidden') {
        recognizer.current?.abort();
        window.speechSynthesis?.cancel();
        speaking.current = false;
      } else schedule();
    };
    document.addEventListener('visibilitychange', visibility);
    return () => {
      alive.current = false;
      wanted.current = false;
      abort.abort();
      controller.current?.abort();
      clearTimeout(wakeTimeout.current);
      clearTimeout(restart.current);
      recognizer.current?.abort();
      window.speechSynthesis?.cancel();
      listeningHandler.current?.(false);
      document.removeEventListener('visibilitychange', visibility);
    };
  }, []);
  useEffect(()=>{const changed=()=>setRemember(persistent());window.addEventListener('tng-token-updated',changed);return()=>window.removeEventListener('tng-token-updated',changed);},[]);
  async function saveRemember(enabled) {
    if (settingsBusy) return;
    setSettingsBusy(true);
    setError('');
    const originalToken = localStorage.getItem('token');
    const previousChoice=staySignedIn();
    saveStaySignedIn(enabled);
    window.dispatchEvent(new Event('tng-token-updated'));
    try {
      const r = await fetch(`${API}/api/auth/${enabled ? 'remember-device' : 'forget-device'}`, {
        method: 'POST',
        headers: authHeaders()
      });
      const data = await r.json();
      if (!r.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Could not change device setting.');
      if (!alive.current || localStorage.getItem('token') !== originalToken) {
        fetch(`${API}/api/auth/logout`, {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${data.token}`
          }
        }).catch(() => {});
        return;
      }
      localStorage.setItem('token', data.token);
      saveStaySignedIn(enabled);
      window.dispatchEvent(new Event('tng-token-updated'));
      setRemember(enabled);
    } catch (e) {
      if(localStorage.getItem('token')===originalToken){saveStaySignedIn(previousChoice);window.dispatchEvent(new Event('tng-token-updated'));}
      setError(e.message);
    } finally {
      setSettingsBusy(false);
    }
  }
  return <Box sx={{
    maxWidth: 1150,
    mx: 'auto'
  }}><Stack className="tng-hero" direction="row" sx={{
      justifyContent: "space-between",
      alignItems: "center",
      mb: 3,
      p: {
        xs: 2.5,
        md: 4
      },
      gap: 2
    }}><Box><Typography variant="overline" sx={{
          color: '#80cfdb'
        }}>YOUR TNG COMMAND CENTER</Typography><Typography variant="h3" sx={{
          fontWeight: 900
        }}>Hey, TNG.</Typography><Typography sx={{
          color: '#afbed0',
          mt: 1
        }}>Your gym and promotion, ready for a conversation.</Typography></Box><Chip sx={{
        bgcolor: listening ? undefined : '#ffffff12',
        color: listening ? undefined : '#dbe7f5',
        border: '1px solid #ffffff15'
      }} color={listening ? 'success' : 'default'} label={status} /></Stack>
 {error && <Alert severity="warning" onClose={() => setError('')} sx={{
      mb: 2
    }}>{error}</Alert>}
 <Box sx={{
      display: 'grid',
      gridTemplateColumns: {
        xs: 'repeat(2,minmax(0,1fr))',
        md: 'repeat(4,minmax(0,1fr))'
      },
      gap: 2,
      mb: 2
    }}>{facts && [['Active gym members', facts.members.active], ['Expiring in 7 days', facts.members.expiring], ['Paid tickets', facts.tickets ? (facts.tickets.unknown_quantity_orders ? '≥ ' : '') + facts.tickets.paid_quantity : '—'], ['Bouts on card', facts.card?.bouts.length ?? '—']].map(([label, value]) => <Card key={label} sx={{
        flex: 1
      }}><CardContent><Typography color="text.secondary">{label}</Typography><Typography variant="h3" sx={{
            fontWeight: 900
          }}>{value}</Typography></CardContent></Card>)}</Box>
 <Card sx={{
      borderTop: '3px solid #d51f2b',
      mb: 2
    }}><CardContent><Stack spacing={2}>
 <Stack direction={{
            xs: 'column',
            sm: 'row'
          }} spacing={1}><Button variant="contained" size="large" onClick={() => startVoice(false)} disabled={busy}>Ask by voice</Button><Button variant="outlined" onClick={() => startVoice(true)} disabled={busy}>Enable “Hey TNG”</Button><Button onClick={() => stopVoice()}>Stop listening / speaking</Button></Stack>
 <Typography variant="body2" color="text.secondary">Enable voice once and allow the microphone. Say “Hey TNG” while TNGOS is open and visible. Browser voice services may process your audio; TNGOS does not save recordings. Screen-locked/background listening requires device-specific support.</Typography>
 <form onSubmit={e => {
            e.preventDefault();
            ask(question);
          }}><Stack direction={{
              xs: 'column',
              sm: 'row'
            }} spacing={1}><TextField fullWidth label="Ask TNG" value={question} inputProps={{
                maxLength: 1600
              }} onChange={e => setQuestion(e.target.value)} placeholder="How are we today?" /><Button variant="contained" type="submit" disabled={busy || !question.trim()}>{busy ? 'Checking…' : 'Ask TNG'}</Button></Stack></form>
 <Stack direction="row" flexWrap="wrap" sx={{
            gap: 1
          }}>{['How are we today?', 'How many active members?', 'How many tickets are sold?', 'How is the fight card coming?', 'What needs attention?'].map(text => <Button variant="outlined" size="small" key={text} disabled={busy} onClick={() => ask(text)}>{text}</Button>)}</Stack>
 <Typography variant="h6">{facts?.event?.name || 'TNG briefing'}</Typography><Typography sx={{
            whiteSpace: 'pre-wrap',
            lineHeight: 1.8
          }} aria-live="polite">{answer || 'Loading your live briefing…'}</Typography>
 {facts && <Typography variant="caption" color="text.secondary">Live TNGOS records · {new Date(facts.generated_at).toLocaleString('en-US', {
              timeZone: 'America/Chicago'
            })} Central · Figures reflect saved records, not a new Clover reconciliation.</Typography>}
 </Stack></CardContent></Card>
 <Card><CardContent><Typography variant="h6">Assistant & device settings</Typography><Stack spacing={1}>
 <FormControlLabel label="Speak answers aloud" control={<Switch checked={speak} onChange={e => {
            setSpeak(e.target.checked);
            localStorage.setItem('tng_assistant_speak', String(e.target.checked));
            if (!e.target.checked) {
              window.speechSynthesis?.cancel();
              speaking.current = false;
              schedule();
            }
          }} />} />
 <FormControlLabel label="Open TNG Assistant automatically after login" control={<Switch checked={autoOpen} onChange={e => {
            setAutoOpen(e.target.checked);
            localStorage.setItem('tng_assistant_open', String(e.target.checked));
          }} />} />
 <FormControlLabel label="Stay signed in on this trusted device until I log out" control={<Switch checked={remember} disabled={settingsBusy} onChange={e => saveRemember(e.target.checked)} />} />
 <Typography variant="body2" color="text.secondary">Use remembered sign-in on your own device. Password changes, account deactivation and security session revocation still end access. Public member kiosks use their separate restricted device credential.</Typography>
 <Select value={event} disabled={busy} displayEmpty onChange={e => {
            setEvent(e.target.value);
            eventRef.current = e.target.value;
            lastTopic.current = null;
            ask('How are we today?');
          }} inputProps={{
            'aria-label': 'Reporting event'
          }}><MenuItem value="">Next upcoming event (or latest saved event)</MenuItem>{facts?.events.map(e => <MenuItem key={e.id} value={String(e.id)}>{e.name} · {e.date}</MenuItem>)}</Select>
 <Typography variant="body2" color="text.secondary">The assistant reports information. It does not send messages, charge customers, alter bouts, or change memberships.</Typography>
 </Stack></CardContent></Card></Box>;
}
