import {MOVES,newRound,gamepadEdges,keyboardMove} from './boxingEngine.mjs';
export const TRAINING_MODES=[
 {id:'combo',name:'Combination Lab',description:'Learn numbered combinations and directional defense.'},
 {id:'bag',name:'Heavy Bag',description:'Find your range, manage stamina and finish each punch before throwing again.'},
 {id:'defense',name:'Defense & Counters',description:'Read telegraphed attacks, choose the right defense and counter in the opening.'},
 {id:'footwork',name:'Footwork',description:'Step into range, move out and pivot to the called angle.'},
 {id:'sparring',name:'Sparring',description:'Work against an attacking partner with guard, range, recovery and round health.'},
];
export const TRAINING_MOVES={
 stepIn:{name:'Step in',key:'W',button:'Right stick up'},stepOut:{name:'Step out',key:'Z',button:'Right stick down'},
 pivotLeft:{name:'Pivot left',key:'Q',button:'Right stick left'},pivotRight:{name:'Pivot right',key:'E',button:'Right stick right'},
 bodyBlock:{name:'Body guard',key:'C',button:'Left stick click'},
};
export const ALL_MOVES={...MOVES,...TRAINING_MOVES};
export const LEVELS={learn:{name:'Learn',telegraph:1000,interval:1600},flow:{name:'Flow',telegraph:720,interval:1200},fast:{name:'Challenge',telegraph:480,interval:950}};
const PUNCHES={
 '1':{cost:5,startup:130,recovery:300,min:.65,max:1.85,damage:4},'2':{cost:9,startup:190,recovery:430,min:.7,max:1.75,damage:8},
 '3':{cost:11,startup:210,recovery:460,min:.4,max:1.15,damage:9},'4':{cost:12,startup:240,recovery:490,min:.4,max:1.15,damage:10},
 '5':{cost:12,startup:220,recovery:480,min:.35,max:.95,damage:10},'6':{cost:13,startup:260,recovery:520,min:.35,max:.95,damage:11},
};
const THREATS=[{name:'JAB',move:'1',defenses:['slipLeft','slipRight','block'],range:1.85,hint:'slip or high guard'},{name:'HOOK',move:'3',defenses:['roll','block'],range:1.2,hint:'roll or high guard'},{name:'CROSS',move:'2',defenses:['slipLeft','slipRight','block'],range:1.75,hint:'slip or high guard'},{name:'BODY SHOT',move:'5',defenses:['bodyBlock'],range:1.1,hint:'body guard or step out'}];
export const FOOTWORK_TARGETS=[{name:'Find jab range',test:s=>s.distance>=1.2&&s.distance<=1.65},{name:'Move outside range',test:s=>s.distance>=2.05},{name:'Pivot left',test:s=>s.angle<=-.65},{name:'Pivot right',test:s=>s.angle>=.65}];
const clamp=(n,min,max)=>Math.max(min,Math.min(max,n));
const event=(s,now,type,text)=>({...s,lastEvent:{at:now,type},feedback:text,result:type});
export function newTrainingRound(now,duration=120,mode='bag',level='learn'){
 if(!TRAINING_MODES.some(m=>m.id===mode&&mode!=='combo')||!LEVELS[level])throw Error('Choose a training mode and difficulty.');
 return {...newRound(now,duration),mode,level,lastTick:now,stamina:100,playerHealth:100,opponentHealth:100,distance:mode==='footwork'?2.2:1.4,angle:0,readyAt:now,defenseUntil:0,defense:null,counterUntil:0,nextThreatAt:now+1800,threat:null,threatIndex:0,pendingPunch:null,lastExertion:-Infinity,lastMove:null,visualUntil:0,lastEvent:null,defenses:0,taken:0,counters:0,footworkGoals:0,targetIndex:0,targetHoldSince:null,feedback:mode==='footwork'?'Find jab range. Use W / Z to step and Q / E to pivot.':'Set your feet. Work at the right distance.',result:'ready'};
}
export function stepTraining(state,now){
 if(state.result==='finished')return state;
 if(now>=state.endsAt)return {...state,result:'finished',pendingPunch:null,threat:null,feedback:'Round complete. Review your accuracy, defense and stamina.'};
 const dt=clamp((now-state.lastTick)/1000,0,.2);let s={...state,lastTick:now,stamina:clamp(state.stamina+(now-state.lastExertion>600?15*dt:0),0,100)};
 if(s.mode==='sparring'&&s.distance>1.4)s.distance=Math.max(1.4,s.distance-dt*.35);
 if(s.pendingPunch&&now>=s.pendingPunch.impactAt){
  const punch=s.pendingPunch,stats=PUNCHES[punch.move];s.pendingPunch=null;
  const inRange=s.distance>=stats.min&&s.distance<=stats.max;
  const guarded=s.mode==='sparring'&&!s.threat&&Math.floor((now-s.startedAt)/1400)%3===0;
  if(!inRange)s=event(s,now,'missed','Out of range. Straight punches reach farther; hooks and uppercuts need inside position.');
  else if(guarded)s=event(s,now,'blocked','Partner caught it on the guard. Draw an attack and counter.');
  else{
   const counter=now<=s.counterUntil;s.hits++;s.points+=counter?175:100;s.counters+=Number(counter);s.counterUntil=0;
   if(s.mode==='sparring')s.opponentHealth=clamp(s.opponentHealth-stats.damage*(counter?1.4:1),0,100);
   s=event(s,now,'landed',counter?'Clean counter! Return to your guard.':'Clean contact. Recover your hand and keep your balance.');
  }
 }
 if(['defense','sparring'].includes(s.mode)){
  if(!s.threat&&now>=s.nextThreatAt){const attack=THREATS[s.threatIndex%THREATS.length];s.threat={...attack,impactAt:now+LEVELS[s.level].telegraph};s.threatIndex++;s.feedback=attack.name+' incoming — '+attack.hint+'.';}
  if(s.threat&&now>=s.threat.impactAt){
   const threat=s.threat;const outside=s.distance>threat.range;const defended=outside||(s.defenseUntil>=threat.impactAt&&threat.defenses.includes(s.defense));
   s.threat=null;s.nextThreatAt=now+LEVELS[s.level].interval;
   if(defended){s.defenses++;s.counterUntil=now+700;s.points+=outside?40:75;s=event(s,now,'defended',outside?'Good distance. Step back in behind your jab.':'Defense worked — counter now!');}
   else{s.taken++;s.playerHealth=clamp(s.playerHealth-(s.mode==='sparring'?10:5),0,100);s=event(s,now,'caught','Caught by the '+threat.name.toLowerCase()+'. '+threat.hint+'.');}
  }
 }
 if(s.mode==='footwork'){
  const target=FOOTWORK_TARGETS[s.targetIndex%FOOTWORK_TARGETS.length];
  if(target.test(s)){
   if(s.targetHoldSince===null)s.targetHoldSince=now;
   else if(now-s.targetHoldSince>=600){s.footworkGoals++;s.points+=150;s.targetIndex++;s.targetHoldSince=null;s=event(s,now,'movement','Balanced position. Next: '+FOOTWORK_TARGETS[s.targetIndex%FOOTWORK_TARGETS.length].name+'.');}
  }else{s.targetHoldSince=null;s.feedback=target.name+' — hold the position briefly.';}
 }
 if(s.playerHealth<=0||s.opponentHealth<=0)return {...s,result:'finished',pendingPunch:null,threat:null,feedback:s.playerHealth<=0?'Partner stops the round. Reset and prioritize defense.':'Training partner stopped. Round complete.'};
 return s;
}
export function trainingInput(state,move,now){
 if(state.result==='finished'||now-state.lastInput<90)return state;
 let s=stepTraining(state,now);if(s.result==='finished'||!ALL_MOVES[move]||move==='slip')return s;
 if(PUNCHES[move]){
  if(s.mode==='footwork')return event(s,now,'movement','Footwork round: use W / Z and Q / E to find the called position.');
  if(now<s.readyAt)return event(s,now,'recovering','Recover your last punch before throwing again.');
  const stats=PUNCHES[move];if(s.stamina<stats.cost)return event(s,now,'tired','Low stamina. Stop punching briefly and recover.');
  const fatigue=1+(100-s.stamina)/130;s.stamina-=stats.cost;s.lastExertion=now;s.readyAt=now+stats.recovery*fatigue;s.pendingPunch={move,impactAt:now+stats.startup*fatigue};s.attempts++;s.defenseUntil=0;s.lastMove=move;s.visualUntil=now+stats.recovery*fatigue;s.lastInput=now;
  return event(s,now,'punching',ALL_MOVES[move].name+' — drive, contact, recover.');
 }
 if(s.pendingPunch)return event(s,now,'recovering','Finish the punch before changing position or guard.');
 if(s.stamina<3)return event(s,now,'tired','Recover your stamina before moving again.');
 s.stamina-=3;s.lastExertion=now;s.lastInput=now;s.lastMove=move;s.visualUntil=now+360;
 if(move==='stepIn')s.distance=clamp(s.distance-.25,.45,2.6);
 else if(move==='stepOut')s.distance=clamp(s.distance+.25,.45,2.6);
 else if(move==='pivotLeft')s.angle=clamp(s.angle-.35,-1.2,1.2);
 else if(move==='pivotRight')s.angle=clamp(s.angle+.35,-1.2,1.2);
 else{s.defense=move;s.defenseUntil=now+LEVELS[s.level].telegraph+80;return event(s,now,'guarding',ALL_MOVES[move].name+' set. Read the next attack.');}
 return event(s,now,'movement','Feet set. Keep the opponent in front of you.');
}
export function resumeTraining(state,pausedAt,now){
 const elapsed=Math.max(0,now-pausedAt);const s={...state,lastTick:now};
 for(const key of ['startedAt','endsAt','readyAt','defenseUntil','counterUntil','nextThreatAt','lastExertion','lastInput','visualUntil'])s[key]+=elapsed;
 if(s.pendingPunch)s.pendingPunch={...s.pendingPunch,impactAt:s.pendingPunch.impactAt+elapsed};
 if(s.threat)s.threat={...s.threat,impactAt:s.threat.impactAt+elapsed};
 if(s.targetHoldSince!==null)s.targetHoldSince+=elapsed;
 if(s.lastEvent)s.lastEvent={...s.lastEvent,at:s.lastEvent.at+elapsed};
 return s;
}
export function trainingKeyboardMove(key){return ({w:'stepIn',z:'stepOut',q:'pivotLeft',e:'pivotRight',c:'bodyBlock'})[key]||keyboardMove(key);}
export function trainingGamepadEdges(pad,previous={}){
 const base=gamepadEdges(pad,previous);if(!pad||pad.mapping!=='standard')return base;
 const state={...base.state,in:(pad.axes?.[3]||0)<-.65,out:(pad.axes?.[3]||0)>.65,pivotL:(pad.axes?.[2]||0)<-.65,pivotR:(pad.axes?.[2]||0)>.65,body:!!pad.buttons?.[10]?.pressed};
 const map={in:'stepIn',out:'stepOut',pivotL:'pivotLeft',pivotR:'pivotRight',body:'bodyBlock'};
 return {...base,state,moves:[...base.moves,...Object.keys(map).filter(k=>state[k]&&!previous[k]).map(k=>map[k])]};
}
export function trainingPose(state,now){
 const recent=state.lastEvent&&now-state.lastEvent.at<260;
 return {actionId:state.lastInput,actionDuration:Math.max(300,state.visualUntil-state.lastInput),id:state.lastEvent?.at||state.lastInput,move:now<state.visualUntil?state.lastMove:state.defenseUntil>now?state.defense:'block',hit:recent&&state.lastEvent.type==='landed',playerHit:recent&&state.lastEvent.type==='caught',opponentMove:state.threat&&state.threat.impactAt-now<240?state.threat.move:'block',distance:state.distance,angle:state.angle,mode:state.mode,threat:state.threat?.name};
}
