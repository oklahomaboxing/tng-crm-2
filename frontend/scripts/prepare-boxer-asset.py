"""Prepare CC0 MakeHuman data for the TNG clothed, simplified game rig.
Usage: python prepare-boxer-asset.py SOURCE_DIRECTORY INTERMEDIATE_JSON
Source files and attribution are documented in public/game/assets/ATTRIBUTION.md.
"""
import sys,json,math,hashlib
from pathlib import Path
src=Path(sys.argv[1]);out=Path(sys.argv[2]);verts=[];uv=[];faces=[];group=''
for line in (src/'body').read_text().splitlines():
 if line.startswith('v '):verts.append(list(map(float,line.split()[1:4])))
 elif line.startswith('vt '):uv.append(list(map(float,line.split()[1:3])))
 elif line.startswith('g '):group=line[2:]
 elif line.startswith('f ')and group=='body':
  values=[tuple(int(x)-1 for x in item.split('/')[:2])for item in line.split()[1:]]
  for i in range(1,len(values)-1):faces.append([values[0],values[i],values[i+1]])
sourcefiles=['body','rig','weights','assets-license']
for filename,factor in [('caucasian-male-young.target',1/3),('african-male-young.target',1/3),('asian-male-young.target',1/3),('universal-male-young-maxmuscle-averageweight.target',.7),('universal-male-young-averagemuscle-averageweight.target',.3)]:
 sourcefiles.append(filename)
 for line in (src/filename).read_text().splitlines():
  if not line.strip()or line.startswith('#'):continue
  i,x,y,z=line.split();i=int(i)
  for j,v in enumerate([x,y,z]):verts[i][j]+=float(v)*factor
rig=json.loads((src/'rig').read_text());weights=json.loads((src/'weights').read_text())['weights']
ids={v[0]for face in faces for v in face};low=min(verts[i][1]for i in ids);high=max(verts[i][1]for i in ids);scale=1.80/(high-low)
def point(v):return [v[0]*scale,(v[1]-low)*scale,v[2]*scale]
def joint(bone):
 indices=rig['joints'][rig['bones'][bone]['head']];return point([sum(verts[i][j]for i in indices)/len(indices)for j in range(3)])
config=[('hips',None,'root'),('spine','hips','spine04'),('chest','spine','spine01'),('neck','chest','neck01'),('head','neck','head')]
for side in ['L','R']:
 config.extend([(f'clav{side}','chest',f'shoulder01.{side}'),(f'arm{side}',f'clav{side}',f'upperarm01.{side}'),(f'forearm{side}',f'arm{side}',f'lowerarm01.{side}'),(f'hand{side}',f'forearm{side}',f'wrist.{side}'),(f'thigh{side}','hips',f'upperleg01.{side}'),(f'shin{side}',f'thigh{side}',f'lowerleg01.{side}'),(f'foot{side}',f'shin{side}',f'foot.{side}')])
bones=[{'name':n,'parent':p,'position':joint(original)}for n,p,original in config];boneidx={b['name']:i for i,b in enumerate(bones)}
def mapped(name):
 side='L'if name.endswith('.L')else'R'
 if name.startswith('upperarm'):return 'arm'+side
 if name.startswith('lowerarm'):return 'forearm'+side
 if name.startswith(('shoulder','clavicle')):return 'clav'+side
 if name.startswith('upperleg'):return 'thigh'+side
 if name.startswith('lowerleg'):return 'shin'+side
 if name.startswith(('foot','toe')):return 'foot'+side
 if name.startswith(('wrist','finger','thumb')):return 'hand'+side
 if name.startswith(('neck')):return 'neck'
 if name=='head'or name.startswith(('eye','jaw','tongue','special','levator','orbicularis','oris','temporalis','oculi','risorius','platysma')):return 'head'
 if name.startswith('breast')or name in ['spine01','spine02']:return 'chest'
 if name.startswith('spine'):return 'spine'
 return 'hips'
