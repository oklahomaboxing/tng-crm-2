import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Alert, Box, Button, Chip, MenuItem, Stack, TextField, Typography } from '@mui/material';
import BoxingArena from '../game/BoxingArena';
import { DRILLS, gamepadEdges, keyboardMove, newRound, parseCombo, playMove, resumeRound, tickRound } from '../game/boxingEngine.mjs';
import {ALL_MOVES as MOVES,TRAINING_MODES,LEVELS,FOOTWORK_TARGETS,newTrainingRound,stepTraining,trainingInput,resumeTraining,trainingKeyboardMove,trainingGamepadEdges,trainingPose} from '../game/trainingEngine.mjs';
const resumeState=(r,paused,now)=>r?.mode?resumeTraining(r,paused,now):resumeRound(r,paused,now);

export default function TngBoxingGame() {
  const [mode,setMode]=useState('combo'),[level,setLevel]=useState('learn');
  const [drill, setDrill] = useState('signature'), [custom, setCustom] = useState('1, slip, 5, 2, 3, 2'), [combo, setCombo] = useState(DRILLS[0].moves), [duration, setDuration] = useState(120), [pace, setPace] = useState(1400), [stance, setStance] = useState('orthodox');
  const [effects, setEffects] = useState(true), [status, setStatus] = useState('ready'), [round, setRound] = useState(null), [remaining, setRemaining] = useState(120), [animation, setAnimation] = useState({}), [controller, setController] = useState('Connect a controller and press a button'), [error, setError] = useState('');
  const root = useRef(null), arena = useRef(null), live = useRef({status:'ready',round:null,combo,pace}), pausedAt = useRef(0), animTimer = useRef(null), padHistory = useRef({});
  live.current.combo = combo; live.current.pace = pace;
  const focusArena = () => arena.current?.focus({preventScroll:true});
  const changeStatus = (next, r = live.current.round) => { live.current.status=next; live.current.round=r;setStatus(next);setRound(r); };
  const pause = useCallback(() => { if(live.current.status==='running'){pausedAt.current=performance.now();changeStatus('paused');if(!live.current.round?.mode)setAnimation({});clearTimeout(animTimer.current);} }, []);
  const resume = () => { if(live.current.status==='paused'){changeStatus('running',resumeState(live.current.round,pausedAt.current,performance.now()));focusArena();} };
  const act = useCallback(move => {
    const s=live.current;if(s.status!=='running')return;
    const now=performance.now();const next=s.round.mode?trainingInput(s.round,move,now):playMove(s.round,move,s.combo,now,s.pace);if(next===s.round)return;
    s.round=next;setRound(next);if(next.result==='finished'){changeStatus('finished',next);return;}
    if(next.mode){setAnimation(trainingPose(next,now));return;}
    setAnimation({move,id:performance.now(),hit:/^[1-6]$/.test(move)&&['correct','combo'].includes(next.result)});clearTimeout(animTimer.current);animTimer.current=setTimeout(()=>setAnimation({}),220);
  }, []);
  function start() {
    try { const moves=mode==='combo'?(drill==='custom'?parseCombo(custom):DRILLS.find(d=>d.id===drill).moves):combo;setCombo(moves);live.current.combo=moves;setError('');const r=mode==='combo'?newRound(performance.now(),duration):newTrainingRound(performance.now(),duration,mode,level);setRemaining(duration);changeStatus('running',r);setAnimation({});focusArena(); }
    catch(e){setError(e.message);}
  }
  async function fullscreen() { try{if(document.fullscreenElement)await document.exitFullscreen();else if(root.current?.requestFullscreen)await root.current.requestFullscreen();else setError('Full screen is unavailable in this browser. You can still play in this window.');}catch{setError('Full screen could not open. You can still play in this window.');} }
  useEffect(()=>{
    const key=e=>{if(!root.current?.contains(document.activeElement)||e.target.closest('input,textarea,[role="combobox"],[contenteditable="true"]')||e.ctrlKey||e.metaKey||e.altKey)return;
      const m=(live.current.round?.mode?trainingKeyboardMove:keyboardMove)(e.key.length===1?e.key.toLowerCase():e.key);const k=e.key.toLowerCase();if(e.target.closest('button')&&e.key===' ')return;if(!m&&!['p','escape','f'].includes(k))return;e.preventDefault();if(e.repeat)return;
      if(k==='p'){if(live.current.status==='running')pause();else if(live.current.status==='paused'){changeStatus('running',resumeState(live.current.round,pausedAt.current,performance.now()));focusArena();}}else if(k==='escape')pause();else if(k==='f')fullscreen();else if(m)act(m);
    };
    const hidden=()=>{if(document.hidden)pause();};window.addEventListener('keydown',key);window.addEventListener('blur',pause);document.addEventListener('visibilitychange',hidden);
    let frame,lastUi=0,knownPad='';
    const loop=now=>{
      const s=live.current;
      if(s.status==='running'){
        const next=s.round.mode?stepTraining(s.round,now):tickRound(s.round,now);if(next!==s.round){s.round=next;if(!next.mode||now-lastUi>80)setRound(next);if(next.result==='finished'){changeStatus('finished',next);setAnimation({});}}
        if(now-lastUi>100){if(s.round.mode){setRound(s.round);setAnimation(trainingPose(s.round,now));}setRemaining(Math.max(0,Math.ceil((s.round.endsAt-now)/1000)));lastUi=now;}
      }
      let pads=[];try{pads=navigator.getGamepads?Array.from(navigator.getGamepads()).filter(Boolean):[];}catch{}
      const pad=pads[0];const label=pad?(pad.mapping==='standard'?'Controller connected · Standard layout':'Controller not standard-mapped · Use keyboard'):'Connect a controller and press a button';if(label!==knownPad){knownPad=label;setController(label);}
      const historyKey=pad?pad.index+':'+pad.id:'';const previous=padHistory.current[historyKey];const edges=(s.round?.mode?trainingGamepadEdges:gamepadEdges)(pad,previous||{});padHistory.current=pad?{[historyKey]:edges.state}:{};
      if(previous&&document.hasFocus()&&root.current?.contains(document.activeElement)&&!document.activeElement.closest('input,textarea,[role="combobox"]')){
        if(edges.pause){if(s.status==='running')pause();else if(s.status==='paused'){changeStatus('running',resumeState(s.round,pausedAt.current,now));focusArena();}}
        else if(edges.moves.length===1)act(edges.moves[0]);
      }
      frame=requestAnimationFrame(loop);
    };frame=requestAnimationFrame(loop);
    return()=>{cancelAnimationFrame(frame);clearTimeout(animTimer.current);window.removeEventListener('keydown',key);window.removeEventListener('blur',pause);document.removeEventListener('visibilitychange',hidden);};
  },[act,pause]);
  const locked=status==='running'||status==='paused';const expected=combo[round?.index||0];const simulation=mode!=='combo';
  return <Stack ref={root} spacing={2} sx={{minWidth:0,maxWidth:'100%',bgcolor:'background.default',p:{xs:0,sm:1},overflow:'auto','&:fullscreen':{p:2}}}>
    <Stack direction="row" useFlexGap sx={{justifyContent:'space-between',flexWrap:'wrap',gap:1}}><Box><Typography variant="overline" color="primary">TNG TRAINING ARENA</Typography><Typography variant="h4" fontWeight={900}>TNG Boxing Game</Typography><Typography color="text.secondary">Throw. Defend. Put it together.</Typography></Box><Stack direction="row" spacing={1}><Button onClick={()=>setEffects(v=>!v)} aria-pressed={effects}>{effects?'Effects on':'Low motion'}</Button><Button onClick={fullscreen}>Full screen · F</Button></Stack></Stack>
    <Box sx={{display:'grid',gridTemplateColumns:{xs:'1fr',sm:'repeat(2,minmax(0,1fr))'},gap:1.5}}><TextField select label="Training mode" value={mode} disabled={locked} onChange={e=>{setMode(e.target.value);changeStatus('ready',null);setAnimation({});setRemaining(duration);padHistory.current={};}}>{TRAINING_MODES.map(m=><MenuItem key={m.id} value={m.id}>{m.name}</MenuItem>)}</TextField><TextField select label="Partner difficulty" value={level} disabled={locked||!simulation} onChange={e=>setLevel(e.target.value)}>{Object.entries(LEVELS).map(([id,l])=><MenuItem key={id} value={id}>{l.name}</MenuItem>)}</TextField></Box><Typography color="text.secondary">{TRAINING_MODES.find(m=>m.id===mode).description}</Typography>
    {error&&<Alert severity="error" onClose={()=>setError('')}>{error}</Alert>}
    <Box ref={arena} tabIndex={0} aria-label="Boxing game controls. Keys 1 through 6 punch. A and D slip. S rolls. Space blocks. P pauses." sx={{border:'1px solid',borderColor:status==='running'?'primary.main':'divider',borderRadius:3,overflow:'hidden',outlineOffset:3,bgcolor:'#090e19',color:'#fff'}}>
      <Stack direction="row" useFlexGap sx={{p:2,justifyContent:'space-between',flexWrap:'wrap',gap:1}}>{[['TIME',`${Math.floor(remaining/60)}:${String(remaining%60).padStart(2,'0')}`],['SCORE',round?.points||0],[simulation?(mode==='footwork'?'POSITIONS':mode==='bag'?'CLEAN HITS':'DEFENSES'):'COMBOS',simulation?(mode==='footwork'?round?.footworkGoals||0:mode==='bag'?round?.hits||0:round?.defenses||0):round?.combos||0],['ACCURACY',round?.attempts?Math.round(round.hits/round.attempts*100)+'%':'—']].map(([label,value])=><Box key={label}><Typography variant="caption" color="#99afc9">{label}</Typography><Typography fontWeight={900} fontSize={24}>{value}</Typography></Box>)}</Stack>
      {simulation&&<Box sx={{display:'grid',gridTemplateColumns:{xs:'repeat(2,minmax(0,1fr))',sm:'repeat(4,minmax(0,1fr))'},gap:1,p:2,pt:0}}>{[['Stamina',Math.round(round?.stamina??100)+'%'],[mode==='footwork'?'Angle':mode==='bag'?'Punches thrown':'Your condition',mode==='footwork'?((round?.angle||0)<-.3?'Left':(round?.angle||0)>.3?'Right':'Center'):mode==='bag'?round?.attempts||0:Math.round(round?.playerHealth??100)+'%'],['Range',(round?.distance??1.4)>1.85?'Outside':(round?.distance??1.4)<1.2?'Inside':'Straight punches'],[mode==='sparring'?'Partner condition':mode==='footwork'?'Target':'Counters',mode==='sparring'?Math.round(round?.opponentHealth??100)+'%':mode==='footwork'?FOOTWORK_TARGETS[(round?.targetIndex||0)%4].name:round?.counters||0]].map(([label,value])=><Box key={label}><Typography variant="caption" color="#a9bed5">{label}</Typography><Typography fontWeight={800}>{value}</Typography></Box>)}</Box>}
      <BoxingArena animation={simulation?{...animation,mode}:animation} expected={expected} stance={stance} active={status==='running'} effects={effects}/>
      <Stack spacing={1.5} sx={{p:2,borderTop:'1px solid #ffffff18'}}><Stack direction="row" useFlexGap sx={{flexWrap:'wrap',gap:.75}}>{!simulation&&combo.map((m,i)=><Chip key={i} label={`${i+1}. ${/^[1-6]$/.test(m)?m+' · ':''}${MOVES[m].name}`} variant={i===(round?.index||0)?'filled':'outlined'} sx={{color:i<(round?.index||0)?'#7ee0be':'#fff',borderColor:i===(round?.index||0)?'#ff405e':'#536176',bgcolor:i===(round?.index||0)?'#a11733':undefined}}/>)}</Stack>
      <Typography role="status" aria-live="polite" sx={{minHeight:28,color:round?.result==='wrong'||round?.result==='timeout'?'#ffbfa3':'#91efc9',fontWeight:750}}>{status==='ready'?'Choose your drill, then start a round.':status==='paused'?'Paused. Resume when you are ready.':status==='finished'?(simulation?round?.feedback:`Round complete · ${round.combos} combinations · Best streak ${round.bestStreak}`):round?.feedback}</Typography>
      <Stack direction="row" useFlexGap sx={{gap:1,flexWrap:'wrap'}}>{!locked?<Button variant="contained" size="large" onClick={start}>{status==='finished'?'Play again':'Start round'}</Button>:<><Button variant="contained" onClick={status==='running'?pause:resume}>{status==='running'?'Pause · P':'Resume · P'}</Button><Button variant="outlined" sx={{color:'#fff',borderColor:'#71839b'}} onClick={()=>{pause();changeStatus('finished',{...live.current.round,result:'finished',feedback:'Round ended. Review your accuracy, defense and stamina.'});setAnimation({});}}>End round</Button></>}<Typography variant="caption" sx={{alignSelf:'center',color:'#a9bed5'}}>Click the ring to focus · P pauses · Start / Options pauses controller play</Typography></Stack></Stack>
    </Box>
    <Box sx={{display:'grid',gridTemplateColumns:{xs:'1fr',md:simulation?'repeat(2,minmax(0,1fr))':'repeat(4,minmax(0,1fr))'},gap:1.5}}>
      {!simulation&&<><TextField select label="Combination drill" value={drill} disabled={locked||simulation} onChange={e=>{setDrill(e.target.value);if(e.target.value!=='custom')setCombo(DRILLS.find(d=>d.id===e.target.value).moves);setRound(null);}}>{DRILLS.map(d=><MenuItem key={d.id} value={d.id}>{d.name}</MenuItem>)}<MenuItem value="custom">Build your own</MenuItem></TextField>
      <TextField select label="Between-move window" disabled={locked||simulation} value={pace} onChange={e=>setPace(Number(e.target.value))}><MenuItem value={2200}>Learn · 2.2 seconds</MenuItem><MenuItem value={1400}>Flow · 1.4 seconds</MenuItem><MenuItem value={850}>Fast · 0.85 seconds</MenuItem></TextField></>}
      <TextField select label="Round length" disabled={locked} value={duration} onChange={e=>{setDuration(Number(e.target.value));setRemaining(Number(e.target.value));}}>{[60,120,180].map(n=><MenuItem key={n} value={n}>{n/60} minute{n>60?'s':''}</MenuItem>)}</TextField>
      <TextField select label="Stance" disabled={locked} value={stance} onChange={e=>setStance(e.target.value)}><MenuItem value="orthodox">Orthodox · left lead</MenuItem><MenuItem value="southpaw">Southpaw · right lead</MenuItem></TextField>
    </Box>
    {!simulation&&drill==='custom'&&<TextField label="Custom combination" disabled={locked} value={custom} onChange={e=>setCustom(e.target.value)} helperText="Separate moves with commas. Example: 1, slip, 5, 2, 3, 2. Slips, roll and block are supported."/>}
    <Stack spacing={1}><Typography variant="h6">Controls</Typography><Typography variant="body2" color="text.secondary">{controller}. Bluetooth or USB Xbox/PlayStation controllers use the browser’s standard layout. Press a face button after connecting. Keyboard input is active while this game is focused.</Typography>
    <Box sx={{display:'grid',gridTemplateColumns:{xs:'repeat(2,minmax(0,1fr))',sm:'repeat(5,minmax(0,1fr))'},gap:1}}>{(mode==='footwork'?['stepIn','stepOut','pivotLeft','pivotRight']:['1','2','3','4','5','6','slipLeft','slipRight','roll','block',...(simulation?['bodyBlock','stepIn','stepOut','pivotLeft','pivotRight']:[])]).map(m=><Button key={m} variant="outlined" disabled={status!=='running'} onClick={()=>{act(m);focusArena();}} sx={{display:'flex',flexDirection:'column',minHeight:76,textTransform:'none'}}><Typography fontWeight={800}>{/^[1-6]$/.test(m)?m+' · ':''}{MOVES[m].name}</Typography><Typography variant="caption">{MOVES[m].key} · {MOVES[m].button}</Typography></Button>)}</Box>
    <Typography variant="caption" color="text.secondary">1 jab · 2 cross · 3 lead hook · 4 rear hook · 5 lead uppercut · 6 rear uppercut. Lead/rear follow your selected stance. Combination Lab scores sequences; the other modes model range, stamina, guard and recovery. W steps in, Z steps out, Q/E pivot and C guards the body. On controllers use the right stick for footwork and left-stick click for body guard. This game does not assess physical punching technique. Sessions stay on this screen.</Typography></Stack>
  </Stack>;
}
