import fs from 'node:fs/promises';
import * as THREE from 'three';
import {GLTFExporter}from'three/addons/exporters/GLTFExporter.js';
class FileReaderPolyfill{
 readAsArrayBuffer(blob){blob.arrayBuffer().then(result=>{this.result=result;this.onloadend?.();});}
 readAsDataURL(blob){blob.arrayBuffer().then(result=>{this.result='data:application/octet-stream;base64,'+Buffer.from(result).toString('base64');this.onloadend?.();});}
}
globalThis.FileReader=FileReaderPolyfill;
const d=JSON.parse(await fs.readFile(process.argv[2],'utf8')),dest=process.argv[3];
const geometry=new THREE.BufferGeometry();
for(const[name,key,size,Type]of[['position','positions',3,THREE.Float32BufferAttribute],['normal','normals',3,THREE.Float32BufferAttribute],['uv','uv',2,THREE.Float32BufferAttribute],['skinIndex','skinIndex',4,THREE.Uint16BufferAttribute],['skinWeight','skinWeight',4,THREE.Float32BufferAttribute]])geometry.setAttribute(name,new Type(d[key],size));
geometry.setIndex(d.indices);for(const g of d.groups)if(g.count)geometry.addGroup(g.start,g.count,g.material);
const materials=[['skin',0xb87856,.53],['shorts',0x9e132b,.7],['vest',0xb51535,.72],['hair',0x101116,.96],['lips',0x7a3e32,.66]].map(([name,color,roughness])=>{const m=new THREE.MeshStandardMaterial({color,roughness,metalness:0});m.name=name;return m;});
const bones=d.bones.map(b=>{const bone=new THREE.Bone();bone.name=b.name;return bone;}),lookup=Object.fromEntries(d.bones.map((b,i)=>[b.name,{...b,bone:bones[i]}]));
for(const b of d.bones){const bone=lookup[b.name].bone;bone.position.fromArray(b.position);if(b.parent){bone.position.sub(new THREE.Vector3().fromArray(lookup[b.parent].position));lookup[b.parent].bone.add(bone);}}
const mesh=new THREE.SkinnedMesh(geometry,materials);mesh.name='TNG-Boxer';mesh.add(lookup.hips.bone);mesh.updateMatrixWorld(true);mesh.bind(new THREE.Skeleton(bones));mesh.normalizeSkinWeights();mesh.castShadow=true;mesh.receiveShadow=true;
const scene=new THREE.Scene();scene.name='TNG rigged training boxer';scene.add(mesh);
const binary=await new GLTFExporter().parseAsync(scene,{binary:true,trs:true});await fs.mkdir(dest,{recursive:true});await fs.writeFile(dest+'/boxer-rig-v1.glb',Buffer.from(binary));
const meta={height:d.height,bones:d.bones,eyes:d.eyes,license:d.license,source_sha256:d.source_sha256,vertex_count:d.positions.length/3,triangle_count:d.indices.length/3};await fs.writeFile(dest+'/boxer-rig-v1.json',JSON.stringify(meta,null,2));
console.log(JSON.stringify({bytes:binary.byteLength,vertices:meta.vertex_count,triangles:meta.triangle_count,bones:bones.length}));
