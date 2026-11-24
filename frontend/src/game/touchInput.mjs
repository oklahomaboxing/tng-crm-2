export function padAction(x,y,mode='bag',deadZone=.22){
 if(!Number.isFinite(x)||!Number.isFinite(y)||Math.hypot(x,y)<deadZone)return null;
 if(mode==='combo')return Math.abs(x)>Math.abs(y)?x<0?'slipLeft':'slipRight':y<0?'block':'roll';
 return Math.abs(x)>Math.abs(y)?x<0?'pivotLeft':'pivotRight':y<0?'stepIn':'stepOut';
}
export function normalizedPad(clientX,clientY,rect){
 const radius=Math.max(1,Math.min(rect.width,rect.height)/2);let x=(clientX-(rect.left+rect.width/2))/radius,y=(clientY-(rect.top+rect.height/2))/radius;const length=Math.hypot(x,y);if(length>1){x/=length;y/=length;}return{x,y};
}
