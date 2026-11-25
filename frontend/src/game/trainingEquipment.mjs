import * as THREE from'three';
import{targetLaneForStance}from'./fightPresentation.mjs';
function cueTexture(number){const canvas=document.createElement('canvas');canvas.width=canvas.height=256;const ctx=canvas.getContext('2d');ctx.clearRect(0,0,256,256);ctx.fillStyle='#0a1420dd';ctx.beginPath();ctx.arc(128,128,108,0,Math.PI*2);ctx.fill();for(const[r,color,width]of[[107,'#f7d25e',8],[83,'#ffffff',3]]){ctx.strokeStyle=color;ctx.lineWidth=width;ctx.beginPath();ctx.arc(128,128,r,0,Math.PI*2);ctx.stroke();}ctx.fillStyle='#fff';ctx.font='900 102px Arial';ctx.textAlign='center';ctx.fillText(String(number),128,158);ctx.font='700 20px Arial';ctx.fillText('TNG',128,196);const texture=new THREE.CanvasTexture(canvas);texture.colorSpace=THREE.SRGBColorSpace;return texture;}
export function createTrainingEquipment(scene){
 const textures=Array.from({length:6},(_,i)=>cueTexture(i+1));const material=new THREE.SpriteMaterial({map:textures[0],transparent:true,depthTest:true,depthWrite:false});const marker=new THREE.Sprite(material);marker.scale.set(.27,.27,1);marker.visible=false;scene.add(marker);let id=null;
 function update(p,player,partner,dt,stance='orthodox'){
  const active=['targets','mitts'].includes(p.mode)&&p.target;marker.visible=!!active;if(!active)return;
  const t=p.target;material.depthTest=p.mode!=='mitts';marker.renderOrder=p.mode==='mitts'?20:0;if(material.map!==textures[Number(t.move)-1]){material.map=textures[Number(t.move)-1];material.needsUpdate=true;}
  let goal;if(p.mode==='mitts')goal=partner.mittTarget(t.move,stance);else goal=player.root.localToWorld(new THREE.Vector3(targetLaneForStance(t.lane,stance),t.body?1.35:1.62,Math.max(.60,4+(0.85-4)*t.progress)));
  if(t.id!==id){id=t.id;marker.position.copy(goal);}else marker.position.lerp(goal,Math.min(1,dt*22));
  marker.scale.setScalar(p.mode==='mitts'?.13:.28);material.opacity=t.progress<0?0:1;
 }
 return {update,aimPoint:()=>marker.visible?marker.position.clone():null,dispose(){material.dispose();for(const t of textures)t.dispose();}};
}
