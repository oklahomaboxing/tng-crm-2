import test from 'node:test';
import assert from 'node:assert/strict';
import {DRILLS,gamepadEdges,keyboardMove,newRound,parseCombo,playMove,resumeRound,tickRound}from'../src/game/boxingEngine.mjs';
test('signature sequence requires jab, slip, lead uppercut, cross, hook and cross',()=>{
 let s=newRound(0);const sequence=['1','slipRight','5','2','3','2'];for(let i=0;i<sequence.length;i++)s=playMove(s,sequence[i],DRILLS[0].moves,200+i*200);
 assert.equal(s.combos,1);assert.equal(s.hits,6);assert.equal(s.points,850);assert.equal(s.index,0);assert.equal(s.deadline,null);
});
test('incorrect input resets a combo without awarding points; directional slips are enforced',()=>{
 let s=playMove(newRound(0),'1',['1','slipLeft','2'],200);s=playMove(s,'slipRight',['1','slipLeft','2'],500);assert.equal(s.index,0);assert.equal(s.points,100);assert.equal(s.misses,1);assert.equal(s.attempts,2);
});
test('timing expiry resets once and finished rounds cannot earn points',()=>{
 let s=playMove(newRound(0,60),'1',['1','2'],200,850);s=tickRound(s,1051);assert.equal(s.index,0);assert.equal(s.misses,1);assert.equal(tickRound(s,1100),s);s=playMove(s,'2',['1','2'],60001);assert.equal(s.result,'finished');assert.equal(s.points,100);
});
test('pause preserves remaining round time and combo deadline',()=>{
 const s=playMove(newRound(0),'1',['1','2'],200);const resumed=resumeRound(s,500,10500);assert.equal(resumed.endsAt,s.endsAt+10000);assert.equal(resumed.deadline,s.deadline+10000);assert.equal(playMove(resumed,'2',['1','2'],10700).combos,1);
});
test('input guard rejects impossible rapid repeats and unknown actions',()=>{
 const s=playMove(newRound(0),'1',['1','1','2'],200);assert.equal(playMove(s,'1',['1','1','2'],250),s);assert.equal(playMove(s,'unknown',['1','2'],500),s);
});
test('custom drills validate complete move names and length',()=>{
 assert.deepEqual(parseCombo('1, slip, 5, 2, 3, 2'),DRILLS[0].moves);assert.deepEqual(parseCombo('1 → slip left → 2'),['1','slipLeft','2']);for(const text of ['1','1,7','1,<script>','1,slpi,2',Array(17).fill('1').join(',')])assert.throws(()=>parseCombo(text));
});
test('keyboard has distinct punches and defense',()=>{
 for(let n=1;n<=6;n++)assert.equal(keyboardMove(String(n)),String(n));assert.equal(keyboardMove('a'),'slipLeft');assert.equal(keyboardMove('ArrowRight'),'slipRight');assert.equal(keyboardMove(' '),'block');assert.equal(keyboardMove('s'),'roll');assert.equal(keyboardMove('x'),null);
});
test('standard controller only fires edges; held triggers and sticks must rearm',()=>{
 const pad={mapping:'standard',buttons:Array.from({length:16},()=>({pressed:false,value:0})),axes:[0]};pad.buttons[0].pressed=true;let e=gamepadEdges(pad);assert.deepEqual(e.moves,['1']);assert.deepEqual(gamepadEdges(pad,e.state).moves,[]);pad.buttons[0].pressed=false;pad.axes[0]=-.9;e=gamepadEdges(pad,e.state);assert.deepEqual(e.moves,['slipLeft']);assert.deepEqual(gamepadEdges(pad,e.state).moves,[]);pad.axes[0]=0;e=gamepadEdges(pad,e.state);pad.buttons[7].value=.8;assert.deepEqual(gamepadEdges(pad,e.state).moves,['slipRight']);pad.buttons[9].pressed=true;assert.equal(gamepadEdges(pad,e.state).pause,true);assert.deepEqual(gamepadEdges({...pad,mapping:''}).moves,[]);
});
