import test from'node:test';import assert from'node:assert/strict';import fs from'node:fs';import * as THREE from'three';
import{solveLimb}from'../src/game/boxerRig.mjs';import{padAction,normalizedPad}from'../src/game/touchInput.mjs';
test('phone pad supports dead zone, footwork and combination defense directions',()=>{
 assert.equal(padAction(0,0),null);assert.equal(padAction(.1,.1),null);assert.equal(padAction(NaN,1),null);
 assert.equal(padAction(0,-1),'stepIn');assert.equal(padAction(0,1),'stepOut');assert.equal(padAction(-1,0),'pivotLeft');assert.equal(padAction(1,0),'pivotRight');
 assert.equal(padAction(-1,0,'combo'),'slipLeft');assert.equal(padAction(1,0,'combo'),'slipRight');assert.equal(padAction(0,-1,'combo'),'block');assert.equal(padAction(0,1,'combo'),'roll');
});
test('pad coordinates normalize viewport offsets and clamp outside drags',()=>{
 const rect={left:40,top:80,width:100,height:100};assert.deepEqual(normalizedPad(90,130,rect),{x:0,y:0});const p=normalizedPad(900,900,rect);assert.ok(Math.abs(Math.hypot(p.x,p.y)-1)<1e-8);assert.ok(Number.isFinite(normalizedPad(1,1,{left:0,top:0,width:0,height:0}).x));
});
test('two-bone solver respects arm lengths and target, including unreachable cases',()=>{
 const start=new THREE.Vector3(0,1.5,0),pole=new THREE.Vector3(.4,1,0);
 for(const target of[new THREE.Vector3(.1,1.6,.35),new THREE.Vector3(0,1.5,2),start.clone()]){
  const s=solveLimb(start,target,.26,.29,pole);assert.ok(Math.abs(s.elbow.distanceTo(start)-.26)<1e-6);assert.ok(Math.abs(s.end.distanceTo(s.elbow)-.29)<1e-6);assert.ok(s.end.toArray().every(Number.isFinite));assert.ok(s.end.distanceTo(start)<=.55);
 }
});
test('bundled rig is compact, licensed, self-contained and has valid skin weights',()=>{
 const path=new URL('../public/game/assets/boxer-rig-v1.glb',import.meta.url),bytes=fs.readFileSync(path);assert.ok(bytes.length<1024*1024);assert.equal(bytes.readUInt32LE(0),0x46546c67);assert.equal(bytes.readUInt32LE(4),2);assert.equal(bytes.readUInt32LE(8),bytes.length);
 const length=bytes.readUInt32LE(12),json=JSON.parse(bytes.subarray(20,20+length).toString()),binStart=20+length+8;assert.ok(json.skins[0].joints.length>=19);assert.ok(json.buffers.every(b=>!b.uri));assert.ok(!json.images?.length);
 const attrs=json.meshes[0].primitives[0].attributes;assert.ok(attrs.JOINTS_0!==undefined);assert.ok(attrs.WEIGHTS_0!==undefined);
 const read=(accessor,index,component)=>{const a=json.accessors[accessor],v=json.bufferViews[a.bufferView],size=a.componentType===5126?4:2;const at=binStart+(v.byteOffset||0)+(a.byteOffset||0)+index*(v.byteStride||4*size)+component*size;return size===4?bytes.readFloatLE(at):bytes.readUInt16LE(at);};
 const count=json.accessors[attrs.WEIGHTS_0].count;
 for(let i=0;i<count;i+=31){let sum=0;for(let j=0;j<4;j++){sum+=read(attrs.WEIGHTS_0,i,j);assert.ok(read(attrs.JOINTS_0,i,j)<json.skins[0].joints.length);}assert.ok(Math.abs(sum-1)<1e-5);}
 const meta=JSON.parse(fs.readFileSync(new URL('../public/game/assets/boxer-rig-v1.json',import.meta.url)));assert.equal(meta.license,'CC0-1.0');assert.equal(meta.height,1.8);assert.equal(new Set(meta.bones.map(b=>b.name)).size,19);assert.ok(meta.source_sha256.body);
});
