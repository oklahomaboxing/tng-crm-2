import * as THREE from'three';
export const GYM_LAYOUT=Object.freeze({room:{width:16,depth:18,height:4.6},ringHalf:3.4,walkway:.85,bagX:5.65,bagZ:[-4.8,-1.6,1.6,4.8],warmUp:{x:-5.65,z:.2,width:2.45,depth:7.4},benches:[[-5.7,-5.5],[-5.7,5.5]]});
// Background equipment stays outside the ring and its clear perimeter walkway.
export function buildTrainingGym(scene,{brand,noise,low=false}={}){
 const wall=new THREE.MeshStandardMaterial({color:0x4b535e,roughness:.94}),rubber=new THREE.MeshStandardMaterial({color:0x151d27,roughness:.96,bumpMap:low?null:noise,bumpScale:.004}),steel=new THREE.MeshStandardMaterial({color:0x454e5a,metalness:.65,roughness:.4}),black=new THREE.MeshStandardMaterial({color:0x121820,roughness:.55}),red=new THREE.MeshStandardMaterial({color:0x9c1c35,roughness:.62}),light=new THREE.MeshBasicMaterial({color:0xc3d4e1});
 const mesh=(geo,mat,pos,rot)=>{const m=new THREE.Mesh(geo,mat);m.position.set(...pos);if(rot)m.rotation.set(...rot);scene.add(m);return m;};
 for(const x of[-8,8])mesh(new THREE.BoxGeometry(.16,4.7,18),wall,[x,2.2,0]);
 for(const z of[-9,9])mesh(new THREE.BoxGeometry(16,4.7,.16),wall,[0,2.2,z]);
 mesh(new THREE.PlaneGeometry(16,18),new THREE.MeshStandardMaterial({color:0x171e28,roughness:1,side:THREE.DoubleSide}),[0,4.6,0],[Math.PI/2,0,0]);
 // Three functional zones: ring, bag lane, and warm-up floor.
 mesh(new THREE.PlaneGeometry(2.45,13),rubber,[GYM_LAYOUT.bagX,-.115,0],[-Math.PI/2,0,0]);
 mesh(new THREE.PlaneGeometry(GYM_LAYOUT.warmUp.width,GYM_LAYOUT.warmUp.depth),rubber,[GYM_LAYOUT.warmUp.x,-.114,GYM_LAYOUT.warmUp.z],[-Math.PI/2,0,0]);
 for(const x of[4.35,6.95,-6.95,-4.35])mesh(new THREE.BoxGeometry(.035,.006,13),red,[x,-.108,0]);
 for(let i=0;i<6;i++)mesh(new THREE.PlaneGeometry(1.65,.018),new THREE.MeshBasicMaterial({color:0x6d7887}),[-5.65,-.107,-2.8+i*1.1],[-Math.PI/2,0,0]);
 const bagGeometry=new THREE.CapsuleGeometry(.21,.98,low?4:7,low?12:20),bandGeometry=new THREE.CylinderGeometry(.215,.215,.055,16),chainGeometry=new THREE.CylinderGeometry(.007,.007,2.0,6),count=GYM_LAYOUT.bagZ.length,bags=new THREE.InstancedMesh(bagGeometry,black,count),bands=new THREE.InstancedMesh(bandGeometry,red,count*2),chains=new THREE.InstancedMesh(chainGeometry,steel,count*2),temp=new THREE.Object3D();
 for(let i=0;i<count;i++){const z=GYM_LAYOUT.bagZ[i];temp.position.set(GYM_LAYOUT.bagX,1.40,z);temp.rotation.set(0,0,0);temp.updateMatrix();bags.setMatrixAt(i,temp.matrix);for(let j=0;j<2;j++){temp.position.set(GYM_LAYOUT.bagX,j?1.91:.88,z);temp.updateMatrix();bands.setMatrixAt(i*2+j,temp.matrix);temp.position.set(GYM_LAYOUT.bagX+(j?.12:-.12),3.05,z);temp.updateMatrix();chains.setMatrixAt(i*2+j,temp.matrix);}}
 bags.castShadow=!low;scene.add(bags,bands,chains);
 for(const[x,z]of GYM_LAYOUT.benches){mesh(new THREE.BoxGeometry(1.65,.12,.52),black,[x,.48,z]);for(const dx of[-.62,.62])mesh(new THREE.BoxGeometry(.08,.57,.40),steel,[x+dx,.15,z]);}
 // High wall windows and strip lighting leave the play sightline unobstructed.
 for(const z of[-8.88,8.88])for(const x of[-5,0,5]){mesh(new THREE.PlaneGeometry(3.1,.9),light,[x,3.45,z],[0,z>0?Math.PI:0,0]);for(const offset of[-.8,.8])mesh(new THREE.BoxGeometry(.05,.94,.07),steel,[x+offset,3.45,z]);}
 for(const x of[-5.2,5.2])for(const z of[-5,0,5])mesh(new THREE.BoxGeometry(.10,.05,2.2),light,[x,4.48,z]);
 const signs=[['BAG WORK','FOCUS • POWER • CONTROL',5.65,-8.88],['WARM UP','MOVE WITH PURPOSE',-5.65,-8.88]];
 for(const[text,sub,x,z]of signs){const map=brand(text,sub,'#dbe3ed','#182331');mesh(new THREE.PlaneGeometry(2.4,.6),new THREE.MeshStandardMaterial({map,emissiveMap:map,emissive:0xffffff,emissiveIntensity:.17,roughness:.7}),[x,2.45,z]);}
 const columns=new THREE.InstancedMesh(new THREE.BoxGeometry(.18,4.7,.18),steel,6);for(let i=0;i<6;i++){temp.position.set(i<3?-7.86:7.86,2.2,[-6,0,6][i%3]);temp.updateMatrix();columns.setMatrixAt(i,temp.matrix);}scene.add(columns);
}
