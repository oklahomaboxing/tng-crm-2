import * as THREE from 'three';
import{clone}from'three/addons/utils/SkeletonUtils.js';
const V=(a)=>new THREE.Vector3().fromArray(a),UP=new THREE.Vector3(0,1,0),clamp=THREE.MathUtils.clamp;
export function solveLimb(start,target,a,b,pole){
 const direction=target.clone().sub(start);const distance=clamp(direction.length(),Math.max(.015,Math.abs(a-b)+.002),a+b-.004);if(direction.lengthSq()<1e-8)direction.set(0,0,1);direction.normalize();
 const along=(a*a-b*b+distance*distance)/(2*distance),height=Math.sqrt(Math.max(0,a*a-along*along));
 const bend=pole.clone().sub(start);bend.addScaledVector(direction,-bend.dot(direction));if(bend.lengthSq()<.0001)bend.set(0,0,1).addScaledVector(direction,-direction.z);bend.normalize();
 return {elbow:start.clone().addScaledVector(direction,along).addScaledVector(bend,height),end:start.clone().addScaledVector(direction,distance)};
}
function textTexture(text,color='#fff',background='#10131a'){
 const canvas=document.createElement('canvas');canvas.width=256;canvas.height=96;const c=canvas.getContext('2d');c.fillStyle=background;c.fillRect(0,0,256,96);c.fillStyle=color;c.font='italic 900 58px Arial';c.textAlign='center';c.textBaseline='middle';c.fillText(text,128,48);const t=new THREE.CanvasTexture(canvas);t.colorSpace=THREE.SRGBColorSpace;return t;
}
export function createBoxer(source,meta,{kit=0xc71e3b,skin=0xb77c59,bumpMap,lowDetail=false}={}){
 const root=new THREE.Group(),model=clone(source),bones={},rest=Object.fromEntries(meta.bones.map(b=>[b.name,V(b.position)]));root.add(model);
 const BodyMaterial=lowDetail?THREE.MeshStandardMaterial:THREE.MeshPhysicalMaterial;const athlete=new BodyMaterial({color:0xffffff,roughness:.56,metalness:0,...(!lowDetail?{clearcoat:.1,clearcoatRoughness:.6,ior:1.4,specularIntensity:.3}:{}),bumpMap:lowDetail?null:bumpMap,bumpScale:.0012});
 athlete.customProgramCacheKey=()=>"tng-athlete-kit-v1";
 athlete.onBeforeCompile=shader=>{
  shader.uniforms.tngSkin={value:new THREE.Color(skin)};shader.uniforms.tngKit={value:new THREE.Color(kit)};
  shader.vertexShader='varying vec3 tngRest;\n'+shader.vertexShader.replace('#include <begin_vertex>','#include <begin_vertex>\ntngRest=position;');
  shader.fragmentShader='varying vec3 tngRest;uniform vec3 tngSkin;uniform vec3 tngKit;\n'+shader.fragmentShader.replace('#include <color_fragment>',`#include <color_fragment>
   float y=tngRest.y;float ax=abs(tngRest.x);
   float shirt=smoothstep(1.018,1.023,y)*(1.0-smoothstep(1.50,1.505,y))*(1.0-smoothstep(.203,.209,ax));
   shirt*=1.0-smoothstep(1.415,1.44,y)*(1.0-smoothstep(.067,.075,ax));
   float shorts=smoothstep(.605,.610,y)*(1.0-smoothstep(1.020,1.025,y));
   float clothes=clamp(shirt+shorts,0.0,1.0);
   vec3 tone=tngSkin;float cheek=(1.0-smoothstep(.045,.075,abs(y-1.655)))*smoothstep(.025,.05,ax)*(1.0-smoothstep(.07,.09,ax))*smoothstep(.07,.13,tngRest.z);
   tone=mix(tone,tone*vec3(1.04,.90,.88),cheek*.5);
   diffuseColor.rgb=mix(tone,tngKit*mix(.73,1.0,shirt),clothes);
   float waist=smoothstep(.995,1.0,y)*(1.0-smoothstep(1.027,1.032,y));
   float hem=smoothstep(.61,.614,y)*(1.0-smoothstep(.632,.636,y));
   diffuseColor.rgb=mix(diffuseColor.rgb,vec3(.83,.85,.89),clamp(waist+hem,0.0,1.0));
   float hair=max(smoothstep(1.73,1.738,y),smoothstep(1.67,1.68,y)*(1.0-smoothstep(.048,.058,tngRest.z)));
   diffuseColor.rgb=mix(diffuseColor.rgb,vec3(.018,.015,.018),hair);
  `).replace('#include <roughnessmap_fragment>','#include <roughnessmap_fragment>\nroughnessFactor=mix(roughnessFactor,.78,clothes);');
 };
 model.traverse(object=>{
  if(object.isBone)bones[object.name]=object;
  if(object.isSkinnedMesh){object.frustumCulled=false;object.castShadow=true;object.receiveShadow=true;object.material=athlete;}
 });
 const gloveMat=new BodyMaterial({color:kit,roughness:.34,...(!lowDetail?{clearcoat:.42,clearcoatRoughness:.25}:{}),bumpMap:lowDetail?null:bumpMap,bumpScale:.0013});
 const bootMat=new THREE.MeshStandardMaterial({color:0x111722,roughness:.55}),trim=new THREE.MeshStandardMaterial({color:0xe5e8ee,roughness:.6});
 const patch=new THREE.MeshStandardMaterial({map:textTexture('TNG'),roughness:.6});
 const mesh=(g,m,parent,position,scale)=>{const o=new THREE.Mesh(g,m);if(position)o.position.set(...position);if(scale)o.scale.set(...scale);o.castShadow=true;o.receiveShadow=true;parent.add(o);return o;};
 for(const side of ['L','R']){
  const glove=new THREE.Group();glove.quaternion.setFromUnitVectors(UP,rest['hand'+side].clone().sub(rest['forearm'+side]).normalize());bones['hand'+side].add(glove);
  mesh(new THREE.SphereGeometry(1,24,18),gloveMat,glove,[0,.10,0],[.087,.115,.092]);mesh(new THREE.CapsuleGeometry(.031,.07,5,12),gloveMat,glove,[side==='L'?-.073:.073,.055,.035]);mesh(new THREE.CylinderGeometry(.065,.058,.06,20),gloveMat,glove,[0,-.015,0]);mesh(new THREE.CylinderGeometry(.059,.06,.018,20),trim,glove,[0,-.045,0]);const label=mesh(new THREE.PlaneGeometry(.075,.028),patch,glove,[0,.09,.09]);
  label.castShadow=false;
  const boot=new THREE.Group();bones['foot'+side].add(boot);mesh(new THREE.SphereGeometry(1,20,10),bootMat,boot,[0,-.061,.07],[.072,.018,.145]);mesh(new THREE.SphereGeometry(1,16,12),bootMat,boot,[0,-.025,.085],[.066,.062,.137]);mesh(new THREE.CapsuleGeometry(.045,.14,5,12),bootMat,boot,[0,.025,0]);for(let i=0;i<4;i++)mesh(new THREE.BoxGeometry(.078,.005,.006),trim,boot,[0,.025-i*.012,.037+i*.023]);
 }
 const whites=new THREE.MeshStandardMaterial({color:0xd9d4cb,roughness:.32}),iris=new THREE.MeshStandardMaterial({color:0x261f1b,roughness:.35});
 for(const side of ['L','R']){
  const center=V(meta.eyes[side]).sub(rest.head);mesh(new THREE.SphereGeometry(.013,18,12),whites,bones.head,center.toArray());mesh(new THREE.SphereGeometry(.006,14,10),iris,bones.head,[center.x,center.y,center.z+.011]);const brow=mesh(new THREE.CapsuleGeometry(.0025,.029,3,8),bootMat,bones.head,[center.x,center.y+.019,center.z+.007]);brow.rotation.z=Math.PI/2;
 }
 const chestPatch=mesh(new THREE.PlaneGeometry(.105,.04),patch,bones.chest,[0,.015,.15]);chestPatch.castShadow=false;const backPatch=mesh(new THREE.PlaneGeometry(.12,.045),patch,bones.chest,[0,.015,-.115]);backPatch.rotation.y=Math.PI;backPatch.castShadow=false;
 root.updateMatrixWorld(true);
 const restDirection={};for(const side of ['L','R']){restDirection['arm'+side]=rest['forearm'+side].clone().sub(rest['arm'+side]);restDirection['forearm'+side]=rest['hand'+side].clone().sub(rest['forearm'+side]);restDirection['thigh'+side]=rest['shin'+side].clone().sub(rest['thigh'+side]);restDirection['shin'+side]=rest['foot'+side].clone().sub(rest['shin'+side]);}
 const state={actionId:null,move:null,start:0,duration:360,hit:0,lastHit:null,opponentAction:null,opponentStart:0};
 const localPosition=bone=>root.worldToLocal(bone.getWorldPosition(new THREE.Vector3()));
 function aim(name,target){
  const bone=bones[name],q=new THREE.Quaternion().setFromUnitVectors(restDirection[name].clone().normalize(),target.clone().normalize());const rootQ=root.getWorldQuaternion(new THREE.Quaternion());q.premultiply(rootQ);const parentQ=bone.parent.getWorldQuaternion(new THREE.Quaternion()).invert();bone.quaternion.copy(parentQ.multiply(q));bone.updateMatrixWorld(true);
 }
 function limb(upper,lower,end,target,pole){
  const start=localPosition(bones[upper]),length1=restDirection[upper].length(),length2=restDirection[lower].length();const solution=solveLimb(start,target,length1,length2,pole);aim(upper,solution.elbow.clone().sub(start));const elbow=localPosition(bones[lower]);aim(lower,solution.end.clone().sub(elbow));
 }
 function update(pose,now,dt,{opponent=false,stance='orthodox',target,active=true}={}){
  const move=opponent?pose.opponentMove:pose.move;const id=opponent?move:pose.actionId??pose.id;
  if(/^[1-6]$/.test(move||'')&&id!==state.actionId){state.actionId=id;state.move=move;state.start=now;state.duration=opponent?360:pose.actionDuration||380;}
  const hit=opponent?pose.hit:pose.playerHit;
  if(hit&&pose.id!==state.lastHit){state.hit=1;state.lastHit=pose.id;}state.hit=Math.max(0,state.hit-dt*4.5);
  const t=(now-state.start)/state.duration,punch=t>=0&&t<1&&state.move;const drive=punch?(t<.42?Math.sin(t/.42*Math.PI/2):Math.cos((t-.42)/.58*Math.PI/2)):0;
  const slip=move==='slipLeft'?-1:move==='slipRight'?1:0,duck=move==='roll'?1:0;const lead=stance==='southpaw'?'R':'L';
  const side=(punch&&['1','3','5'].includes(state.move)?lead:punch?lead==='L'?'R':'L':null);
  bones.hips.position.copy(rest.hips);bones.hips.position.y-=.055+duck*.10;const breath=active?Math.sin(now*.0024)*.006:0;bones.hips.position.y+=breath;bones.hips.position.x+=slip*.075;
  bones.hips.rotation.set(.04-state.hit*.10,(stance==='southpaw'?.22:-.22)+(side==='L'?-1:1)*drive*.12,-slip*.07);
  bones.spine.rotation.set(.055-state.hit*.12,0,-slip*.08);bones.chest.rotation.set(.025,(side==='L'?-1:1)*drive*.20,0);bones.neck.rotation.set(.02,0,0);bones.head.rotation.set(.06-state.hit*.10,0,0);
  root.updateMatrixWorld(true);
  for(const s of ['L','R']){
   const sign=s==='L'?1:-1,isLead=s===lead;const foot=rest['foot'+s].clone();foot.x=sign*.17;foot.y=.075;foot.z=isLead?.20:-.19;
   if(['stepIn','stepOut','pivotLeft','pivotRight'].includes(move)&&active){const wave=Math.max(0,Math.sin(now*.011+(isLead?0:Math.PI)));foot.y+=wave*.025;foot.z+=Math.sin(now*.011+(isLead?0:Math.PI))*.035;}
   limb('thigh'+s,'shin'+s,'foot'+s,foot,new THREE.Vector3(sign*.32,.40,.45));const parentQ=bones['foot'+s].parent.getWorldQuaternion(new THREE.Quaternion()).invert();bones['foot'+s].quaternion.copy(parentQ.multiply(root.getWorldQuaternion(new THREE.Quaternion())));
  }
  root.updateMatrixWorld(true);
  for(const s of ['L','R']){
   const sign=s==='L'?1:-1,isLead=s===lead;const guard=new THREE.Vector3(sign*(isLead?.14:.11),isLead?1.48:1.52,isLead?.27:.19);
   if(move==='bodyBlock'){guard.y=1.19;guard.z=.24;}
   if(duck)guard.y-=.09;
   let hand=guard.clone();
   if(punch&&s===side){
    let end=target?root.worldToLocal(target.clone()):new THREE.Vector3(0,1.6,.8);end.z-=.12;end.x+=sign*.018;
    if(['3','4'].includes(state.move)){hand.x+=sign*Math.sin(Math.PI*t)*.14;end.z-=.06;end.y-=.03;}
    if(['5','6'].includes(state.move)){hand.y-=Math.sin(Math.PI*t)*.15;end.y-=.06;}
    hand.lerp(end,drive);
   }
   const shoulder=localPosition(bones['arm'+s]);const pole=new THREE.Vector3(sign*.65,shoulder.y-.52,.05+(s===side?drive*.18:0));limb('arm'+s,'forearm'+s,'hand'+s,hand,pole);
  }
  root.updateMatrixWorld(true);
 }
 function headTarget(){return bones.head.localToWorld(new THREE.Vector3(0,.015,.14));}
 return {root,model,bones,rest,update,headTarget};
}
