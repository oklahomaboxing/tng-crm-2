import React, { useId } from 'react';
import { ALL_MOVES as MOVES } from './trainingEngine.mjs';
import './boxingArena.css';

function Fighter({ opponent = false, move, hit, stance, paint, actionId, x, y=218 }) {
  let lead = [[-7, 18], [20, 46], [54, -7]], rear = [[-30, 23], [-21, 55], [26, 0]];
  if (move === '1') lead = [[-7,18],[65,0],[137,-9]];
  if (move === '2') rear = [[-30,23],[62,14],[143,-7]];
  if (move === '3') lead = [[-7,18],[89,-34],[126,7]];
  if (move === '4') rear = [[-30,23],[84,-39],[133,7]];
  if (move === '5') lead = [[-7,18],[54,66],[111,-24]];
  if (move === '6') rear = [[-30,23],[49,72],[120,-22]];
  if (move === 'bodyBlock') { lead=[[-7,18],[45,56],[20,55]];rear=[[-30,23],[-40,45],[-7,51]]; }
  if (move === 'block') { lead=[[-7,18],[44,26],[28,-42]];rear=[[-30,23],[-21,2],[-7,-43]]; }
  if (!opponent && stance === 'southpaw') [lead,rear]=[rear,lead];
  const lean = move==='slipLeft'?-19:move==='slipRight'?19:move==='roll'?22:hit?-9:['2','4','6'].includes(move)?7:move==='pivotLeft'?-6:move==='pivotRight'?6:0;
  const drop = move==='roll'?34:move?.startsWith('slip')?12:0;
  const kit = opponent?'blue':'red', skin=opponent?'darkSkin':'skin';
  const color=opponent?'#50d5ff':'#ff3c5f';
  const arm=(points,key,back=false)=>{
    const leadPunch=['1','3','5'].includes(move);
    const punching=/^[1-6]$/.test(move||'') && key===(!opponent&&stance==='southpaw'?(leadPunch?'rear':'lead'):(leadPunch?'lead':'rear'));
    return <g key={punching?`${key}-${actionId}`:key} className={`tng-boxing-arm ${punching?'tng-boxing-active-arm':''}`}>
    <polyline points={points.map(p=>p.join(',')).join(' ')} fill="none" stroke={opponent?'#452b28':'#794332'} strokeWidth="24" strokeLinecap="round" strokeLinejoin="round"/>
    <polyline points={points.map(([x,y])=>`${x-2},${y-3}`).join(' ')} fill="none" stroke={paint(skin)} strokeWidth={back?16:19} strokeLinecap="round" strokeLinejoin="round"/>
    <ellipse cx={points[0][0]} cy={points[0][1]} rx="15" ry="19" fill={paint(skin)}/>
    <g transform={`translate(${points[2][0]},${points[2][1]})`}>
      <rect x="-25" y="-8" width="14" height="25" rx="4" fill="#e0e9ed" stroke="#9daeb9" strokeWidth="1.5"/>
      <ellipse cx="0" cy="-1" rx="24" ry="20" fill={paint(kit)} stroke={opponent?'#9ce9ff':'#ffadad'} strokeWidth="1.5"/>
      <path d="M-13 -13Q1 -20 13 -10" stroke="#fff" strokeOpacity=".55" strokeWidth="3" fill="none" strokeLinecap="round"/>
      <path d="M-13 10Q2 17 17 7M-9 -3Q-5 4 -9 9" stroke="#000" strokeOpacity=".3" strokeWidth="2" fill="none"/>
      <rect x="-8" y="8" width="16" height="6" rx="2" fill="#101824"/>
      <text y="13" textAnchor="middle" transform={opponent?'scale(-1,1)':undefined} fontSize="4.5" fill="#fff" fontWeight="900">TNG</text>
    </g>
  </g>; };
  const punch=/^[1-6]$/.test(move||'');
  return <g data-boxer={opponent?'partner':'player'} transform={`translate(${x??(opponent?486:304)},${y}) scale(${opponent?-1:1},1)`}>
    <ellipse cx="-8" cy="183" rx="77" ry="15" fill="#000" opacity=".45"/>
    <ellipse cx="-8" cy="184" rx="60" ry="4" fill={color} opacity=".12"/>
    <g className="tng-boxing-stance">
      <path d="M-25 96Q-39 123 -45 149L-58 171M12 96Q18 128 28 152L49 173" stroke="#30242a" strokeWidth="29" strokeLinecap="round" fill="none"/>
      <path d="M-25 96Q-39 123 -45 149L-58 171M12 96Q18 128 28 152L49 173" stroke={paint(skin)} strokeWidth="23" strokeLinecap="round" fill="none"/>
      <path d="M-45 147l-10 25M28 150l15 22" stroke="#121b2c" strokeWidth="28"/>
      <path d="M-56 156L-66 175L-79 178Q-84 187 -70 188L-39 185L-38 179L-42 160M32 157L39 176L57 178Q68 185 58 188L29 184L24 173L20 162" fill={paint('boot')} stroke="#758397" strokeWidth="1.5"/>
      <path d="M-63 164l17 -2M-66 171l16 -2M27 163l13 3M31 170l13 3M-78 185l36 -3M30 182l29 3" stroke="#d3dde7" strokeWidth="2"/>
      <g className="tng-boxing-body" style={{transform:`translate(${hit?-10:0}px,${drop}px) rotate(${lean}deg)`}}>
        {arm(rear,'rear',true)}
        <path d="M-37 17Q-29 -1 -12 -4L6 -3Q25 0 28 23L20 78L-35 79L-43 48Z" fill={paint(skin)} stroke="#3b2329" strokeWidth="2"/>
        <path d="M-30 22Q-10 12 9 22M-8 32L-9 62M-27 45Q-16 49 -10 45M-5 45Q6 49 14 43M-26 58Q-16 62 -10 58M-4 58Q6 62 13 56" fill="none" stroke="#4f302c" strokeOpacity=".4" strokeWidth="2"/>
        <path d="M-36 19Q-41 41 -32 71M22 17L17 68" fill="none" stroke="#ffe0bd" strokeOpacity=".23" strokeWidth="3"/>
        <path d="M-36 76H21L30 111L-5 114L-12 99L-22 115L-45 109Z" fill={paint(kit)} stroke="#141c2c" strokeWidth="2"/>
        <path d="M-35 79H22" stroke="#e8e9ea" strokeWidth="10"/>
        <path d="M-32 86L-39 106M17 86L23 106" stroke="#fff" strokeOpacity=".55" strokeWidth="3"/>
        <rect x="-17" y="75" width="18" height="9" rx="2" fill="#111a29"/>
        <text x={opponent?8:-8} y="82" transform={opponent?'scale(-1,1)':undefined} fontSize="6" textAnchor="middle" fill="#fff" fontWeight="900">TNG</text>
        <path d="M-12 -25L-11 -6Q1 5 12 -6L14 -28" fill={paint(skin)} stroke="#5f3930" strokeWidth="1.5"/>
        <path d="M-22 -55Q-13 -79 13 -72Q34 -69 35 -43L29 -20L15 -8L-5 -12L-19 -30Z" fill={paint(skin)} stroke={opponent?'#452b28':'#91523c'} strokeWidth="1.5"/>
        <ellipse cx="-20" cy="-35" rx="6" ry="10" fill={paint(skin)}/>
        <path d={opponent?'M-23 -47Q-23 -76 7 -77Q39 -78 36 -45L24 -56L-4 -60Z':'M-23 -45Q-26 -74 5 -78Q33 -77 37 -54L24 -48L11 -60L-6 -51Z'} fill="#14151c"/>
        <path d="M15 -43l13 1M18 -38h6M26 -37l5 11l-8 2M12 -17q8 4 13 -2" fill="none" stroke="#35252b" strokeWidth="2" strokeLinecap="round"/>
        <path d="M4 -52Q15 -58 25 -51M-8 -34L-3 -22" stroke="#fff" strokeOpacity=".2" fill="none" strokeWidth="3"/>
        {arm(lead,'lead')}
        {punch&&<g className="tng-boxing-trail" fill="none" stroke={color} strokeLinecap="round"><path d={['5','6'].includes(move)?'M57 86Q154 48 139 -42':['3','4'].includes(move)?'M55 -52Q159 -55 152 22':'M64 -19L151 -19'} strokeWidth="15" opacity=".13"/><path d={['5','6'].includes(move)?'M57 86Q154 48 139 -42':['3','4'].includes(move)?'M55 -52Q159 -55 152 22':'M64 -19L151 -19'} strokeWidth="3" opacity=".8"/></g>}
      </g>
    </g>
    <text y="209" transform={opponent?'scale(-1,1)':undefined} textAnchor="middle" fill={opponent?'#9dddf4':'#ffc1c9'} fontSize="10" letterSpacing="1.5" fontWeight="700">{opponent?'TRAINING PARTNER':stance==='southpaw'?'YOU · SOUTHPAW':'YOU · ORTHODOX'}</text>
  </g>;
}
export default function BoxingArena({ animation, expected, stance, active, effects=true }) {
  const id=useId().replace(/:/g,'');const paint=name=>`url(#${id}-${name})`;
  const simulation=!!animation.mode;const distance=animation.distance??1.4;const playerX=304+(1.4-distance)*45;const opponentX=486+(distance-1.4)*45;
  const defense=simulation?!!animation.threat:['slip','slipLeft','slipRight','roll','block'].includes(expected);
  const gradient=(name,colors)=><linearGradient key={name} id={`${id}-${name}`} x1="0" y1="0" x2="1" y2="1">{colors.map(([at,color])=><stop key={at} offset={at} stopColor={color}/>)}</linearGradient>;
  return <svg className={`tng-boxing-arena ${active?'is-playing':''} ${effects?'':'low-effects'}`} viewBox="0 0 800 470" role="img" aria-label={`TNG boxing ring. ${animation.move?MOVES[animation.move]?.name||'Footwork':'Boxers in guard'}.`} style={{width:'100%',display:'block',maxHeight:'56vh'}}>
    <defs>
      {gradient('background',[[0,'#070c18'],[.55,'#152139'],[1,'#050915']])}
      {gradient('canvas',[[0,'#354359'],[.5,'#202d41'],[1,'#0f1a2b']])}
      {gradient('red',[[0,'#ff9a8a'],[.3,'#f22e4e'],[.7,'#a80f30'],[1,'#4f0a20']])}
      {gradient('blue',[[0,'#b0f4ff'],[.3,'#34b4e2'],[.7,'#12648e'],[1,'#0c264c']])}
      {gradient('skin',[[0,'#ffe0b2'],[.4,'#dba078'],[.75,'#b66d4d'],[1,'#6c3f36']])}
      {gradient('darkSkin',[[0,'#cb9676'],[.4,'#9a644c'],[.75,'#70402f'],[1,'#392735']])}
      {gradient('boot',[[0,'#5d6c83'],[.4,'#1c283d'],[1,'#0a1020']])}
      <radialGradient id={`${id}-haze`}><stop stopColor="#5994ba" stopOpacity=".28"/><stop offset="1" stopColor="#122040" stopOpacity="0"/></radialGradient>
      <linearGradient id={`${id}-beam`} x2="0" y2="1"><stop stopColor="#b4e7ff" stopOpacity=".2"/><stop offset="1" stopColor="#b4e7ff" stopOpacity="0"/></linearGradient>
      <clipPath id={`${id}-floor`}><path d="M60 275H740L788 436H12Z"/></clipPath>
    </defs>
    <rect width="800" height="470" fill={paint('background')}/>
    <g className="tng-boxing-lights" fill={paint('beam')}><path d="M130 21L33 340H388Z"/><path d="M670 21L413 340H765Z"/><path d="M400 17L227 319H578Z" opacity=".5"/></g>
    <g stroke="#58718e" fill="none" opacity=".5"><path d="M0 18H800M0 39H800M0 18L40 39L80 18L120 39L160 18L200 39L240 18L280 39L320 18L360 39L400 18L440 39L480 18L520 39L560 18L600 39L640 18L680 39L720 18L760 39L800 18"/></g>
    {[92,186,307,493,614,708].map(x=><g key={x}><rect x={x-9} y="25" width="18" height="11" rx="3" fill="#bddef4"/><ellipse cx={x} cy="38" rx="19" ry="4" fill="#82cdf5" opacity=".3"/></g>)}
    <rect x="297" y="61" width="206" height="65" rx="6" fill="#070e1c" stroke="#ffffff23"/><path d="M297 61H355M445 126H503" stroke="#f13656" strokeWidth="2"/>
    <text x="400" y="93" fontSize="29" fontStyle="italic" fontWeight="950" textAnchor="middle" fill="#f4f8ff">TNG BOXING</text><text x="400" y="112" textAnchor="middle" fontSize="8" letterSpacing="4" fill="#88aac7">{simulation?(animation.mode==='bag'?'HEAVY BAG':animation.mode==='footwork'?'FOOTWORK LAB':animation.mode==='defense'?'DEFENSE & COUNTERS':'SPARRING PARTNER'):'COMBINATION LAB'}</text>
    <g opacity=".65">{Array.from({length:60},(_,i)=>{const x=(i%20)*42-4,y=160+Math.floor(i/20)*24;return <g key={i} fill={i%4===0?'#35435a':'#1a2539'}><ellipse cx={x} cy={y-8} rx="8" ry="10"/><path d={`M${x-13} ${y+17}q0 -20 13 -19q13 -1 13 19Z`}/></g>;})}</g>
    <ellipse cx="400" cy="236" rx="380" ry="174" fill={paint('haze')}/>
    <path d="M60 275H740L788 436H12Z" fill={paint('canvas')} stroke="#728195" strokeWidth="2"/>
    <g clipPath={`url(#${id}-floor)`} stroke="#a5c7e2" strokeOpacity=".055">{Array.from({length:18},(_,i)=><path key={i} d={`M${130+i*30} 275L${-100+i*60} 436`}/>)}{[288,309,337,375,424].map(y=><path key={y} d={`M0 ${y}H800`}/>)}</g>
    <ellipse cx="400" cy="367" rx="173" ry="41" fill="#091321" stroke="#a5bed81f"/><text x="400" y="376" fill="#c4d5e02b" textAnchor="middle" fontSize="48" fontWeight="950" fontStyle="italic">TNG</text><text x="400" y="395" fill="#afc8df40" textAnchor="middle" fontSize="8" letterSpacing="3">EARNED NOT GIVEN</text>
    {[176,212,249].map((y,i)=><g key={y}><path d={`M49 ${y+2}H751`} stroke="#030812" strokeWidth="6"/><path d={`M49 ${y}H751`} stroke={i===0?'#d8e6f0':i===1?'#647d99':'#bd213e'} strokeWidth="3"/></g>)}
    <g><path d="M49 156v137M751 156v137" stroke="#111a29" strokeWidth="17"/><path d="M47 156v137" stroke="#d32745" strokeWidth="9"/><path d="M753 156v137" stroke="#35a8d1" strokeWidth="9"/>{[179,215,251].map(y=><g key={y}><rect x="38" y={y-7} width="21" height="14" rx="4" fill={paint('red')}/><rect x="741" y={y-7} width="21" height="14" rx="4" fill={paint('blue')}/></g>)}</g>
    {animation.mode==='footwork'&&<g opacity=".7"><ellipse cx="355" cy="393" rx="120" ry="25" fill="none" stroke="#5cd9d4" strokeDasharray="7 6"/><path d={`M${350+(animation.angle||0)*65} 365v32`} stroke="#fff" strokeWidth="4"/><text x="355" y="425" fill="#9ee7e1" textAnchor="middle" fontSize="10">W / Z · STEP  —  Q / E · PIVOT</text></g>}
    <Fighter actionId={animation.id} move={animation.move} hit={animation.playerHit} stance={stance} paint={paint} x={simulation?playerX:undefined} y={218+(animation.angle||0)*12}/>
    {animation.mode==='bag'?<g key={`heavybag-${animation.hit?animation.id:'idle'}`} className={animation.hit?'tng-heavybag tng-heavybag-hit':'tng-heavybag'}><path d="M500 62v50M470 144l30 -34l30 34" fill="none" stroke="#95a5b5" strokeWidth="4"/><ellipse cx="500" cy="379" rx="62" ry="13" fill="#000" opacity=".4"/><rect x="453" y="139" width="94" height="217" rx="27" fill={paint('boot')} stroke="#8899a9" strokeWidth="2"/><path d="M460 173h80M459 315h82" stroke="#e52a4b" strokeWidth="15"/><path d="M470 148v199" stroke="#cbd7e3" strokeWidth="3" opacity=".3"/><text x="500" y="238" textAnchor="middle" fill="#fff" fontWeight="900" fontSize="24" fontStyle="italic">TNG</text><text x="500" y="258" textAnchor="middle" fill="#a9bbcc" fontSize="8">EARNED NOT GIVEN</text></g>:<Fighter opponent x={simulation?opponentX:undefined} actionId={animation.id} move={simulation?animation.opponentMove||'block':active&&defense?'1':'block'} hit={animation.hit} paint={paint}/>}
    {animation.playerHit&&<g><circle cx={playerX+15} cy="172" r="31" fill="#ff335d" opacity=".2"/><text x={playerX} y="126" textAnchor="middle" fill="#ff9db0" fontSize="12" fontWeight="800">CAUGHT</text></g>}
    {animation.hit&&<g key={`impact-${animation.id}`} className="tng-boxing-impact" transform={`translate(${animation.mode==='bag'?454:simulation?opponentX-40:445} ${animation.mode==='bag'?230:171})`}><g className="tng-boxing-burst"><circle r="29" fill="#ffe8b5" opacity=".12"/><circle r="24" fill="none" stroke="#ffe1a6" strokeWidth="2"/>{Array.from({length:9},(_,i)=><path key={i} transform={`rotate(${i*40})`} d="M15 0L37 -2" stroke={i%2?'#ffb44d':'#fff3cf'} strokeWidth={i%3?2:4} strokeLinecap="round"/>)}</g><text y="-47" fill="#ffde9b" textAnchor="middle" fontSize="15" fontWeight="900" letterSpacing="2">CLEAN!</text></g>}
    {active&&defense&&<g><rect x="262" y="132" width="276" height="23" rx="12" fill="#071a2c" stroke="#4ed3f750"/><text x="400" y="147" textAnchor="middle" fill="#95e5ff" fontSize="9" letterSpacing="2">DEFEND · {simulation?animation.threat:MOVES[expected].name.toUpperCase()}</text></g>}
    <path d="M12 437H788" stroke="#3f5169" strokeWidth="5"/><path d="M12 440H788V469H12Z" fill="#070e1a"/><text x="400" y="459" fill="#61768f" textAnchor="middle" fontSize="9" letterSpacing="4">THE NEXT GENERATION</text>
  </svg>;
}
