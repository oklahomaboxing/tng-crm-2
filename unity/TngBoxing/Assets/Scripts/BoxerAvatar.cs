using System;
using System.Collections.Generic;
using UnityEngine;
namespace TNG.Boxing {
[Serializable] public class RigBone { public string name; public int parent; public float[] position; }
[Serializable] public class RigGroup { public string name; public int[] indices; }
[Serializable] public class RigAsset { public float[] positions,normals,uv,weights; public int[] joints; public RigBone[] bones; public RigGroup[] groups; }
public sealed class BoxerAvatar : MonoBehaviour {
 readonly Dictionary<string,Transform> joints=new Dictionary<string,Transform>();
 readonly Dictionary<string,Quaternion> rest=new Dictionary<string,Quaternion>();
 public float Health=100,Stamina=100; public bool Guard,BodyGuard; public int Punch=-1; public float PunchStart=-10,SlipUntil,RollUntil,HitUntil;
 public static Material Material(Color color,float smooth=.3f) { var m=new Material(Shader.Find("Standard"));m.color=color;m.SetFloat("_Glossiness",smooth);return m; }
 public static GameObject Shape(PrimitiveType type,Transform parent,Vector3 position,Vector3 scale,Material material) {
  var g=GameObject.CreatePrimitive(type);g.transform.SetParent(parent,false);g.transform.localPosition=position;g.transform.localScale=scale;g.GetComponent<Renderer>().sharedMaterial=material;Destroy(g.GetComponent<Collider>());return g;
 }
 public void Initialize(Color kit,Color skin) {
  var a=JsonUtility.FromJson<RigAsset>(Resources.Load<TextAsset>("Boxer").text);var bs=new Transform[a.bones.Length];var bind=new Matrix4x4[bs.Length];
  for(int i=0;i<bs.Length;i++){var b=a.bones[i];bs[i]=new GameObject(b.name).transform;bs[i].SetParent(b.parent<0?transform:bs[b.parent],false);bs[i].position=transform.TransformPoint(new Vector3(b.position[0],b.position[1],b.position[2]));joints[b.name]=bs[i];rest[b.name]=bs[i].localRotation;bind[i]=bs[i].worldToLocalMatrix*transform.localToWorldMatrix;}
  var mesh=new Mesh{name="TNG CC0 athlete"};int count=a.positions.Length/3;var vertices=new Vector3[count];var normals=new Vector3[count];var uv=new Vector2[count];var weights=new BoneWeight[count];
  for(int i=0;i<count;i++){vertices[i]=new Vector3(a.positions[i*3],a.positions[i*3+1],a.positions[i*3+2]);normals[i]=new Vector3(a.normals[i*3],a.normals[i*3+1],a.normals[i*3+2]);uv[i]=new Vector2(a.uv[i*2],a.uv[i*2+1]);weights[i]=new BoneWeight{boneIndex0=a.joints[i*4],boneIndex1=a.joints[i*4+1],boneIndex2=a.joints[i*4+2],boneIndex3=a.joints[i*4+3],weight0=a.weights[i*4],weight1=a.weights[i*4+1],weight2=a.weights[i*4+2],weight3=a.weights[i*4+3]};}
  mesh.vertices=vertices;mesh.normals=normals;mesh.uv=uv;mesh.boneWeights=weights;mesh.bindposes=bind;mesh.subMeshCount=a.groups.Length;
  var mats=new Material[a.groups.Length];for(int i=0;i<mats.Length;i++){mesh.SetTriangles(a.groups[i].indices,i);string n=a.groups[i].name.ToLowerInvariant();mats[i]=Material(n.Contains("hair")?new Color(.04f,.025f,.02f):n.Contains("short")||n.Contains("vest")?kit:n.Contains("lip")?skin*.65f:skin);}
  mesh.RecalculateBounds();var renderer=gameObject.AddComponent<SkinnedMeshRenderer>();renderer.sharedMesh=mesh;renderer.bones=bs;renderer.rootBone=bs[0];renderer.sharedMaterials=mats;renderer.localBounds=new Bounds(Vector3.up,new Vector3(3,3,3));
  foreach(string side in new[]{"L","R"}) {var glove=Shape(PrimitiveType.Sphere,joints["hand"+side],Vector3.zero,new Vector3(.19f,.23f,.23f),Material(kit,.65f));Shape(PrimitiveType.Cube,glove.transform,new Vector3(0,0,-.4f),new Vector3(.6f,.35f,.15f),Material(Color.white));Shape(PrimitiveType.Capsule,joints["foot"+side],new Vector3(0,.035f,-.03f),new Vector3(.13f,.11f,.25f),Material(new Color(.035f,.04f,.05f)));}
 }
 public Vector3 Head => transform.TransformPoint(new Vector3(0,1.66f,0));
 void Bone(string name,Vector3 euler){joints[name].localRotation=rest[name]*Quaternion.Euler(euler);}
 void LateUpdate(){
  float breathing=Mathf.Sin(Time.time*3)*1.5f;float hit=Time.time<HitUntil?12:0;float roll=Time.time<RollUntil?22:0;float slip=Time.time<SlipUntil?16:0;
  Bone("spine",new Vector3(5+roll,slip,hit));Bone("chest",new Vector3(3+breathing,-slip*.5f,0));Bone("neck",new Vector3(7,0,0));
  foreach(string s in new[]{"L","R"}){float sign=s=="L"?1:-1;Bone("arm"+s,new Vector3(-25,sign*12,sign*(Guard?-65:-48)));Bone("forearm"+s,new Vector3(0,sign*(BodyGuard?65:105),0));Bone("thigh"+s,new Vector3(-6,0,sign*5));Bone("shin"+s,new Vector3(12,0,0));}
  float t=(Time.time-PunchStart)/.46f;if(Punch>=0&&t<1){string side=Punch%2==0?"L":"R";float sign=side=="L"?1:-1;float extension=Mathf.Sin(Mathf.Clamp01(t)*Mathf.PI);bool hook=Punch==2||Punch==3,upper=Punch>=4;Bone("arm"+side,new Vector3(-25-extension*(upper?60:35),sign*(12+extension*(hook?65:10)),sign*(-48+extension*30)));Bone("forearm"+side,new Vector3(upper?-extension*35:0,sign*(105-extension*(hook?35:95)),0));Bone("chest",new Vector3(3,sign*extension*18,0));}
 }
}
}
