import test from'node:test';import assert from'node:assert/strict';
import{punchMotion,broadcastFrame,meterPercent}from'../src/game/fightPresentation.mjs';
import{newTrainingRound,stepTraining,trainingInput,trainingPose,resumeTraining}from'../src/game/trainingEngine.mjs';
test('all punch trajectories load, contact at startup and return to guard without nonfinite values',()=>{
 for(const move of['1','2','3','4','5','6'])for(const contact of[.3,.43,.6]){
  assert.equal(punchMotion(move,0,contact).extension,0);assert.equal(punchMotion(move,contact,contact).extension,1);assert.equal(punchMotion(move,1,contact).extension,0);
  for(let i=0;i<=100;i++){const p=punchMotion(move,i/100,contact);assert.ok(Object.values(p).every(Number.isFinite));assert.ok(p.extension>=0&&p.extension<=1);}
 }
 assert.notEqual(punchMotion('1',.2).arc,punchMotion('3',.2).arc);assert.ok(punchMotion('5',.2).lift<0);assert.ok(punchMotion('1',.43).turn<0);assert.ok(punchMotion('2',.43).turn>0);
});
test('presentation keeps attack identity and follow-through after mechanics resolve contact',()=>{
 let s=stepTraining(newTrainingRound(0,120,'defense'),1800);const ready=trainingPose(s,2600);assert.equal(ready.opponentMove,'1');assert.equal(ready.opponentActionId,1);
 s=stepTraining(s,2800);const after=trainingPose(s,2850);assert.equal(after.opponentMove,'1');assert.equal(after.opponentActionId,ready.opponentActionId);assert.ok(after.opponentProgress>ready.opponentProgress);assert.equal(trainingPose(s,3100).opponentMove,'block');
 // A later identical punch has a different ID and must animate again.
 s={...s,threatIndex:4,nextThreatAt:3200};s=stepTraining(s,3200);const repeat=trainingPose(s,4000);assert.equal(repeat.opponentMove,'1');assert.notEqual(repeat.opponentActionId,ready.opponentActionId);
});
test('pause preserves opponent animation progress and player motion matches impact timing',()=>{
 let s=stepTraining(newTrainingRound(0,120,'defense'),1800);const before=trainingPose(s,2600);const resumed=resumeTraining(s,2600,12600);assert.equal(trainingPose(resumed,12600).opponentProgress,before.opponentProgress);
 s=trainingInput(newTrainingRound(0,120,'bag'),'2',1000);const at=trainingPose(s,s.pendingPunch.impactAt);assert.ok(Math.abs(at.actionProgress-at.contactFraction)<1e-8);
});
test('broadcast camera remains bounded at extremes and meters sanitize values',()=>{
 for(const portrait of[true,false])for(const d of[-100,.45,1.4,2.6,100]){const f=broadcastFrame(d,200,portrait);assert.ok(f.gap>.4&&f.gap<1.1);assert.ok(f.position.every(Number.isFinite));assert.ok(f.position.every(v=>Math.abs(v)<5));}
 assert.equal(meterPercent(-20),0);assert.equal(meterPercent(150),100);assert.equal(meterPercent(NaN),100);
});
test('a ready round has finite animation timing and a jab remains valid exactly at near range',()=>{
 const pose=trainingPose(newTrainingRound(0,120,'bag'),0);assert.ok(Number.isFinite(pose.actionDuration));assert.ok(Number.isFinite(pose.actionProgress));
 let s=newTrainingRound(0,120,'bag');s=trainingInput(s,'stepIn',1000);s=trainingInput(s,'stepIn',1400);s=trainingInput(s,'stepIn',1800);s=trainingInput(s,'1',2300);s=stepTraining(s,2600);assert.equal(s.hits,1);
});
test('two-thumb play accepts a punch immediately after footwork without bypassing punch recovery',()=>{
 let s=trainingInput(newTrainingRound(0,120,'bag'),'pivotLeft',1000);s=trainingInput(s,'1',1010);assert.equal(s.attempts,1);assert.ok(s.pendingPunch);s=trainingInput(s,'2',1020);assert.equal(s.attempts,1);assert.equal(s.pendingPunch.move,'1');s=stepTraining(s,1400);assert.equal(s.hits,1);
});
