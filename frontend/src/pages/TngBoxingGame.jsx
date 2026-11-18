import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Alert, Box, Button, Chip, MenuItem, Stack, TextField, Typography } from '@mui/material';
import { DRILLS, MOVES, gamepadEdges, keyboardMove, newRound, parseCombo, playMove, resumeRound, tickRound } from '../game/boxingEngine.mjs';

function Boxer({ opponent = false, move, hit, stance }) {
  let lead = [[-5, 21], [20, 45], [52, -5]], rear = [[-29, 25], [-18, 58], [25, 5]];
  if (move === '1') lead = [[-5, 21], [67, 3], [137, -7]];
  if (move === '2') rear = [[-29, 25], [63, 15], [143, -5]];
  if (move === '3') lead = [[-5, 21], [92, -33], [126, 8]];
  if (move === '4') rear = [[-29, 25], [85, -39], [133, 8]];
  if (move === '5') lead = [[-5, 21], [56, 67], [111, -22]];
  if (move === '6') rear = [[-29, 25], [49, 72], [120, -20]];
  if (move === 'block') { lead = [[-5, 21], [43, 27], [27, -39]]; rear = [[-29, 25], [-20, 3], [-7, -40]]; }
  if (!opponent && stance === 'southpaw') [lead, rear] = [rear, lead];
  const lean = move === 'slipLeft' ? -19 : move === 'slipRight' ? 19 : move === 'roll' ? 22 : hit ? -9 : 0;
  const drop = move === 'roll' ? 36 : move?.startsWith('slip') ? 12 : 0;
  const punch = /^[1-6]$/.test(move || '');
  const color = opponent ? '#44c3e5' : '#ef354f';
  const arm = (points, key, dark = false) => <g key={key}><polyline points={points.map(p => p.join(',')).join(' ')} fill="none" stroke={dark ? '#b57c61' : '#dfa682'} strokeWidth="17" strokeLinecap="round" strokeLinejoin="round" style={{ transition: 'all 90ms ease-out' }} /><ellipse cx={points[2][0]} cy={points[2][1]} rx="23" ry="18" fill={color} stroke="#fff" strokeWidth="2"/><path d={`M${points[2][0]-10},${points[2][1]+10}h20`} stroke="#ffffff88" strokeWidth="3"/></g>;
  return <g transform={`translate(${opponent ? 480 : 310}, 216) scale(${opponent ? -1 : 1},1)`}>
    <ellipse cx="-5" cy="187" rx="65" ry="12" fill="#0009"/>
    <path d="M-25 98 L-48 160 L-59 179 M13 98 L27 155 L52 179" fill="none" stroke="#c48a69" strokeWidth="24" strokeLinecap="round"/>
    <path d="M-75 181h36M35 181h36" stroke="#101522" strokeWidth="17" strokeLinecap="round"/>
    <g style={{ transform: `translate(${hit ? -10 : 0}px,${drop}px) rotate(${lean}deg)`, transformOrigin: '0px 95px', transition: 'transform 100ms ease-out' }}>
      {arm(rear, 'rear', true)}
      <path d="M-34 12 Q-3 -3 26 17 L21 88 L-35 88Z" fill={opponent ? '#152e42' : '#251621'} stroke={color} strokeWidth="3"/>
      <path d="M-35 82H22L29 113L-6 115L-12 100L-21 115L-43 110Z" fill={color}/><path d="M-35 84H24" stroke="#fff" strokeWidth="9"/>
      <rect x="-12" y="-20" width="22" height="28" rx="7" fill="#c48a69"/>
      <ellipse cx="5" cy="-37" rx="28" ry="34" fill="#dfa682" stroke="#b57c61" strokeWidth="2"/>
      <path d="M-22 -45Q-18 -80 17 -68Q39 -61 32 -42L16 -57L-18 -39Z" fill="#121624"/><path d="M17 -39h8M11 -17h12" stroke="#38282b" strokeWidth="3"/>
      <text x="-6" y="52" fill="#fff" textAnchor="middle" fontSize="15" fontWeight="900">TNG</text>
      {arm(lead, 'lead')}
      {punch && <path d={['5','6'].includes(move) ? 'M60 95Q155 55 145 -45' : ['3','4'].includes(move) ? 'M62 -57Q175 -54 157 25' : 'M72 -17L152 -17'} fill="none" stroke={color} strokeWidth="4" opacity=".5" strokeDasharray="7 8"/>}
      {hit && <g stroke="#ffe29b" strokeWidth="4"><path d="M25 -83v-16M47 -68l15 -10M48 -40h19M-12 -82l-9 -13"/></g>}
    </g>
    <text x="0" y="224" transform={opponent ? 'scale(-1,1)' : undefined} textAnchor="middle" fill="#bfd0df" fontSize="12">{opponent ? 'TRAINING PARTNER' : stance === 'southpaw' ? 'YOU · SOUTHPAW' : 'YOU · ORTHODOX'}</text>
  </g>;
}
function Ring({ animation, expected, stance, active }) {
  const defense = ['slip','slipLeft','slipRight','roll','block'].includes(expected);
  return <svg viewBox="0 0 800 470" role="img" aria-label={`TNG boxing ring. ${animation.move ? MOVES[animation.move].name : 'Boxers in guard'}.`} style={{ width: '100%', display: 'block', maxHeight: '56vh' }}>
    <defs><linearGradient id="tng-ring-bg" x2="0" y2="1"><stop stopColor="#0b1428"/><stop offset="1" stopColor="#070a12"/></linearGradient><radialGradient id="tng-ring-light"><stop stopColor="#2d507c" stopOpacity=".55"/><stop offset="1" stopColor="#111624" stopOpacity="0"/></radialGradient></defs>
    <rect width="800" height="470" fill="url(#tng-ring-bg)"/><ellipse cx="400" cy="185" rx="385" ry="230" fill="url(#tng-ring-light)"/>
    <g opacity=".35" fill="#61718b">{Array.from({length:22},(_,i)=><circle key={i} cx={i*38} cy={115+(i%3)*12} r="11"/>)}</g>
    <path d="M55 270L745 270L790 432L10 432Z" fill="#19263a" stroke="#54657a" strokeWidth="2"/>
    <g stroke="#899ab3" strokeWidth="3" opacity=".4">{[174,207,240].map(y=><path key={y} d={`M48 ${y}H752`}/>)}</g>
    <path d="M48 159v130M752 159v130" stroke="#ef354f" strokeWidth="12"/>
    <text x="400" y="388" fill="#ffffff12" fontSize="72" textAnchor="middle" fontWeight="900">TNG BOXING</text>
    <Boxer move={animation.move} stance={stance}/><Boxer opponent move={active && defense ? '1' : 'block'} hit={animation.hit}/>
    {animation.hit&&<text x="418" y="158" textAnchor="middle" fill="#ffda87" fontWeight="900" fontSize="24">CLEAN!</text>}
    {active&&defense&&<text x="400" y="74" textAnchor="middle" fill="#70ddf2" fontSize="15" letterSpacing="3">DEFEND · {MOVES[expected].name.toUpperCase()}</text>}
  </svg>;
}
export default function TngBoxingGame() {
  const [drill, setDrill] = useState('signature'), [custom, setCustom] = useState('1, slip, 5, 2, 3, 2'), [combo, setCombo] = useState(DRILLS[0].moves), [duration, setDuration] = useState(120), [pace, setPace] = useState(1400), [stance, setStance] = useState('orthodox');
  const [status, setStatus] = useState('ready'), [round, setRound] = useState(null), [remaining, setRemaining] = useState(120), [animation, setAnimation] = useState({}), [controller, setController] = useState('Connect a controller and press a button'), [error, setError] = useState('');
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
    setAnimation({move,hit:/^[1-6]$/.test(move)&&['correct','combo'].includes(next.result)});clearTimeout(animTimer.current);animTimer.current=setTimeout(()=>setAnimation({}),220);
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
    <Stack direction="row" useFlexGap sx={{justifyContent:'space-between',flexWrap:'wrap',gap:1}}><Box><Typography variant="overline" color="primary">TNG ARCADE · COMBINATION LAB</Typography><Typography variant="h4" fontWeight={900}>TNG Boxing Game</Typography><Typography color="text.secondary">Throw. Defend. Put it together.</Typography></Box><Button onClick={fullscreen}>Full screen · F</Button></Stack>
    {error&&<Alert severity="error" onClose={()=>setError('')}>{error}</Alert>}
    <Box ref={arena} tabIndex={0} aria-label="Boxing game controls. Keys 1 through 6 punch. A and D slip. S rolls. Space blocks. P pauses." sx={{border:'1px solid',borderColor:status==='running'?'primary.main':'divider',borderRadius:3,overflow:'hidden',outlineOffset:3,bgcolor:'#090e19',color:'#fff'}}>
      <Stack direction="row" useFlexGap sx={{p:2,justifyContent:'space-between',flexWrap:'wrap',gap:1}}>{[['TIME',`${Math.floor(remaining/60)}:${String(remaining%60).padStart(2,'0')}`],['SCORE',round?.points||0],['COMBOS',round?.combos||0],['ACCURACY',round?.attempts?Math.round(round.hits/round.attempts*100)+'%':'—']].map(([label,value])=><Box key={label}><Typography variant="caption" color="#99afc9">{label}</Typography><Typography fontWeight={900} fontSize={24}>{value}</Typography></Box>)}</Stack>
      <Ring animation={animation} expected={expected} stance={stance} active={status==='running'}/>
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
