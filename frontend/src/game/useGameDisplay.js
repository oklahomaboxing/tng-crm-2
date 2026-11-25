import{useEffect}from'react';import{requestScreenAwake}from'./mobileDisplay.mjs';
export default function useGameDisplay(active){
 useEffect(()=>{if(!active||document.hidden)return;let cancelled=false,lock;
  requestScreenAwake(navigator.wakeLock).then(value=>{if(cancelled)value?.release?.().catch(()=>{});else lock=value;});
  return()=>{cancelled=true;lock?.release?.().catch(()=>{});};
 },[active]);
}
