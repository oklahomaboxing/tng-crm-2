import test from'node:test';import assert from'node:assert/strict';
import{newTargetRound,stepTargetRound,targetInput,resumeTargetRound,targetPose}from'../src/game/targetTraining.mjs';
import{firstPersonPunchPath}from'../src/game/fightPresentation.mjs';import{createFirstPersonHands}from'../src/game/firstPersonHands.mjs';
test('incoming targets advance toward range, score once at the matching impact, and spawn the next cue',()=>{
 let s=newTargetRound(0,30,'targets');assert.equal(s.target.move,'1');const before=targetPose(s,600),near=targetPose(s,1700);assert.ok(near.progress>before.progress);
 s=targetInput(s,'1',1900);assert.equal(s.hits,0);s=stepTargetRound(s,2100);assert.equal(s.hits,1);assert.equal(s.points,100);assert.equal(s.target.move,'2');assert.equal(stepTargetRound(s,2110).hits,1);
});
test('early or wrong punches do not score and an expired incoming target reduces health',()=>{
 let s=newTargetRound(0,30,'targets');s=targetInput(s,'1',350);s=stepTargetRound(s,600);assert.equal(s.hits,0);assert.equal(s.target.id,1);
 s=newTargetRound(0,30,'targets');s=targetInput(s,'2',1900);s=stepTargetRound(s,2150);assert.equal(s.hits,0);s=stepTargetRound(s,2300);assert.equal(s.misses,1);assert.equal(s.playerHealth,94);assert.equal(s.target.id,2);
});
test('mitt combinations require their sequence and reward a completed combination',()=>{
 let s=newTargetRound(0,30,'mitts');s=targetInput(s,'1',350);s=stepTargetRound(s,600);assert.equal(s.target.move,'2');assert.equal(s.hits,1);s=targetInput(s,'2',900);s=stepTargetRound(s,1250);assert.equal(s.hits,2);assert.equal(s.completedSequences,1);assert.equal(s.points,450);assert.equal(s.target.move,'1');assert.equal(s.playerHealth,100);
});
test('target pause shifts spawn, contact and expiry together; session expiry prevents further scores',()=>{
 let s=targetInput(newTargetRound(0,30,'targets'),'1',1900);const resumed=resumeTargetRound(s,1950,6950);assert.equal(resumed.target.arriveAt,s.target.arriveAt+5000);assert.equal(resumed.pendingPunch.impactAt,s.pendingPunch.impactAt+5000);assert.equal(targetPose(resumed,6950).progress,targetPose(s,1950).progress);
 s=stepTargetRound(s,30000);assert.equal(s.result,'finished');assert.equal(s.target,null);assert.equal(targetInput(s,'1',31000),s);assert.throws(()=>newTargetRound(0,30,'bad'));
});
test('uppercuts chamber low then rise above guard at contact, with a shorter reach than a straight',()=>{
 const base=[-.18,-.145,-.43];for(const move of['5','6']){const start=firstPersonPunchPath(move,0,base),load=firstPersonPunchPath(move,.43*.30,base),hit=firstPersonPunchPath(move,.43,base),end=firstPersonPunchPath(move,1,base);assert.deepEqual(start.position,base);assert.ok(load.position[1]<base[1]-.15);assert.ok(hit.position[1]>base[1]+.20);assert.ok(hit.rotation[0]<-.8);assert.deepEqual(end.position,base);assert.ok(hit.position[2]>firstPersonPunchPath('1',.43,base).position[2]);}
});
test('actual first-person glove follows the rising uppercut and returns to guard',()=>{
 const view=createFirstPersonHands({low:true});try{view.update({move:'block',actionId:0,actionProgress:1},0);const y=view.hands.L.position.y;view.update({move:'5',actionId:1,actionProgress:.43*.30,actionDuration:480},100);assert.ok(view.hands.L.position.y<y-.15);view.update({move:'5',actionId:1,actionProgress:.43,actionDuration:480},200);assert.ok(view.hands.L.position.y>y+.20);assert.ok(view.hands.L.rotation.x<-.8);view.update({move:'block',actionId:2,actionProgress:0},300);assert.equal(view.hands.L.position.y,y);}finally{view.dispose();}
});
test('uppercuts rise into the actual low mitt target rather than snapping into a straight',()=>{
 const base=[-.18,-.145,-.43],aim=[-.08,-.20,-.60];const chamber=firstPersonPunchPath('5',.43*.3,base,.43,aim),contact=firstPersonPunchPath('5',.43,base,.43,aim);assert.ok(chamber.position[1]<aim[1]-.2);assert.deepEqual(contact.position,aim);assert.ok(contact.rotation[0]<-.8);
});
test('stationary mitts can be struck immediately after starting the drill',()=>{let s=newTargetRound(0,30,'mitts');s=targetInput(s,'1',0);s=stepTargetRound(s,150);assert.equal(s.hits,1);assert.equal(s.target.move,'2');});
test('numbered targets and the trainer mitt stay on the correct first-person punch side',async()=>{
 const THREE=await import('three');const{mittHandForPunch,targetLaneForStance}=await import('../src/game/fightPresentation.mjs');const camera=new THREE.PerspectiveCamera(76,1,.025,10);camera.position.set(0,1.6,0);camera.lookAt(0,1.6,1);camera.updateMatrixWorld();
 let s=newTargetRound(0,30,'targets');assert.ok(new THREE.Vector3(s.target.lane,1.6,.85).project(camera).x<0,'jab cue is on the player left');s=targetInput(s,'1',1900);s=stepTargetRound(s,2100);assert.ok(new THREE.Vector3(s.target.lane,1.6,.85).project(camera).x>0,'cross cue is on the player right');assert.equal(mittHandForPunch('1'),'R');assert.equal(mittHandForPunch('5'),'R');assert.equal(mittHandForPunch('2'),'L');assert.equal(mittHandForPunch('6'),'L');assert.equal(mittHandForPunch('1','southpaw'),'L');assert.equal(mittHandForPunch('5','southpaw'),'L');assert.equal(targetLaneForStance(.23,'southpaw'),-.23);
});
