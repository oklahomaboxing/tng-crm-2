import test from'node:test';import assert from'node:assert/strict';
import{newAmateurMatch,stepAmateurMatch,amateurInput,resumeAmateurMatch,endAmateurMatch,matchRemaining,matchKeyboardMove}from'../src/game/amateurMatch.mjs';
import{newTrainingRound,stepTraining}from'../src/game/trainingEngine.mjs';
test('three-round match records each round once, rests, carries health and resolves a decision',()=>{
 let s=newAmateurMatch(0,1,'learn',.2);s={...s,hits:2,taken:1,playerHealth:70,stamina:12,opponentStamina:11};s=stepAmateurMatch(s,1000);assert.equal(s.phase,'rest');assert.equal(s.scorecards.length,1);assert.equal(s.scorecards[0].you,10);assert.equal(s.scorecards[0].partner,9);
 assert.equal(amateurInput(s,'1',1100),s);assert.equal(matchRemaining(s,1000),1);s=stepAmateurMatch(s,1200);assert.equal(s.roundNumber,2);assert.equal(s.playerHealth,82);assert.equal(s.stamina,100);assert.equal(s.opponentStamina,100);assert.equal(s.hits,0);
 s=stepAmateurMatch(s,2200);s=stepAmateurMatch(s,2400);assert.equal(s.roundNumber,3);s=stepAmateurMatch(s,3400);assert.equal(s.phase,'finished');assert.equal(s.winner,'you');assert.equal(s.scorecards.length,3);assert.equal(stepAmateurMatch(s,9000),s);
});
test('fight and rest pause shift timing without healing or replaying a bell',()=>{
 let s=stepAmateurMatch(newAmateurMatch(0,1,'learn',.2),1000);const paused=resumeAmateurMatch(s,1050,10050);assert.equal(paused.restEndsAt,s.restEndsAt+9000);assert.equal(paused.playerHealth,s.playerHealth);assert.equal(stepAmateurMatch(paused,10100).phase,'rest');assert.equal(stepAmateurMatch(paused,10200).roundNumber,2);
 s=newAmateurMatch(0,2,'learn',.2);s=amateurInput(s,'1',200);const resumed=resumeAmateurMatch(s,250,5250);assert.equal(resumed.pendingPunch.impactAt,s.pendingPunch.impactAt+5000);assert.equal(resumed.endsAt,7000);
});
test('health stoppage ends the match early and voluntary end declares no winner',()=>{
 let s={...newAmateurMatch(0),opponentHealth:0};s=stepAmateurMatch(s,100);assert.equal(s.phase,'finished');assert.equal(s.winner,'you');assert.equal(s.finishReason,'Training stoppage');assert.equal(s.scorecards[0].partial,true);
 const ended=endAmateurMatch(newAmateurMatch(0));assert.equal(ended.phase,'finished');assert.equal(ended.winner,null);assert.equal(ended.scorecards.length,0);
});
test('late inputs cannot score after the bell and invalid formats are rejected',()=>{
 let s=amateurInput(newAmateurMatch(0,1,'learn',.2),'1',950);s=stepAmateurMatch(s,1000);assert.equal(s.phase,'rest');assert.equal(s.hits,0);assert.equal(s.pendingPunch,null);assert.equal(s.scorecards[0].youHits,0);
 for(const value of[0,-1,Infinity,NaN,181])assert.throws(()=>newAmateurMatch(0,value));
});
test('arrows move while punch and defense mappings remain available',()=>{
 assert.deepEqual(['ArrowUp','ArrowDown','ArrowLeft','ArrowRight'].map(matchKeyboardMove),['stepIn','stepOut','pivotLeft','pivotRight']);for(let i=1;i<=6;i++)assert.equal(matchKeyboardMove(String(i)),String(i));assert.equal(matchKeyboardMove(' '),'block');assert.equal(matchKeyboardMove('a'),'slipLeft');
});
test('partner stamina reflects attacks and recovers, with exhaustion delaying threats',()=>{
 let s=stepTraining(newTrainingRound(0,120,'sparring'),1800);assert.ok(s.opponentStamina<100);const spent=s.opponentStamina;for(let n=2000;n<=2700;n+=100)s=stepTraining(s,n);assert.ok(s.opponentStamina>spent);assert.ok(s.opponentStamina<=100);
 s=stepTraining({...newTrainingRound(0,120,'sparring'),opponentStamina:0,lastOpponentExertion:1800},1800);assert.equal(s.threat,null);assert.equal(s.nextThreatAt,2300);
});
