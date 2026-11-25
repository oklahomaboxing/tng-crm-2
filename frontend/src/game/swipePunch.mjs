// Screen half chooses the anatomical hand; direction chooses punch family.
export function swipePunch(start,end,width,stance='orthodox'){
 if(!start||!end||!Number.isFinite(width)||width<=0)return null;
 const dx=end.x-start.x,dy=end.y-start.y,elapsed=end.time-start.time;
 if(![dx,dy,elapsed].every(Number.isFinite)||elapsed<0||elapsed>700)return null;
 const distance=Math.hypot(dx,dy),left=start.x<width/2,lead=stance==='southpaw'?!left:left;
 if(distance<18)return elapsed<=300?String(lead?1:2):null;
 if(dy<-24&&-dy>Math.abs(dx)*1.15)return String(lead?5:6);
 if(Math.abs(dx)>24&&Math.abs(dx)>Math.abs(dy)*1.15)return String(lead?3:4);
 return null;
}
export function bindSwipePunch(element,getState){
 const starts=new Map();
 const down=e=>{const s=getState();if(e.pointerType!=='touch'||!s.active||s.camera!=='firstperson')return;const r=element.getBoundingClientRect();starts.set(e.pointerId,{x:e.clientX-r.left,y:e.clientY-r.top,time:e.timeStamp});element.setPointerCapture?.(e.pointerId);};
 const up=e=>{const start=starts.get(e.pointerId);starts.delete(e.pointerId);if(!start)return;const s=getState();if(!s.active||s.camera!=='firstperson')return;const r=element.getBoundingClientRect(),move=swipePunch(start,{x:e.clientX-r.left,y:e.clientY-r.top,time:e.timeStamp},r.width,s.stance);if(move)s.onSwipePunch?.(move);};
 const cancel=e=>starts.delete(e.pointerId),clear=()=>starts.clear();
 element.addEventListener('pointerdown',down);element.addEventListener('pointerup',up);element.addEventListener('pointercancel',cancel);element.addEventListener('lostpointercapture',cancel);window.addEventListener('blur',clear);
 return()=>{element.removeEventListener('pointerdown',down);element.removeEventListener('pointerup',up);element.removeEventListener('pointercancel',cancel);element.removeEventListener('lostpointercapture',cancel);window.removeEventListener('blur',clear);clear();};
}
