import React,{useEffect,useRef,useState}from'react';
import * as THREE from'three';
import{GLTFLoader}from'three/addons/loaders/GLTFLoader.js';
import{OrbitControls}from'three/addons/controls/OrbitControls.js';
import{RoomEnvironment}from'three/addons/environments/RoomEnvironment.js';
import{createBoxer}from'./boxerRig.mjs';
import{createTrainingEquipment}from'./trainingEquipment.mjs';
import{createFirstPersonHands}from'./firstPersonHands.mjs';
import{broadcastFrame,firstPersonLens}from'./fightPresentation.mjs';
import './boxing3d.css';
let assetPromise;
function assets(){if(!assetPromise)assetPromise=Promise.all([new GLTFLoader().loadAsync('/game/assets/boxer-rig-v1.glb'),fetch('/game/assets/boxer-rig-v1.json').then(r=>{if(!r.ok)throw Error('Fighter metadata unavailable');return r.json();})]).catch(e=>{assetPromise=null;throw e;});return assetPromise;}
function grain(){const c=document.createElement('canvas');c.width=c.height=128;const g=c.getContext('2d'),image=g.createImageData(128,128);let seed=23;for(let i=0;i<image.data.length;i+=4){seed=(seed*1664525+1013904223)>>>0;const n=115+(seed%35);image.data[i]=image.data[i+1]=image.data[i+2]=n;image.data[i+3]=255;}g.putImageData(image,0,0);const texture=new THREE.CanvasTexture(c);texture.wrapS=texture.wrapT=THREE.RepeatWrapping;texture.repeat.set(5,5);return texture;}
function brand(text,sub,color='#f2f3f7',background='#10141b'){
 const c=document.createElement('canvas');c.width=1024;c.height=256;const g=c.getContext('2d');g.fillStyle=background;g.fillRect(0,0,1024,256);g.fillStyle=color;g.textAlign='center';g.font='italic 900 118px Arial';g.fillText(text,512,140);g.font='700 29px Arial';g.letterSpacing='7px';g.fillText(sub,512,207);const t=new THREE.CanvasTexture(c);t.colorSpace=THREE.SRGBColorSpace;return t;
}
function buildArena(scene,low=false){
 const noise=grain(),red=new THREE.MeshStandardMaterial({color:0x98182c,roughness:.45}),white=new THREE.MeshStandardMaterial({color:0xc9cdd4,roughness:.55}),dark=new THREE.MeshStandardMaterial({color:0x10141c,roughness:.62}),metal=new THREE.MeshStandardMaterial({color:0x65717c,metalness:.78,roughness:.4});
 const mesh=(geo,mat,pos,rotation)=>{const m=new THREE.Mesh(geo,mat);m.position.set(...pos);if(rotation)m.rotation.set(...rotation);scene.add(m);return m;};
 mesh(new THREE.PlaneGeometry(38,38),new THREE.MeshStandardMaterial({color:0x080c12,roughness:.88}),[0,-.12,0],[-Math.PI/2,0,0]);
 mesh(new THREE.BoxGeometry(6.8,.28,6.8),dark,[0,.02,0]);const floor=mesh(new THREE.PlaneGeometry(6.5,6.5),new THREE.MeshStandardMaterial({color:0x404c5c,roughness:.88,bumpMap:low?null:noise,bumpScale:.005}),[0,.168,0],[-Math.PI/2,0,0]);floor.receiveShadow=true;
 const centerLogo=brand('TNG','EARNED NOT GIVEN','#c2c9d1','#404c5c');const label=mesh(new THREE.PlaneGeometry(2.9,.83),new THREE.MeshStandardMaterial({map:centerLogo,roughness:1}),[0,.171,0],[-Math.PI/2,0,0]);label.receiveShadow=true;
 const apron=new THREE.MeshStandardMaterial({map:brand('TNG BOXING','THE NEXT GENERATION'),roughness:.65});mesh(new THREE.PlaneGeometry(5.8,.55),apron,[0,-.02,-3.405],[0,Math.PI,0]);mesh(new THREE.PlaneGeometry(5.8,.55),apron,[0,-.02,3.405]);
 const boardMap=brand('TNG BOXING','SATURDAY NIGHT FIGHTS'),boardMat=new THREE.MeshStandardMaterial({map:boardMap,emissiveMap:boardMap,emissive:0xffffff,emissiveIntensity:.5,roughness:.5});for(const z of[-4.4,4.4])mesh(new THREE.PlaneGeometry(3.8,.95),boardMat,[0,2.5,z],[0,z>0?Math.PI:0,0]);
 const cylinder=new THREE.CylinderGeometry(.027,.027,1,10),postGeo=new THREE.CylinderGeometry(.063,.075,1.65,14),postMat=new THREE.MeshStandardMaterial({color:0x252c36,metalness:.6,roughness:.36});
 function bar(a,b,mat,radius=1){const mid=a.clone().add(b).multiplyScalar(.5);const rod=mesh(cylinder,mat,mid.toArray());rod.scale.set(radius,a.distanceTo(b),radius);rod.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),b.clone().sub(a).normalize());return rod;}
 for(const x of[-3.1,3.1])for(const z of[-3.1,3.1]){
  mesh(postGeo,postMat,[x,.88,z]);const pad=mesh(new THREE.BoxGeometry(.17,.74,.17),x*z>0?red:white,[x,1.12,z]);pad.castShadow=true;
 }
 for(const[y,mat]of[[.63,red],[.93,white],[1.23,dark],[1.52,red]]){
  for(const z of[-3.08,3.08])bar(new THREE.Vector3(-3.08,y,z),new THREE.Vector3(3.08,y,z),mat);
  for(const x of[-3.08,3.08])bar(new THREE.Vector3(x,y,-3.08),new THREE.Vector3(x,y,3.08),mat);
 }
 for(const z of[-3.6,3.6])for(const y of[4,4.18])bar(new THREE.Vector3(-3.8,y,z),new THREE.Vector3(3.8,y,z),metal,.6);
 for(const x of[-3.6,3.6])bar(new THREE.Vector3(x,4,-3.6),new THREE.Vector3(x,4,3.6),metal,.6);
 const lampGeo=new THREE.BoxGeometry(.35,.1,.23),lampMat=new THREE.MeshStandardMaterial({color:0xc5d8e8,emissive:0xd9ecff,emissiveIntensity:2});
 for(const x of[-2.7,-.9,.9,2.7])for(const z of[-3.55,3.55])mesh(lampGeo,lampMat,[x,3.96,z]);
 const crowdMat=new THREE.MeshStandardMaterial({color:0x0b1019,roughness:1}),headGeo=new THREE.SphereGeometry(.085,8,6),torsoGeo=new THREE.CapsuleGeometry(.105,.18,3,8),count=low?64:144,heads=new THREE.InstancedMesh(headGeo,crowdMat,count),bodies=new THREE.InstancedMesh(torsoGeo,crowdMat,count);const temp=new THREE.Object3D();
 for(let i=0;i<count;i++){const row=Math.floor(i/32),a=(i%32)/32*Math.PI*2,r=5+row*.65;temp.position.set(Math.cos(a)*r,.8+row*.35,Math.sin(a)*r);temp.updateMatrix();heads.setMatrixAt(i,temp.matrix);temp.position.y-=.24;temp.updateMatrix();bodies.setMatrixAt(i,temp.matrix);}scene.add(heads,bodies);
 // Illuminated ringside ribbons and overhead light banks.
 const ribbon=new THREE.MeshStandardMaterial({color:0x541022,emissive:0xcf1537,emissiveIntensity:1.1});
 for(const z of[-3.45,3.45])mesh(new THREE.BoxGeometry(6.6,.035,.045),ribbon,[0,.11,z]);
 const shadowCanvas=document.createElement('canvas');shadowCanvas.width=shadowCanvas.height=64;const sg=shadowCanvas.getContext('2d'),gradient=sg.createRadialGradient(32,32,3,32,32,31);gradient.addColorStop(0,'rgba(0,0,0,.48)');gradient.addColorStop(1,'rgba(0,0,0,0)');sg.fillStyle=gradient;sg.fillRect(0,0,64,64);const shadowTexture=new THREE.CanvasTexture(shadowCanvas),shadows=[0,1].map(()=>mesh(new THREE.PlaneGeometry(.65,.5),new THREE.MeshBasicMaterial({map:shadowTexture,transparent:true,depthWrite:false}),[0,.176,0],[-Math.PI/2,0,0]));
 const bag=new THREE.Group();const bagMat=new THREE.MeshPhysicalMaterial({color:0x171c26,roughness:.43,clearcoat:.15,bumpMap:low?null:noise,bumpScale:.003});const body=new THREE.Mesh(new THREE.CapsuleGeometry(.19,.88,8,24),bagMat);body.position.y=.83;body.castShadow=true;bag.add(body);for(const y of[.43,1.22]){const band=new THREE.Mesh(new THREE.CylinderGeometry(.195,.195,.065,24),red);band.position.y=y;bag.add(band);}const bagLabel=new THREE.Mesh(new THREE.PlaneGeometry(.27,.10),new THREE.MeshStandardMaterial({map:brand('TNG','TRAINING'),roughness:.6}));bagLabel.position.set(0,.91,.2);bag.add(bagLabel);for(const x of[-.12,.12]){const chain=new THREE.Mesh(new THREE.CylinderGeometry(.006,.006,1.1,6),metal);chain.position.set(x,1.85,0);chain.rotation.z=x*.2;bag.add(chain);}scene.add(bag);
 return {noise,shadows,bag};
}
export default function BoxingArena3D({animation={},stance='orthodox',active,effects=true,quality='auto',camera='firstperson',outfit='pro',onReady,onError,onFocusArena}){
 const host=useRef(null),latest=useRef(null),sceneControls=useRef(null);latest.current={animation,stance,active,effects,camera,onReady,onError,onFocusArena};const[loading,setLoading]=useState(true),[failure,setFailure]=useState(''),[attempt,setAttempt]=useState(0);
 useEffect(()=>{
  let alive=true,renderer,frame,observer,controls,environment,scene,viewHands;const container=host.current;setLoading(true);setFailure('');latest.current.onReady?.(false);
  try{
   const low=quality==='battery'||(quality==='auto'&&(window.innerWidth<760||window.matchMedia('(pointer:coarse)').matches));renderer=new THREE.WebGLRenderer({antialias:!low,alpha:false,powerPreference:low?'low-power':'high-performance'});renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.05;renderer.shadowMap.type=THREE.PCFSoftShadowMap;
   renderer.domElement.setAttribute('aria-label','Interactive 3D boxing arena. Drag to orbit the camera.');renderer.domElement.setAttribute('role','img');container.appendChild(renderer.domElement);
   scene=new THREE.Scene();scene.background=new THREE.Color(0x080c13);scene.fog=new THREE.FogExp2(0x080c13,.055);
   const perspective=new THREE.PerspectiveCamera(46,1,.035,45);controls=new OrbitControls(perspective,renderer.domElement);controls.enablePan=false;controls.enableDamping=true;controls.dampingFactor=.08;controls.minDistance=1.0;controls.maxDistance=6.8;controls.maxPolarAngle=Math.PI/2-.07;controls.target.set(0,1.05,0);
   sceneControls.current={perspective,controls,preset:null};
   if(!low){const pmrem=new THREE.PMREMGenerator(renderer),room=new RoomEnvironment();environment=pmrem.fromScene(room,.05);scene.environment=environment.texture;scene.environmentIntensity=.45;room.dispose?.();pmrem.dispose();}
   scene.add(new THREE.HemisphereLight(0xd8e5f5,0x17202a,1.3));const key=new THREE.SpotLight(0xffefe0,135,16,.7,.6,2);key.position.set(-2,4.5,2);key.target.position.set(0,1,0);key.castShadow=true;key.shadow.mapSize.set(quality==='high'?2048:1024,quality==='high'?2048:1024);key.shadow.bias=-.0002;key.shadow.normalBias=.015;scene.add(key,key.target);
   const fill=new THREE.DirectionalLight(0x9dbbe0,1.45);fill.position.set(2,3,-2);scene.add(fill);const rim=new THREE.SpotLight(0xe72c4a,65,12,.8,.7);rim.position.set(0,3,-3);rim.target.position.set(0,1,0);scene.add(rim,rim.target);
   const ring=buildArena(scene,low),trainingEquipment=createTrainingEquipment(scene);viewHands=createFirstPersonHands({low});let player,partner,lastRendered=0,lastHit=null,impact=0,currentLow=low,previous=performance.now(),visualNow=0,manualUntil=0;
   const manual=()=>{manualUntil=performance.now()+5000;};controls.addEventListener('start',manual);controls.addEventListener('end',manual);
   const sweatCount=low?8:18,sweat=new THREE.InstancedMesh(new THREE.SphereGeometry(.007,5,4),new THREE.MeshBasicMaterial({color:0xc7e0ec,transparent:true,opacity:.65,depthWrite:false}),sweatCount),drops=[];sweat.frustumCulled=false;sweat.visible=false;scene.add(sweat);const dropMatrix=new THREE.Object3D();
   const resize=()=>{const width=Math.max(1,container.clientWidth),height=Math.max(1,container.clientHeight);currentLow=quality==='battery'||(quality==='auto'&&(width<760||window.matchMedia('(pointer:coarse)').matches));renderer.setPixelRatio(Math.min(window.devicePixelRatio||1,currentLow?1:quality==='high'?1.75:1.25));renderer.shadowMap.enabled=!currentLow;renderer.setSize(width,height,false);perspective.aspect=width/height;perspective.updateProjectionMatrix();};observer=new ResizeObserver(resize);observer.observe(container);resize();
   const focus=()=>latest.current.onFocusArena?.();renderer.domElement.addEventListener('pointerdown',focus);
   const contextLost=e=>{e.preventDefault();if(alive){setFailure('The graphics context paused. Reload the arena to continue.');latest.current.onError?.('3D graphics paused. Your round has been paused.');}};renderer.domElement.addEventListener('webglcontextlost',contextLost);
   assets().then(([gltf,meta])=>{
    if(!alive)return;player=createBoxer(gltf.scene,meta,{kit:0xc51b37,skin:0xb57a56,bumpMap:ring.noise,lowDetail:low,outfit});partner=createBoxer(gltf.scene,meta,{kit:0x174a8b,skin:0x79533d,bumpMap:ring.noise,lowDetail:low,outfit});scene.add(player.root,partner.root);player.root.position.set(0,.18,-.48);partner.root.position.set(0,.18,.35);partner.root.rotation.y=Math.PI;setLoading(false);latest.current.onReady?.(true);
   }).catch(()=>{if(alive){setFailure('Fighter assets could not load. Check the connection and reload the arena.');latest.current.onError?.('The 3D fighters could not load.');}});
   const render=now=>{
    frame=requestAnimationFrame(render);try{if(document.hidden||now-lastRendered<1000/(latest.current.active?(currentLow?30:60):15))return;const dt=Math.min(.05,(now-previous)/1000);previous=now;lastRendered=now;
    const s=latest.current,p=s.animation||{},mode=p.mode||'combo';if(s.active)visualNow+=dt*1000;
    if(player&&partner){
     const distance=p.distance??1.4,gap=s.camera==='firstperson'?Math.max(.95,Math.min(2.6,distance)):.4+Math.max(.45,Math.min(2.6,distance))*.24,targetPlayer=new THREE.Vector3((p.angle||0)*.3,.18,-gap*.5),targetPartner=new THREE.Vector3(0,.18,gap*.5);
     player.root.position.lerp(targetPlayer,Math.min(1,dt*10));partner.root.position.lerp(targetPartner,Math.min(1,dt*10));const facing=Math.atan2(partner.root.position.x-player.root.position.x,partner.root.position.z-player.root.position.z);player.root.rotation.y=facing;partner.root.rotation.y=facing+Math.PI;
     partner.root.visible=!['bag','targets'].includes(mode);partner.setMittMode(mode==='mitts');ring.bag.visible=mode==='bag';ring.bag.position.set(0,.18,gap*.5);ring.bag.rotation.z=p.hit&&s.effects?Math.sin(visualNow*.018)*.035:0;
     const target=mode==='mitts'&&p.target?partner.mittTarget(p.target.move):mode==='targets'&&p.target?player.root.localToWorld(new THREE.Vector3(p.target.lane,p.target.body?1.35:1.62,.85)):mode==='bag'?new THREE.Vector3(0,1.25,gap*.5-.18):partner.headTarget();player.root.visible=s.camera!=='firstperson';player.update(p,visualNow,dt,{stance:s.stance,target,active:s.active&&s.effects});partner.update(p,visualNow,dt,{opponent:true,target:player.headTarget(),active:s.active&&s.effects});
     for(const[i,boxer]of[player,partner].entries()){ring.shadows[i].position.x=boxer.root.position.x;ring.shadows[i].position.z=boxer.root.position.z;ring.shadows[i].visible=i===0||!['bag','targets'].includes(mode);}
     if((p.playerHit||p.hit)&&p.id!==lastHit){lastHit=p.id;impact=s.effects ? .024 : 0;if(s.effects&&!['bag','targets','mitts'].includes(mode)){const origin=p.playerHit?player.headTarget():partner.headTarget();drops.length=0;for(let i=0;i<sweatCount;i++)drops.push({position:origin.clone(),velocity:new THREE.Vector3(Math.sin(i*2.4)*.55,.3+(i%4)*.11,Math.cos(i*2.4)*.55),life:.26});}}
     trainingEquipment.update(p,player,partner,dt);impact=Math.max(0,impact-dt*.12);
     sweat.visible=s.effects&&drops.some(d=>d.life>0);for(let i=0;i<drops.length;i++){const d=drops[i];if(s.active){d.life-=dt;d.velocity.y-=dt*2.4;d.position.addScaledVector(d.velocity,dt);}dropMatrix.position.copy(d.position);dropMatrix.scale.setScalar(Math.max(0,d.life/.26));dropMatrix.updateMatrix();sweat.setMatrixAt(i,dropMatrix.matrix);}sweat.instanceMatrix.needsUpdate=true;
    }
    controls.enabled=s.camera!=='firstperson';
    if(s.camera==='director'&&now>manualUntil){const framing=broadcastFrame(p.distance,p.angle,container.clientHeight>container.clientWidth);const goal=new THREE.Vector3(...framing.position);perspective.position.lerp(goal,Math.min(1,dt*2.7));controls.target.lerp(new THREE.Vector3(...framing.target),Math.min(1,dt*4));const fov=framing.fov-(s.effects?impact*35:0);perspective.fov=THREE.MathUtils.lerp(perspective.fov,fov,Math.min(1,dt*7));perspective.updateProjectionMatrix();}
    const preset=sceneControls.current;if(preset&&preset.preset!==s.camera){preset.preset=s.camera;controls.target.set(0,1.05,0);if(s.camera==='firstperson'){perspective.near=firstPersonLens().near;}else if(s.camera==='director'){const f=broadcastFrame(p.distance,p.angle,container.clientHeight>container.clientWidth);perspective.position.set(...f.position);controls.target.set(...f.target);}else if(s.camera==='broadcast')perspective.position.set(2.4,1.65,1.15);else if(s.camera==='corner')perspective.position.set(3.8,2.8,-3.8);else perspective.position.set(-1.7,1.9,-2.6);if(s.camera!=='firstperson'){perspective.near=.035;perspective.fov=46;controls.update();}perspective.updateProjectionMatrix();}
    if(s.camera==='firstperson'&&player&&partner){const lens=firstPersonLens(container.clientHeight>container.clientWidth);perspective.fov=lens.fov;perspective.near=lens.near;perspective.position.copy(player.eyePosition(!s.effects));const aim=mode==='bag'?new THREE.Vector3(ring.bag.position.x,1.35,ring.bag.position.z):partner.headTarget();perspective.lookAt(aim);perspective.updateProjectionMatrix();renderer.domElement.setAttribute('aria-label','First-person boxing view. Face your opponent and use the punch and defense controls.');}else{controls.update();renderer.domElement.setAttribute('aria-label','Interactive 3D boxing arena. Drag to orbit the camera.');}
    const shake=Math.sin(now*.11)*impact*(s.camera==='firstperson'?.25:1);perspective.position.x+=shake;renderer.render(scene,perspective);if(s.camera==='firstperson'&&player){const targetPoint=trainingEquipment.aimPoint();let viewTarget=null;if(targetPoint){const local=perspective.worldToLocal(targetPoint);const depth=Math.max(.15,-local.z),reach=['5','6'].includes(p.move)?.60:.68;viewTarget=[local.x/depth*reach,local.y/depth*reach,-reach];}viewHands.update({...p,viewTarget},visualNow,s.stance,s.active);viewHands.render(renderer,perspective);}perspective.position.x-=shake;
    }catch{cancelAnimationFrame(frame);if(alive){setFailure('The 3D scene stopped. Reload the arena to continue.');latest.current.onError?.('3D rendering stopped. Your round has been paused.');}}
   };frame=requestAnimationFrame(render);
   return()=>{
    alive=false;cancelAnimationFrame(frame);observer.disconnect();controls.removeEventListener('start',manual);controls.removeEventListener('end',manual);renderer.domElement.removeEventListener('pointerdown',focus);renderer.domElement.removeEventListener('webglcontextlost',contextLost);controls.dispose();sceneControls.current=null;
    const geos=new Set(),materials=new Set(),textures=new Set();scene.traverse(o=>{if(o.geometry)geos.add(o.geometry);for(const m of(o.material?Array.isArray(o.material)?o.material:[o.material]:[])){materials.add(m);for(const v of Object.values(m))if(v?.isTexture)textures.add(v);}});for(const t of textures)t.dispose();for(const m of materials)m.dispose();for(const g of geos)g.dispose();trainingEquipment.dispose();viewHands?.dispose();environment?.dispose();renderer.dispose();renderer.forceContextLoss();renderer.domElement.remove();
   };
  }catch{
   renderer?.dispose();renderer?.domElement?.remove();setFailure('3D graphics are unavailable in this browser. Try a current browser with WebGL 2 enabled.');latest.current.onError?.('3D graphics could not start. Try another browser or device.');
  }
  return()=>{alive=false;cancelAnimationFrame(frame);observer?.disconnect();controls?.dispose();viewHands?.dispose();environment?.dispose();renderer?.dispose();};
 },[quality,attempt,outfit]);
 return <div className="tng-3d-viewport"><div className="tng-3d-canvas" ref={host}/><div className="tng-ring-lens" aria-hidden="true"/>{loading&&!failure&&<div className="tng-3d-loading" role="status"><span className="tng-3d-loader"/>Loading rigged fighters…</div>}{failure&&<div className="tng-3d-loading" role="alert"><strong>3D arena unavailable</strong><p>{failure}</p><button type="button" onClick={()=>setAttempt(n=>n+1)}>Reload arena</button></div>}</div>;
}
