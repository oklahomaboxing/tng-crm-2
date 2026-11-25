const clamp=(n,a=0,b=1)=>Math.max(a,Math.min(b,n));
const ease=t=>{const v=clamp(t);return v*v*(3-2*v);};
// A short load, contact at startup, then an eased return to guard.
export function punchMotion(move,progress,contact=.43){
 const t=clamp(progress),at=clamp(contact,.22,.7),left=['1','3','5'].includes(String(move)),hook=['3','4'].includes(String(move)),upper=['5','6'].includes(String(move));
 const load=ease(t/(at*.3))*(1-ease((t-at*.3)/(at*.5)));
 const extension=t<at?ease(t/at):1-ease((t-at)/(1-at));
 const arc=Math.sin(Math.PI*clamp(t/at));
 return {extension,load,arc:hook?arc*.17:upper?arc*.05:0,lift:upper?-arc*.19:0,turn:extension*(hook?.34:.22)*(left?-1:1),reach:hook?.91:upper?.83:1};
}
export function broadcastFrame(distance=1.4,angle=0,portrait=false){
 const gap=.4+clamp(distance,.45,2.6)*.24,midX=clamp(angle,-1.2,1.2)*.15;
 return {gap,midX,position:[midX-2.7,1.67,portrait?-1.8:-1.4],target:[midX,1.12,0],fov:portrait?47:40};
}
export function meterPercent(value){return Number.isFinite(value)?clamp(value,0,100):100;}
// Simulation snapshots arrive at 10 Hz; advance between them at render cadence.
export function sampleMotion(previous,id,progress,now,duration){
 const sample=!previous||previous.id!==id||previous.progress!==progress?{id,progress,at:now}:previous;
 return {...sample,value:sample.progress+Math.max(0,now-sample.at)/Math.max(1,duration)};
}

export function firstPersonLens(portrait=false){return {fov:portrait?96:76,near:.025};}
