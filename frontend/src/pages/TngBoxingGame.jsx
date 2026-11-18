import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Alert, Box, Button, Chip, MenuItem, Stack, TextField, Typography } from '@mui/material';
import BoxingArena from '../game/BoxingArena';
import { DRILLS, MOVES, gamepadEdges, keyboardMove, newRound, parseCombo, playMove, resumeRound, tickRound } from '../game/boxingEngine.mjs';

export default function TngBoxingGame() {
  const [drill, setDrill] = useState('signature'), [custom, setCustom] = useState('1, slip, 5, 2, 3, 2'), [combo, setCombo] = useState(DRILLS[0].moves), [duration, setDuration] = useState(120), [pace, setPace] = useState(1400), [stance, setStance] = useState('orthodox');
  const [effects, setEffects] = useState(true), [status, setStatus] = useState('ready'), [round, setRound] = useState(null), [remaining, setRemaining] = useState(120), [animation, setAnimation] = useState({}), [controller, setController] = useState('Connect a controller and press a button'), [error, setError] = useState('');
  const root = useRef(null), arena = useRef(null), live = useRef({status:'ready',round:null,combo,pace}), pausedAt = useRef(0), animTimer = useRef(null), padHistory = useRef({});
  live.current.combo = combo; live.current.pace = pace;
  const focusArena = () => arena.current?.focus({preventScroll:true});
  const changeStatus = (next, r = live.current.round) => { live.current.status=next; live.current.round=r;setStatus(next);setRound(r); };
  const pause = useCallback(() => { if(live.current.status==='running'){pausedAt.current=performance.now();changeStatus('paused');setAnimation({});clearTimeout(animTimer.current);} }, []);
  const resume = () => { if(live.current.status==='paused'){changeStatus('running',resumeRound(live.current.round,pausedAt.current,performance.now()));focusArena();} };
  const act = useCallback(move => {
    const s=live.current;if(s.status!=='running')return;
    const next=playMove(s.round,move,s.combo,performance.now(),s.pace);if(next===s.round)return;
    s.round=next;setRound(next);if(next.result==='finished'){changeStatus('finished',next);return;}
    setAnimation({move,id:performance.now(),hit:/^[1-6]$/.test(move)&&['correct','combo'].includes(next.result)});clearTimeout(animTimer.current);animTimer.current=setTimeout(()=>setAnimation({}),220);
  }, []);
  function start() {
    try { const moves=drill==='custom'?parseCombo(custom):DRILLS.find(d=>d.id===drill).moves;setCombo(moves);live.current.combo=moves;setError('');const r=newRound(performance.now(),duration);setRemaining(duration);changeStatus('running',r);setAnimation({});focusArena(); }
    catch(e){setError(e.message);}
  }
  async function fullscreen() { try{if(document.fullscreenElement)await document.exitFullscreen();else if(root.current?.requestFullscreen)await root.current.requestFullscreen();else setError('Full screen is unavailable in this browser. You can still play in this window.');}catch{setError('Full screen could not open. You can still play in this window.');} }
  useEffect(()=>{
    const key=e=>{if(!root.current?.contains(document.activeElement)||e.target.closest('input,textarea,[role="combobox"],[contenteditable="true"]')||e.ctrlKey||e.metaKey||e.altKey)return;
      const m=keyboardMove(e.key.length===1?e.key.toLowerCase():e.key);const k=e.key.toLowerCase();if(e.target.closest('button')&&e.key===' ')return;if(!m&&!['p','escape','f'].includes(k))return;e.preventDefault();if(e.repeat)return;
      if(k==='p'){if(live.current.status==='running')pause();else if(live.current.status==='paused'){changeStatus('running',resumeRound(live.current.round,pausedAt.current,performance.now()));focusArena();}}else if(k==='escape')pause();else if(k==='f')fullscreen();else if(m)act(m);
    };
    const hidden=()=>{if(document.hidden)pause();};window.addEventListener('keydown',key);window.addEventListener('blur',pause);document.addEventListener('visibilitychange',hidden);
    let frame,lastUi=0,knownPad='';
    const loop=now=>{
      const s=live.current;
      if(s.status==='running'){
        const next=tickRound(s.round,now);if(next!==s.round){s.round=next;setRound(next);if(next.result==='finished'){changeStatus('finished',next);setAnimation({});}}
        if(now-lastUi>100){setRemaining(Math.max(0,Math.ceil((s.round.endsAt-now)/1000)));lastUi=now;}
      }
      let pads=[];try{pads=navigator.getGamepads?Array.from(navigator.getGamepads()).filter(Boolean):[];}catch{}
      const pad=pads[0];const label=pad?(pad.mapping==='standard'?'Controller connected · Standard layout':'Controller not standard-mapped · Use keyboard'):'Connect a controller and press a button';if(label!==knownPad){knownPad=label;setController(label);}
      const historyKey=pad?pad.index+':'+pad.id:'';const previous=padHistory.current[historyKey];const edges=gamepadEdges(pad,previous||{});padHistory.current=pad?{[historyKey]:edges.state}:{};
      if(previous&&document.hasFocus()&&root.current?.contains(document.activeElement)&&!document.activeElement.closest('input,textarea,[role="combobox"]')){
        if(edges.pause){if(s.status==='running')pause();else if(s.status==='paused'){changeStatus('running',resumeRound(s.round,pausedAt.current,now));focusArena();}}
        else if(edges.moves.length===1)act(edges.moves[0]);
      }
      frame=requestAnimationFrame(loop);
    };frame=requestAnimationFrame(loop);
    return()=>{cancelAnimationFrame(frame);clearTimeout(animTimer.current);window.removeEventListener('keydown',key);window.removeEventListener('blur',pause);document.removeEventListener('visibilitychange',hidden);};
  },[act,pause]);
  const locked=status==='running'||status==='paused';const expected=combo[round?.index||0];
  return <Stack ref={root} spacing={2} sx={{minWidth:0,maxWidth:'100%',bgcolor:'background.default',p:{xs:0,sm:1},overflow:'auto','&:fullscreen':{p:2}}}>
    <Stack direction="row" useFlexGap sx={{justifyContent:'space-between',flexWrap:'wrap',gap:1}}><Box><Typography variant="overline" color="primary">TNG ARCADE · COMBINATION LAB</Typography><Typography variant="h4" fontWeight={900}>TNG Boxing Game</Typography><Typography color="text.secondary">Throw. Defend. Put it together.</Typography></Box><Stack direction="row" spacing={1}><Button onClick={()=>setEffects(v=>!v)} aria-pressed={effects}>{effects?'Effects on':'Low motion'}</Button><Button onClick={fullscreen}>Full screen · F</Button></Stack></Stack>
    {error&&<Alert severity="error" onClose={()=>setError('')}>{error}</Alert>}
    <Box ref={arena} tabIndex={0} aria-label="Boxing game controls. Keys 1 through 6 punch. A and D slip. S rolls. Space blocks. P pauses." sx={{border:'1px solid',borderColor:status==='running'?'primary.main':'divider',borderRadius:3,overflow:'hidden',outlineOffset:3,bgcolor:'#090e19',color:'#fff'}}>
      <Stack direction="row" useFlexGap sx={{p:2,justifyContent:'space-between',flexWrap:'wrap',gap:1}}>{[['TIME',`${Math.floor(remaining/60)}:${String(remaining%60).padStart(2,'0')}`],['SCORE',round?.points||0],['COMBOS',round?.combos||0],['ACCURACY',round?.attempts?Math.round(round.hits/round.attempts*100)+'%':'—']].map(([label,value])=><Box key={label}><Typography variant="caption" color="#99afc9">{label}</Typography><Typography fontWeight={900} fontSize={24}>{value}</Typography></Box>)}</Stack>
      <BoxingArena animation={animation} expected={expected} stance={stance} active={status==='running'} effects={effects}/>
      <Stack spacing={1.5} sx={{p:2,borderTop:'1px solid #ffffff18'}}><Stack direction="row" useFlexGap sx={{flexWrap:'wrap',gap:.75}}>{combo.map((m,i)=><Chip key={i} label={`${i+1}. ${/^[1-6]$/.test(m)?m+' · ':''}${MOVES[m].name}`} variant={i===(round?.index||0)?'filled':'outlined'} sx={{color:i<(round?.index||0)?'#7ee0be':'#fff',borderColor:i===(round?.index||0)?'#ff405e':'#536176',bgcolor:i===(round?.index||0)?'#a11733':undefined}}/>)}</Stack>
      <Typography role="status" aria-live="polite" sx={{minHeight:28,color:round?.result==='wrong'||round?.result==='timeout'?'#ffbfa3':'#91efc9',fontWeight:750}}>{status==='ready'?'Choose your drill, then start a round.':status==='paused'?'Paused. Resume when you are ready.':status==='finished'?`Round complete · ${round.combos} combinations · Best streak ${round.bestStreak}`:round?.feedback}</Typography>
      <Stack direction="row" useFlexGap sx={{gap:1,flexWrap:'wrap'}}>{!locked?<Button variant="contained" size="large" onClick={start}>{status==='finished'?'Play again':'Start round'}</Button>:<><Button variant="contained" onClick={status==='running'?pause:resume}>{status==='running'?'Pause · P':'Resume · P'}</Button><Button variant="outlined" sx={{color:'#fff',borderColor:'#71839b'}} onClick={()=>{pause();changeStatus('finished');setAnimation({});}}>End round</Button></>}<Typography variant="caption" sx={{alignSelf:'center',color:'#a9bed5'}}>Click the ring to focus · P pauses · Start / Options pauses controller play</Typography></Stack></Stack>
    </Box>
    <Box sx={{display:'grid',gridTemplateColumns:{xs:'1fr',md:'repeat(4,minmax(0,1fr))'},gap:1.5}}>
      <TextField select label="Combination drill" value={drill} disabled={locked} onChange={e=>{setDrill(e.target.value);if(e.target.value!=='custom')setCombo(DRILLS.find(d=>d.id===e.target.value).moves);setRound(null);}}>{DRILLS.map(d=><MenuItem key={d.id} value={d.id}>{d.name}</MenuItem>)}<MenuItem value="custom">Build your own</MenuItem></TextField>
      <TextField select label="Between-move window" disabled={locked} value={pace} onChange={e=>setPace(Number(e.target.value))}><MenuItem value={2200}>Learn · 2.2 seconds</MenuItem><MenuItem value={1400}>Flow · 1.4 seconds</MenuItem><MenuItem value={850}>Fast · 0.85 seconds</MenuItem></TextField>
      <TextField select label="Round length" disabled={locked} value={duration} onChange={e=>{setDuration(Number(e.target.value));setRemaining(Number(e.target.value));}}>{[60,120,180].map(n=><MenuItem key={n} value={n}>{n/60} minute{n>60?'s':''}</MenuItem>)}</TextField>
      <TextField select label="Stance" disabled={locked} value={stance} onChange={e=>setStance(e.target.value)}><MenuItem value="orthodox">Orthodox · left lead</MenuItem><MenuItem value="southpaw">Southpaw · right lead</MenuItem></TextField>
    </Box>
    {drill==='custom'&&<TextField label="Custom combination" disabled={locked} value={custom} onChange={e=>setCustom(e.target.value)} helperText="Separate moves with commas. Example: 1, slip, 5, 2, 3, 2. Slips, roll and block are supported."/>}
    <Stack spacing={1}><Typography variant="h6">Controls</Typography><Typography variant="body2" color="text.secondary">{controller}. Bluetooth or USB Xbox/PlayStation controllers use the browser’s standard layout. Press a face button after connecting. Keyboard input is active while this game is focused.</Typography>
    <Box sx={{display:'grid',gridTemplateColumns:{xs:'repeat(2,minmax(0,1fr))',sm:'repeat(5,minmax(0,1fr))'},gap:1}}>{['1','2','3','4','5','6','slipLeft','slipRight','roll','block'].map(m=><Button key={m} variant="outlined" disabled={status!=='running'} onClick={()=>{act(m);focusArena();}} sx={{display:'flex',flexDirection:'column',minHeight:76,textTransform:'none'}}><Typography fontWeight={800}>{/^[1-6]$/.test(m)?m+' · ':''}{MOVES[m].name}</Typography><Typography variant="caption">{MOVES[m].key} · {MOVES[m].button}</Typography></Button>)}</Box>
    <Typography variant="caption" color="text.secondary">1 jab · 2 cross · 3 lead hook · 4 rear hook · 5 lead uppercut · 6 rear uppercut. Lead/rear follow your selected stance. This game scores button sequence and timing; it does not assess physical punching technique. Sessions stay on this screen.</Typography></Stack>
  </Stack>;
}
