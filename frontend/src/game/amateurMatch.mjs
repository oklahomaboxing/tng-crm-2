import{newTrainingRound,stepTraining,trainingInput,resumeTraining,trainingKeyboardMove}from'./trainingEngine.mjs';
const ROUND_COUNT=3;
export function newAmateurMatch(now,seconds=120,level='learn',restSeconds=seconds===30?10:60){
 if(!Number.isFinite(seconds)||seconds<=0||seconds>180||!Number.isFinite(restSeconds)||restSeconds<=0||restSeconds>60)throw Error('Choose a valid round and rest duration.');
 return {...newTrainingRound(now,seconds,'sparring',level),format:'amateur',phase:'round',roundNumber:1,roundSeconds:seconds,restSeconds,scorecards:[],totalPoints:0,winner:null,finishReason:null,restEndsAt:null,feedback:'Round 1 of 3. Box!'};
}
function card(s,partial=false){const youHits=s.hits||0,partnerHits=s.taken||0;return {round:s.roundNumber,youHits,partnerHits,you:youHits>=partnerHits?10:9,partner:partnerHits>=youHits?10:9,partial};}
function settle(s,now){
 if(s.result!=='finished'||s.phase==='finished')return s;
 const stoppage=s.playerHealth<=0||s.opponentHealth<=0,cards=[...s.scorecards,card(s,stoppage)];
 const neutral={...s,pendingPunch:null,threat:null,lastOpponentAttack:null,defense:null,defenseUntil:0,lastMove:null,visualUntil:now,scorecards:cards};
 if(stoppage||s.roundNumber===ROUND_COUNT){
  const points=cards.reduce((a,c)=>({you:a.you+c.you,partner:a.partner+c.partner}),{you:0,partner:0});
  const winner=stoppage?(s.playerHealth<=0&&s.opponentHealth<=0?'draw':s.playerHealth<=0?'partner':'you'):points.you===points.partner?'draw':points.you>points.partner?'you':'partner';
  return {...neutral,phase:'finished',winner,finishReason:stoppage?'Training stoppage':'Prototype points decision',feedback:stoppage?'The training fight has been stopped.':winner==='draw'?'Three-round fight complete. Draw on the prototype scorecard.':`${winner==='you'?'You win':'Partner wins'} on the prototype scorecard.`};
 }
 return {...neutral,phase:'rest',result:'rest',restEndsAt:now+s.restSeconds*1000,feedback:`Round ${s.roundNumber} complete. Recover for round ${s.roundNumber+1}.`};
}
export function stepAmateurMatch(s,now){
 if(s.phase==='finished')return s;
 if(s.phase==='rest'){
  if(now<s.restEndsAt)return s;
  return {...newTrainingRound(now,s.roundSeconds,'sparring',s.level),format:'amateur',phase:'round',roundNumber:s.roundNumber+1,roundSeconds:s.roundSeconds,restSeconds:s.restSeconds,scorecards:s.scorecards,totalPoints:s.totalPoints+s.points,restEndsAt:null,winner:null,finishReason:null,playerHealth:Math.min(100,s.playerHealth+12),opponentHealth:Math.min(100,s.opponentHealth+12),feedback:`Round ${s.roundNumber+1} of 3. Box!`};
 }
 return settle(stepTraining(s,now),now);
}
export function amateurInput(s,move,now){const next=stepAmateurMatch(s,now);return next.phase==='round'?settle(trainingInput(next,move,now),now):next;}
export function resumeAmateurMatch(s,pausedAt,now){const next=resumeTraining(s,pausedAt,now);return {...next,restEndsAt:s.restEndsAt===null?null:s.restEndsAt+Math.max(0,now-pausedAt)};}
export function endAmateurMatch(s){return {...s,phase:'finished',result:'finished',winner:null,finishReason:'Session ended early',pendingPunch:null,threat:null,lastOpponentAttack:null,feedback:'Session ended early. No winner declared.'};}
export function matchRemaining(s,now){return Math.max(0,Math.ceil(((s.phase==='rest'?s.restEndsAt:s.endsAt)-now)/1000));}
export function matchKeyboardMove(key){return {ArrowUp:'stepIn',ArrowDown:'stepOut',ArrowLeft:'pivotLeft',ArrowRight:'pivotRight'}[key]||trainingKeyboardMove(key);}
