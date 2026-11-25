import test from'node:test';import assert from'node:assert/strict';import fs from'node:fs';
import{GYM_LAYOUT}from'../src/game/gymEnvironment.mjs';import{isPhonePlay,requestScreenAwake}from'../src/game/mobileDisplay.mjs';
test('training equipment and mats leave the ring perimeter walkway clear',()=>{
 const margin=GYM_LAYOUT.ringHalf+GYM_LAYOUT.walkway;
 assert.ok(GYM_LAYOUT.bagX-.215>margin);assert.ok(Math.abs(GYM_LAYOUT.warmUp.x)-GYM_LAYOUT.warmUp.width/2>margin);
 for(const[x,z]of GYM_LAYOUT.benches){assert.ok(Math.abs(x)-.825>margin);assert.ok(Math.abs(x)+.825<GYM_LAYOUT.room.width/2);assert.ok(Math.abs(z)+.26<GYM_LAYOUT.room.depth/2);}
 for(const z of GYM_LAYOUT.bagZ)assert.ok(Math.abs(z)+.22<GYM_LAYOUT.room.depth/2);
 assert.ok(GYM_LAYOUT.room.height>4);
});
test('phone play automatically expands only the touch-sized view',()=>{
 assert.equal(isPhonePlay(true,390),true);assert.equal(isPhonePlay(true,844),true);assert.equal(isPhonePlay(false,390),false);assert.equal(isPhonePlay(true,1440),false);assert.equal(isPhonePlay(true,NaN),false);
});
test('screen wake lock is optional and a denied request cannot break play',async()=>{
 assert.equal(await requestScreenAwake(undefined),null);assert.equal(await requestScreenAwake({request:async()=>{throw Error('denied');}}),null);
 let kind;const sentinel={release:async()=>{}};assert.equal(await requestScreenAwake({request:async value=>{kind=value;return sentinel;}}),sentinel);assert.equal(kind,'screen');
});
test('home-screen manifest uses real icons and keeps normal app authentication entry',()=>{
 const manifest=JSON.parse(fs.readFileSync(new URL('../public/app.webmanifest',import.meta.url)));assert.equal(manifest.start_url,'/');assert.equal(manifest.scope,'/');assert.equal(manifest.display,'standalone');assert.equal(manifest.short_name,'TNGOS');assert.ok(!manifest.orientation,'rotation stays available');
 for(const icon of manifest.icons){const file=fs.readFileSync(new URL('../public'+icon.src,import.meta.url));assert.equal(file.subarray(1,4).toString(),'PNG');}
 assert.ok(fs.readFileSync(new URL('../index.html',import.meta.url),'utf8').includes('href="/app.webmanifest"'));
});
