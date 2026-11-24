import{useCallback,useEffect,useRef}from'react';
export default function useBoxingAudio(enabled){
 const context=useRef(null),active=useRef(enabled);active.current=enabled;
 const unlock=useCallback((force=false)=>{if(!active.current&&!force)return;if(force)active.current=true;try{const Audio=window.AudioContext||window.webkitAudioContext;if(Audio&&!context.current)context.current=new Audio();context.current?.resume().catch(()=>{});}catch{}},[]);
 const play=useCallback(type=>{if(!active.current||!context.current||context.current.state!=='running')return;try{const c=context.current,t=c.currentTime,osc=c.createOscillator(),gain=c.createGain();osc.type=type==='bell'?'sine':'triangle';osc.frequency.setValueAtTime(type==='bell'?880:125,t);osc.frequency.exponentialRampToValueAtTime(type==='bell'?700:52,t+.13);gain.gain.setValueAtTime(.0001,t);gain.gain.exponentialRampToValueAtTime(type==='bell' ? .045 : .06,t+.007);gain.gain.exponentialRampToValueAtTime(.0001,t+(type==='bell' ? .55 : .16));osc.connect(gain);gain.connect(c.destination);osc.start(t);osc.stop(t+(type==='bell' ? .6 : .18));osc.onended=()=>{osc.disconnect();gain.disconnect();};}catch{}},[]);
 useEffect(()=>()=>{context.current?.close().catch(()=>{});context.current=null;},[]);
 return{unlock,play};
}