# Bone names not in the coarse mapping are assigned by skeletal ancestry.
def coarse(name):
 if name not in rig['bones']:return 'hips'
 if name.startswith(('upperarm','lowerarm','shoulder','clavicle','upperleg','lowerleg','foot','toe','wrist','finger','thumb','neck','spine','breast'))or name in ['root','head']:return mapped(name)
 parent=rig['bones'][name]['parent'];return coarse(parent)if parent else'hips'
weighted=[{}for _ in verts]
for name,values in weights.items():
 b=boneidx[coarse(name)]
 for i,w in values:weighted[i][b]=weighted[i].get(b,0)+w
influences=[]
for row in weighted:
 values=sorted(row.items(),key=lambda x:x[1],reverse=True)[:4]or[(0,1)];total=sum(w for _,w in values);values=[(i,w/total)for i,w in values];values+= [(0,0)]*(4-len(values));influences.append(values)
positions=[point(v)for v in verts]
for pos in positions:
 if .62<pos[1]<1.02 and abs(pos[0])<.16:pos[2]=min(pos[2],.17)
normals=[[0.,0.,0.]for _ in verts]
for face in faces:
 a,b,c=[positions[v[0]]for v in face];u=[b[i]-a[i]for i in range(3)];v=[c[i]-a[i]for i in range(3)];normal=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
 for i,_ in face:
  for k in range(3):normals[i][k]+=normal[k]
for n in normals:
 length=math.sqrt(sum(v*v for v in n)) or 1
 for k in range(3):n[k]/=length
partfaces={0:[],1:[],2:[],3:[],4:[]}
for face in faces:
 xyz=[positions[v[0]]for v in face];center=[sum(v[k]for v in xyz)/3 for k in range(3)];dominant=[bones[influences[v[0]][0][0]]['name']for v in face];x,y,z=center
 # Hands and feet are replaced by closed gloves and boots. The pelvis is clothed.
 if all(n.startswith('hand')for n in dominant)or all(n.startswith('foot')for n in dominant):continue
 part=0
 if .59<y<1.025 and all(n in ['hips','spine','thighL','thighR']for n in dominant):part=1
 elif 1.025<=y<1.49 and all(n in ['spine','chest','hips']for n in dominant):part=2
 elif y>1.735 or(y>1.67 and z<.055):part=3
 elif 1.585<y<1.62 and abs(x)<.045 and z>.10:part=4
 partfaces[part].append(face)
data={'positions':[],'normals':[],'uv':[],'skinIndex':[],'skinWeight':[],'indices':[],'groups':[],'bones':bones,'eyes':{'L':joint('eye.L'),'R':joint('eye.R')},'height':1.8,'license':'CC0-1.0','source_sha256':{f:hashlib.sha256((src/f).read_bytes()).hexdigest()for f in sourcefiles}}
lookup={}
for part,rows in partfaces.items():
 start=len(data['indices'])
 for face in rows:
  for vi,ti in face:
   key=(vi,ti,part)
   if key not in lookup:
    idx=len(data['positions'])//3;lookup[key]=idx;pos=list(positions[vi]);n=normals[vi]
    if part in [1,2]:
     pad=0.0;pos=[pos[k]+n[k]*pad for k in range(3)]
     if part==1 and abs(pos[0])<.16:pos[2]=min(pos[2],.17)
    data['positions'].extend(round(v,6)for v in pos);data['normals'].extend(round(v,6)for v in n);data['uv'].extend(uv[ti]if 0<=ti<len(uv)else[0,0]);data['skinIndex'].extend(i for i,_ in influences[vi]);data['skinWeight'].extend(round(w,6)for _,w in influences[vi])
   data['indices'].append(lookup[key])
 data['groups'].append({'start':start,'count':len(data['indices'])-start,'material':part})
out.write_text(json.dumps(data,separators=(',',':')));print(json.dumps({'vertices':len(data['positions'])//3,'triangles':len(data['indices'])//3,'bones':len(bones)}))
