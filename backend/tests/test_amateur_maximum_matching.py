import unittest,random
import test_stabilization as support
from app.amateurs.matching import maximum_candidate_indices
class MaximumMatchingTests(unittest.TestCase):
 def verify(self,n,edges):
  indices=maximum_candidate_indices(n,edges);used=set()
  for k in indices:
   i,j,_,_=edges[k];self.assertNotIn(i,used);self.assertNotIn(j,used);used.update([i,j])
  return len(indices),sum(edges[k][3]for k in indices)
 def test_cardinality_beats_closest_single_pair_and_odd_cycles_work(self):
  self.assertEqual(self.verify(4,[(0,1,{},0),(0,2,{},10),(1,3,{},10)]),(2,20))
  self.assertEqual(self.verify(5,[(0,1,{},1),(1,2,{},1),(2,0,{},1),(2,3,{},1),(3,4,{},1)]),(2,2))
  self.assertEqual(self.verify(3,[]),(0,0))
 def test_exact_maximum_and_lowest_gap_cost_agree_with_exhaustive_small_graphs(self):
  randomizer=random.Random(2026)
  for n in range(2,9):
   for _ in range(12):
    edges=[(i,j,{},randomizer.randrange(20))for i in range(n)for j in range(i+1,n)if randomizer.random()<.5]
    def brute(nodes):
     if not nodes:return(0,0)
     a=min(nodes);left=nodes-{a};best=brute(left)
     for i,j,_,cost in edges:
      b=j if i==a else i if j==a else None
      if b not in left:continue
      count,penalty=brute(left-{b});candidate=(count+1,penalty+cost)
      if (candidate[0],-candidate[1])>(best[0],-best[1]):best=candidate
     return best
    self.assertEqual(self.verify(n,edges),brute(set(range(n))))
 def test_full_supported_roster_returns_100_disjoint_bouts(self):
  edges=[(i,j,{},abs(i-j))for i in range(200)for j in range(i+1,200)]
  self.assertEqual(self.verify(200,edges),(100,100))
