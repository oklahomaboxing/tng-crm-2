import * as THREE from'three';
import{sampleMotion,firstPersonPunchPath}from'./fightPresentation.mjs';
// Camera-space view model avoids projecting the full body's gloves into the lens.
export function createFirstPersonHands({low=false}={}){
 const scene=new THREE.Scene(),camera=new THREE.PerspectiveCamera(76,1,.025,3),hands={};
 scene.add(new THREE.HemisphereLight(0xf3f6ff,0x263348,2.1));const light=new THREE.DirectionalLight(0xffeadc,2.5);light.position.set(-2,3,1);scene.add(light);
 const Mat=low?THREE.MeshStandardMaterial:THREE.MeshPhysicalMaterial;
 const leather=new Mat({color:0xc91a38,roughness:.32,...(!low?{clearcoat:.4,clearcoatRoughness:.3}:{})}),skin=new THREE.MeshStandardMaterial({color:0xb57a56,roughness:.55}),trim=new THREE.MeshStandardMaterial({color:0xe9edf4,roughness:.5});
 const add=(geo,mat,parent,pos,scale)=>{const m=new THREE.Mesh(geo,mat);m.position.set(...pos);if(scale)m.scale.set(...scale);parent.add(m);return m;};
 for(const side of['L','R']){
  const group=new THREE.Group();scene.add(group);hands[side]=group;const sign=side==='L'?-1:1;
  add(new THREE.SphereGeometry(1,20,14),leather,group,[0,0,0],[.076,.089,.10]);
  add(new THREE.SphereGeometry(1,14,10),leather,group,[-sign*.063,-.035,.025],[.034,.055,.048]);
  const cuff=add(new THREE.CylinderGeometry(.056,.059,.065,16),leather,group,[0,-.016,.085]);cuff.rotation.x=Math.PI/2;
  const tape=add(new THREE.CylinderGeometry(.052,.056,.025,16),trim,group,[0,-.016,.125]);tape.rotation.x=Math.PI/2;
  const wrist=new THREE.Vector3(0,-.016,.14),elbow=new THREE.Vector3(sign*.035,-.23,.41),direction=elbow.clone().sub(wrist);const arm=add(new THREE.CylinderGeometry(.044,.060,direction.length(),16),skin,group,wrist.clone().add(elbow).multiplyScalar(.5).toArray());arm.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),direction.normalize());
  add(new THREE.PlaneGeometry(.056,.025),trim,group,[0,.012,.1005]);
 }
 let sample=null,action=null,move=null,start=0,aim=null;
 function update(pose,now,stance='orthodox',active=true){
  const id=pose.actionId??pose.id;
  if(/^[1-6]$/.test(pose.move||'')&&(id!==action||move!==pose.move)){action=id;move=pose.move;start=now;aim=pose.viewTarget||null;}else if(id!==action&&!/^[1-6]$/.test(pose.move||'')){action=id;move=null;}
  const duration=pose.actionDuration||380;const supplied=pose.actionProgress;
  if(Number.isFinite(supplied))sample=sampleMotion(sample,id,supplied,now,duration);
  const progress=Number.isFinite(supplied)?sample.value:(now-start)/duration;
  const punching=move&&progress>=0&&progress<1;
  const lead=stance==='southpaw'?'R':'L',punchSide=punching?(['1','3','5'].includes(move)?lead:lead==='L'?'R':'L'):null;
  for(const side of['L','R']){
   const sign=side==='L'?-1:1,group=hands[side],isLead=side===lead;const base=new THREE.Vector3(sign*(isLead?.18:.20),isLead?-.145:-.17,isLead?-.43:-.40);
   if(pose.move==='bodyBlock')base.y-=.13;
   if(side===punchSide){const path=firstPersonPunchPath(move,progress,base.toArray(),pose.contactFraction||.43,aim);base.fromArray(path.position);group.rotation.set(...path.rotation);}else group.rotation.set(0,sign*.12,sign*-.14);
   group.position.copy(base);
  }
 }
 function render(renderer,perspective){camera.fov=perspective.fov;camera.aspect=perspective.aspect;camera.updateProjectionMatrix();const previous=renderer.autoClear;renderer.autoClear=false;renderer.clearDepth();renderer.render(scene,camera);renderer.autoClear=previous;}
 function dispose(){const geometries=new Set(),materials=new Set();scene.traverse(o=>{if(o.geometry)geometries.add(o.geometry);if(o.material)materials.add(o.material);});for(const g of geometries)g.dispose();for(const m of materials)m.dispose();}
 return {scene,camera,hands,update,render,dispose};
}
