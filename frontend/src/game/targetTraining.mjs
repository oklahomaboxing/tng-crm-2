import{newTrainingRound,stepTraining,trainingInput,resumeTraining}from'./trainingEngine.mjs';
const COMBOS=[['1','2'],['1','2','3','2'],['5','2','3'],['3','6','2']];
const SPEED={learn:1700,flow:1350,fast:1050};
function nextTarget(s,now){
 const sequence=COMBOS[s.sequenceIndex%COMBOS.length],move=s.mode==='mitts'?sequence[s.sequenceStep%sequence.length]:String(s.targetCount%6+1),travel=s.mode==='mitts'?0:SPEED[s.level];
 return {...s,targetCount:s.targetCount+1,target:{id:s.targetCount+1,move,spawnAt:now,arriveAt:now+travel,expiresAt:now+travel+(s.mode==='mitts'?1800:260),lane:Number(move)%2===1?.23:-.23,body:['5','6'].includes(move)},feedback:s.mode==='mitts'?`Mitts: ${sequence.join(' · ')}`:`Incoming ${move}. Time your contact when it reaches range.`};
}
export function newTargetRound(now,seconds=120,mode='targets',level='learn'){
 if(!['targets','mitts'].includes(mode)||!SPEED[level])throw Error('Choose a target mode and difficulty.');
 return nextTarget({...newTrainingRound(now,seconds,'bag',level),mode,target:null,targetCount:0,sequenceIndex:0,sequenceStep:0,completedSequences:0,pendingPunch:null,opponentHealth:100},now+(mode==='mitts'?0:300));
}
export function stepTargetRound(s,now){
 if(s.result==='finished')return s;
 if(now>=s.endsAt)return {...s,result:'finished',pendingPunch:null,target:null,feedback:`Session complete. ${s.hits} clean targets; ${s.misses} missed.`};
 // Reuse recovery/energy mechanics without the sparring AI or range hit resolver.
 let next=stepTraining({...s,mode:'bag',pendingPunch:null},now);next={...next,mode:s.mode,target:s.target,pendingPunch:s.pendingPunch};
 if(next.pendingPunch&&now>=next.pendingPunch.impactAt){
  const punch=next.pendingPunch;next.pendingPunch=null;const target=next.target;
  const inWindow=target&&punch.impactAt>=target.spawnAt&&punch.impactAt>=target.arriveAt-(s.mode==='mitts'?Infinity:430)&&punch.impactAt<=target.expiresAt;
  if(inWindow&&punch.move===target.move){
   next.hits++;next.points+=s.mode==='mitts'?125:100;next.lastEvent={at:now,type:'landed'};next.result='landed';
   if(s.mode==='mitts'){const seq=COMBOS[s.sequenceIndex%COMBOS.length];next.sequenceStep++;if(next.sequenceStep>=seq.length){next.sequenceStep=0;next.sequenceIndex++;next.completedSequences++;next.points+=200;}}
   next=nextTarget(next,now+180);
  }else{next.lastEvent={at:now,type:'missed'};next.feedback=!inWindow?'Wait until the target enters range.':`Use punch ${target.move} on this mitt.`;next.result='missed';}
 }
 if(next.target&&now>next.target.expiresAt){next.misses++;next.lastEvent={at:now,type:'missed'};if(s.mode==='targets')next.playerHealth=Math.max(0,next.playerHealth-6);next=nextTarget(next,now+300);}
 if(next.playerHealth<=0)return {...next,result:'finished',target:null,pendingPunch:null,feedback:'Target session ended. Reset and work on your timing.'};
 return next;
}
export function targetInput(s,move,now){
 let next=stepTargetRound(s,now);if(next.result==='finished')return next;
 if(!/^[1-6]$/.test(move))return {...next,feedback:'This drill uses punches 1–6. Focus on the active target.'};
 const target=next.target;const withPunch=trainingInput({...next,mode:'bag'},move,now);
 return {...withPunch,mode:s.mode,target,sequenceIndex:next.sequenceIndex,sequenceStep:next.sequenceStep,completedSequences:next.completedSequences,targetCount:next.targetCount};
}
export function resumeTargetRound(s,pausedAt,now){const shift=Math.max(0,now-pausedAt),next=resumeTraining(s,pausedAt,now);return {...next,target:s.target?{...s.target,spawnAt:s.target.spawnAt+shift,arriveAt:s.target.arriveAt+shift,expiresAt:s.target.expiresAt+shift}:null};}
export function targetPose(s,now){const target=s.target;return target?{...target,progress:s.mode==='mitts'?1:Math.max(0,Math.min(1.25,(now-target.spawnAt)/(target.arriveAt-target.spawnAt)))}:null;}
