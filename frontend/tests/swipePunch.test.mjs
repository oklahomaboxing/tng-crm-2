import test from'node:test';import assert from'node:assert/strict';import{swipePunch,bindSwipePunch}from'../src/game/swipePunch.mjs';
const start={x:50,y:200,time:0},end=(x,y,time=160)=>({x,y,time});
test('touch halves select anatomical hands for taps, hooks and uppercuts in both stances',()=>{
 for(const [stance,left,right]of[['orthodox',[1,3,5],[2,4,6]],['southpaw',[2,4,6],[1,3,5]]])for(const[x,moves]of[[50,left],[350,right]]){const s={...start,x};assert.equal(swipePunch(s,end(x,200),400,stance),String(moves[0]));assert.equal(swipePunch(s,end(x+80,200),400,stance),String(moves[1]));assert.equal(swipePunch(s,end(x,100),400,stance),String(moves[2]));}
});
test('downward, diagonal, long holds and invalid gestures do not punch',()=>{for(const e of[end(50,300),end(100,150),end(50,200,900)])assert.equal(swipePunch(start,e,400),null);assert.equal(swipePunch(start,end(50,100),0),null);});
test('real pointer binding cancels touches and suppresses paused, mouse and non-first-person input',()=>{
 const original=globalThis.window;globalThis.window=new EventTarget();const el=new EventTarget();el.getBoundingClientRect=()=>({left:0,top:0,width:400});let state={active:true,camera:'firstperson',stance:'orthodox',onSwipePunch:m=>moves.push(m)},moves=[];const clean=bindSwipePunch(el,()=>state);
 const fire=(type,id=1,pointerType='touch',x=50,y=200)=>{const e=new Event(type);Object.assign(e,{pointerId:id,pointerType,clientX:x,clientY:y});el.dispatchEvent(e);};
 try{fire('pointerdown');fire('pointerup',1,'touch',50,100);assert.deepEqual(moves,['5']);fire('pointerdown');fire('pointercancel');fire('pointerup');fire('pointerdown');state.active=false;fire('pointerup');state.active=true;fire('pointerdown',1,'mouse');fire('pointerup',1,'mouse');state.camera='corner';fire('pointerdown');fire('pointerup');assert.equal(moves.length,1);clean();state.camera='firstperson';fire('pointerdown');fire('pointerup');assert.equal(moves.length,1);}finally{clean();globalThis.window=original;}
});
