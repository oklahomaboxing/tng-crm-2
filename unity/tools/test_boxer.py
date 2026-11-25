import unittest,math,json,struct,pathlib
from convert_boxer import convert,ROOT
class AssetChecks(unittest.TestCase):
 def test_skinning_and_geometry(self):
  r=convert();count=len(r['positions'])//3
  self.assertEqual(count,9055);self.assertEqual(len(r['bones']),19)
  self.assertEqual(len(r['normals']),count*3);self.assertEqual(len(r['uv']),count*2)
  self.assertEqual(len(r['weights']),count*4);self.assertEqual(len(r['joints']),count*4)
  self.assertTrue(all(math.isfinite(x) for k in ['positions','normals','uv','weights'] for x in r[k]))
  for i in range(count):
   self.assertAlmostEqual(sum(r['weights'][i*4:i*4+4]),1,places=5)
  self.assertTrue(all(0<=j<19 for j in r['joints']))
  for i,b in enumerate(r['bones']):self.assertTrue(-1<=b['parent']<i)
  self.assertEqual(sum(len(g['indices']) for g in r['groups'])//3,16198)
  self.assertTrue(all(0<=j<count for g in r['groups'] for j in g['indices']))
  self.assertEqual(r['license'],'CC0-1.0')
 def test_coordinate_reflection(self):
  r=convert();meta=json.loads((ROOT/'frontend/public/game/assets/boxer-rig-v1.json').read_text())
  for actual,original in zip(r['bones'],meta['bones']):
   self.assertEqual(actual['position'],[original['position'][0],original['position'][1],-original['position'][2]])
 def test_conversion_is_deterministic(self):
  convert();p=ROOT/'unity/TngBoxing/Assets/Resources/Boxer.json';before=p.read_bytes();convert();self.assertEqual(before,p.read_bytes())
if __name__=='__main__':unittest.main()
