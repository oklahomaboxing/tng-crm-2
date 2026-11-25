"""Package a Godot source project; never include editor caches or credentials."""
import argparse,hashlib,json,pathlib,shutil,zipfile
root=pathlib.Path(__file__).resolve().parents[1]
project=root/'godot/TNGAmateur'
out=root/'frontend/public/downloads'
def build(pack=None):
 out.mkdir(parents=True,exist_ok=True)
 archive=out/'TNGOS-Godot-Amateur-Prototype.zip'
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for path in sorted(project.rglob('*')):
   rel=path.relative_to(project)
   if not path.is_file() or any(part in {'.godot','exports','__pycache__'} for part in rel.parts):continue
   if path.suffix in {'.zip','.pck','.tmp'}:continue
   info=zipfile.ZipInfo(str(rel).replace('\\','/'),date_time=(2026,1,1,0,0,0))
   info.compress_type=zipfile.ZIP_DEFLATED
   info.external_attr=0o644<<16
   z.writestr(info,path.read_bytes())
 with zipfile.ZipFile(archive) as z:
  assert z.testzip() is None
  assert {'project.godot','main.tscn','START_HERE.md','assets/boxer.glb','scripts/main.gd','tests/test_keyboard.gd'}<=set(z.namelist())
  assert all('.godot/' not in n for n in z.namelist())
 files=[archive]
 if pack:
  pack=pathlib.Path(pack)
  assert pack.read_bytes()[:4]==b'GDPC','Not a Godot game pack'
  dest=out/'TNGOS-Amateur-Boxing.pck';shutil.copyfile(pack,dest);files.append(dest)
 manifest={'version':'0.1.0','engine':'Godot 4.6.3 Standard','kind':'source prototype and Godot resource pack','standalone_executable':False,'files':[{'name':p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}for p in files]}
 (out/'tngos-godot-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 print(json.dumps(manifest))
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--pack');build(parser.parse_args().pack)
