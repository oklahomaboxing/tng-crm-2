import test from'node:test';import assert from'node:assert/strict';import * as THREE from'three';
import{firstPersonLens}from'../src/game/fightPresentation.mjs';import{createFirstPersonHands}from'../src/game/firstPersonHands.mjs';
test('portrait first-person lens widens the vertical view and keeps a positive close clipping plane',()=>{
 assert.ok(firstPersonLens(true).fov>firstPersonLens(false).fov);for(const portrait of[true,false]){const lens=firstPersonLens(portrait);assert.ok(lens.fov>60&&lens.fov<110);assert.ok(lens.near>0&&lens.near<.04);}
});
test('first-person guard and punch positions fit the lens and recover without blocking the center',()=>{
 const view=createFirstPersonHands({low:true});try{
  view.update({move:'block',actionId:0,actionProgress:1},0);const left=view.hands.L.position.clone(),right=view.hands.R.position.clone();assert.ok(left.x<0&&right.x>0);
  for(const portrait of[true,false]){view.camera.fov=firstPersonLens(portrait).fov;view.camera.aspect=portrait?390/590:844/335;view.camera.updateProjectionMatrix();for(const hand of[left,right]){const point=hand.clone().project(view.camera);assert.ok(Math.abs(point.x)<1&&Math.abs(point.y)<1);assert.ok(hand.z<-.3);}}
  view.update({move:'1',actionId:1,actionProgress:.43,actionDuration:400},100);assert.ok(view.hands.L.position.z<left.z-.1);assert.ok(Math.abs(view.hands.L.position.x)<Math.abs(left.x));assert.deepEqual(view.hands.R.position.toArray(),right.toArray());
  view.update({move:'block',actionId:2,actionProgress:0},120);assert.deepEqual(view.hands.L.position.toArray(),left.toArray());
  view.update({move:'1',actionId:3,actionProgress:.43,actionDuration:400},200,'southpaw');assert.ok(view.hands.R.position.z<right.z-.1);assert.deepEqual(view.hands.L.position.toArray(),[-.2,-.17,-.4]);
 }finally{view.dispose();}
});
test('body cover lowers gloves and paused visual time cannot advance a punch',()=>{
 const view=createFirstPersonHands({low:true});try{
  view.update({move:'block',actionId:0,actionProgress:1},0);const high=view.hands.L.position.y;
  view.update({move:'bodyBlock',actionId:1,actionProgress:0},10);assert.ok(view.hands.L.position.y<high-.1);
  const pose={move:'2',actionId:2,actionProgress:.25,actionDuration:430};view.update(pose,100);const p=view.hands.R.position.clone();view.update(pose,100);assert.deepEqual(view.hands.R.position.toArray(),p.toArray());
 }finally{view.dispose();}
});
