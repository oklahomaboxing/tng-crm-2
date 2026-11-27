"""TNG local-match experience policy based on reported bouts, not an eligibility certification."""
POLICY={'version':'tng_novice_0_10_open_11_v1','novice_max_bouts':10,'open_min_bouts':11,'consideration_min_bouts':8}
def experience_class(bouts):
 if not isinstance(bouts,int) or isinstance(bouts,bool) or not 0<=bouts<=1000:return 'review'
 return 'novice' if bouts<=10 else 'open'
def experience_pair(a,b,allow_consideration=True):
 classes=[experience_class(a.get('bouts')),experience_class(b.get('bouts'))]
 if 'review' in classes:return None
 mixed=classes[0]!=classes[1]
 if mixed and (not allow_consideration or min(a['bouts'],b['bouts'])<8):return None
 return {'experience_classes':classes,'novice_open_review_required':mixed,'experience_policy_version':POLICY['version']}
