import{useCallback,useEffect,useRef}from'react';
export default function useBoxingAudio(enabled){
 const context=useRef(null),active=useRef(enabled);active.current=enabled;
 const unlock=useCallback((force=false)=>{if(!active.current&&!force)return;if(force)active.current=true;try{const Audio=window.AudioContext||window.webkitAudioContext;if(Audio&&!context.current)context.current=new Audio();context.current?.resume().catch(()=>{});}catch{}},[]);
 const play=useCallback(type=>{if(!active.current||!context.current||context.current.state!=='running')return;try{
  const c=context.current,t=c.currentTime;
  if(type==='bell')for(const[frequency,volume]of[[760,.035],[1529,.012],[2132,.006]]){const osc=c.createOscillator(),gain=c.createGain();osc.frequency.value=frequency;gain.gain.setValueAtTime(volume,t);gain.gain.exponentialRampToValueAtTime(.0001,t+.85);osc.connect(gain);gain.connect(c.destination);osc.start(t);osc.stop(t+.9);osc.onended=()=>{osc.disconnect();gain.disconnect();};}
  else{
   const blocked=type==='guard',duration=blocked?.09:.16,buffer=c.createBuffer(1,Math.ceil(c.sampleRate*duration),c.sampleRate),data=buffer.getChannelData(0);for(let i=0;i<data.length;i++)data[i]=(Math.random()*2-1)*Math.exp(-i/data.length*8);
   const noise=c.createBufferSource(),filter=c.createBiquadFilter(),gain=c.createGain();noise.buffer=buffer;filter.type='lowpass';filter.frequency.value=blocked?600:1350;gain.gain.value=blocked?.08:.14;noise.connect(filter);filter.connect(gain);gain.connect(c.destination);noise.start(t);noise.onended=()=>{noise.disconnect();filter.disconnect();gain.disconnect();};
   const osc=c.createOscillator(),thump=c.createGain();osc.frequency.setValueAtTime(blocked?120:95,t);osc.frequency.exponentialRampToValueAtTime(42,t+.11);thump.gain.setValueAtTime(.055,t);thump.gain.exponentialRampToValueAtTime(.0001,t+.13);osc.connect(thump);thump.connect(c.destination);osc.start(t);osc.stop(t+.14);osc.onended=()=>{osc.disconnect();thump.disconnect();};
  }
 }catch{}},[]);
 useEffect(()=>()=>{context.current?.close().catch(()=>{});context.current=null;},[]);
 return{unlock,play};
}
