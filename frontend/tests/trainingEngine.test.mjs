import test from'node:test';import assert from'node:assert/strict';
import{newTrainingRound,stepTraining,trainingInput,resumeTraining,trainingKeyboardMove,trainingGamepadEdges,TRAINING_MODES}from'../src/game/trainingEngine.mjs';
test('distinct training modes validate and start with bounded resources',()=>{
 assert.deepEqual(TRAINING_MODES.map(x=>x.id),['combo','bag','defense','footwork','sparring']);
 for(const mode of ['bag','defense','footwork','sparring']){const s=newTrainingRound(0,120,mode);assert.equal(s.endsAt,120000);assert.equal(s.stamina,100);assert.equal(s.playerHealth,100)}
 assert.throws(()=>newTrainingRound(0,120,'combo'));assert.throws(()=>newTrainingRound(0,120,'bag','unknown'));
});
test('contact occurs at impact, not key press, and rapid repeats cannot score twice',()=>{
 let s=trainingInput(newTrainingRound(0),'1',200);assert.equal(s.hits,0);assert.equal(s.attempts,1);assert.ok(s.pendingPunch);s=trainingInput(s,'1',350);assert.equal(s.attempts,1);assert.equal(s.hits,1);const points=s.points;s=stepTraining(s,500);assert.equal(s.points,points);assert.equal(s.hits,1);
});
test('hooks and uppercuts need inside distance; straight punches reach farther',()=>{
 let s=trainingInput(newTrainingRound(0),'5',200);s=stepTraining(s,500);assert.equal(s.hits,0);assert.equal(s.result,'missed');
 s=trainingInput(s,'stepIn',800);s=trainingInput(s,'stepIn',1000);s=trainingInput(s,'5',1200);s=stepTraining(s,1500);assert.equal(s.hits,1);assert.ok(s.distance<=.95);
});
test('stamina depletion blocks punches and rest restores stamina without free hits',()=>{
 let s={...newTrainingRound(0),stamina:3,lastExertion:0};s=trainingInput(s,'2',200);assert.equal(s.result,'tired');assert.equal(s.attempts,0);s=stepTraining(s,1200);assert.ok(s.stamina>3);assert.equal(s.hits,0);assert.ok(s.stamina<=100);
});
test('defense reads telegraphed attacks and opens a real counter window',()=>{
 let s=stepTraining(newTrainingRound(0,120,'defense'),1800);assert.equal(s.threat.name,'JAB');s=trainingInput(s,'slipRight',2300);s=stepTraining(s,2800);assert.equal(s.defenses,1);assert.equal(s.taken,0);s=trainingInput(s,'2',2900);s=stepTraining(s,3200);assert.equal(s.counters,1);assert.equal(s.hits,1);
});
test('slipping a hook does not count as correct defense',()=>{
 let s=newTrainingRound(0,120,'defense');s={...s,threatIndex:1,distance:.9};s=stepTraining(s,1800);assert.equal(s.threat.name,'HOOK');s=trainingInput(s,'slipLeft',2300);s=stepTraining(s,2800);assert.equal(s.taken,1);assert.equal(s.defenses,0);assert.ok(s.playerHealth<100);
});
test('body guard protects against body attack and high guard does not',()=>{
 for(const [move,taken]of[['bodyBlock',0],['block',1]]){
  let s={...newTrainingRound(0,120,'defense'),threatIndex:3,distance:.8};s=stepTraining(s,1800);s=trainingInput(s,move,2300);s=stepTraining(s,2800);assert.equal(s.taken,taken);
 }
});
test('footwork requires moving into the called zone and holding, not punch spam',()=>{
 let s=newTrainingRound(0,120,'footwork');s=stepTraining(s,700);assert.equal(s.footworkGoals,0);s=trainingInput(s,'1',800);assert.equal(s.attempts,0);
 for(const now of[1000,1200,1400])s=trainingInput(s,'stepIn',now);s=stepTraining(s,1500);s=stepTraining(s,2100);assert.equal(s.footworkGoals,1);assert.equal(s.targetIndex,1);assert.equal(s.hits,0);
});
test('pause shifts incoming threats, punch impacts and end time together',()=>{
 let s=stepTraining(newTrainingRound(0,120,'defense'),1800);s=trainingInput(s,'1',2000);const before={impact:s.pendingPunch.impactAt,threat:s.threat.impactAt,ends:s.endsAt};s=resumeTraining(s,2050,12050);assert.equal(s.pendingPunch.impactAt,before.impact+10000);assert.equal(s.threat.impactAt,before.threat+10000);assert.equal(s.endsAt,before.ends+10000);assert.equal(stepTraining(s,12060).pendingPunch.impactAt,before.impact+10000);
});
test('round expiry prevents new points and resources stay within their limits',()=>{
 let s=newTrainingRound(0,60,'sparring');for(let now=200;now<4000;now+=200)s=trainingInput(s,'stepOut',now);assert.ok(s.distance<=2.6);assert.ok(s.stamina>=0&&s.stamina<=100);s=stepTraining(s,60000);const points=s.points;assert.equal(s.result,'finished');assert.equal(trainingInput(s,'1',60100).points,points);
});
test('sparring partner closes excess distance rather than standing still',()=>{
 const s=stepTraining({...newTrainingRound(0,120,'sparring'),distance:2.4},200);assert.ok(s.distance<2.4);
});
test('training keyboard and controller add footwork without held-input repeats',()=>{
 assert.equal(trainingKeyboardMove('w'),'stepIn');assert.equal(trainingKeyboardMove('z'),'stepOut');assert.equal(trainingKeyboardMove('q'),'pivotLeft');assert.equal(trainingKeyboardMove('e'),'pivotRight');assert.equal(trainingKeyboardMove('c'),'bodyBlock');assert.equal(trainingKeyboardMove('1'),'1');
 const pad={mapping:'standard',buttons:Array.from({length:16},()=>({pressed:false})),axes:[0,0,0,-.9]};const e=trainingGamepadEdges(pad);assert.deepEqual(e.moves,['stepIn']);assert.deepEqual(trainingGamepadEdges(pad,e.state).moves,[]);
});
