"""Convert the bundled CC0 GLB into Unity JsonUtility data; no third-party importer."""
import json,struct,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[2]
def convert():
 data=(ROOT/'frontend/public/game/assets/boxer-rig-v1.glb').read_bytes()
 assert data[:4]==b'glTF'
 length=struct.unpack_from('<I',data,12)[0];doc=json.loads(data[20:20+length]);base=28+length
 sizes={5126:('f',4),5123:('H',2),5125:('I',4),5121:('B',1)}
 def read(idx):
  a=doc['accessors'][idx];v=doc['bufferViews'][a['bufferView']];fmt,size=sizes[a['componentType']];n={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}[a['type']]
  return [list(struct.unpack_from('<'+fmt*n,data,base+v.get('byteOffset',0)+a.get('byteOffset',0)+i*v.get('byteStride',n*size))) for i in range(a['count'])]
 p=doc['meshes'][0]['primitives'];at=p[0]['attributes'];flat=lambda vals:[x for row in vals for x in row]
 meta=json.loads((ROOT/'frontend/public/game/assets/boxer-rig-v1.json').read_text());names=[b['name'] for b in meta['bones']]
 positions=read(at['POSITION']);normals=read(at['NORMAL'])
 # Reflect Z and reverse winding for Unity's left-handed coordinates.
 for arr in (positions,normals):
  for v in arr:v[2]=-v[2]
 bones=[]
 for b in meta['bones']:
  pos=b['position'];bones.append({'name':b['name'],'parent':names.index(b['parent']) if b['parent'] else -1,'position':[pos[0],pos[1],-pos[2]]})
 joint_names=[doc['nodes'][j]['name'] for j in doc['skins'][0]['joints']]
 joints=[[names.index(joint_names[int(j)]) for j in row] for row in read(at['JOINTS_0'])]
 groups=[]
 for pr in p:
  indices=flat(read(pr['indices']))
  for i in range(0,len(indices),3):indices[i+1],indices[i+2]=indices[i+2],indices[i+1]
  groups.append({'name':doc.get('materials',[])[pr.get('material',0)].get('name','skin'),'indices':indices})
 result={'positions':flat(positions),'normals':flat(normals),'uv':flat(read(at['TEXCOORD_0'])),'joints':flat(joints),'weights':flat(read(at['WEIGHTS_0'])),'bones':bones,'groups':groups,'license':'CC0-1.0'}
 assert len(result['weights'])==len(positions)*4
 out=ROOT/'unity/TngBoxing/Assets/Resources/Boxer.json';out.write_text(json.dumps(result,separators=(',',':'))+'\n');return result
if __name__=='__main__':
 r=convert();print('Converted',len(r['positions'])//3,'vertices;',len(r['bones']),'bones;',len(r['groups']),'materials')
