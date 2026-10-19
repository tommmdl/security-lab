#!/usr/bin/env python3
"""Round-trip controlled Unicode notes only against the Alpine previews."""
import json,sys,urllib.request,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/'tracing-lab/scripts'))
from client import forward
fixture=['Ação e automação','English note','São Paulo — café','日本語のメモ','Emoji 🚀',"O'Reilly & <xml>literal</xml>",'e\u0301 and é']
def run(base):
 ids=[]
 def request(path,body=None,method=None):
  r=urllib.request.Request(base+path,data=None if body is None else json.dumps(body).encode(),method=method,headers={'Content-Type':'application/json'})
  with urllib.request.urlopen(r,timeout=10) as response:return json.load(response) if response.status!=204 else None
 try:
  for title in fixture:ids.append((request('/notes',{'title':title})['id'],title))
  actual={n['id']:n['title'] for n in request('/notes')['notes']};assert all(actual[i]==t for i,t in ids)
  return {'controlled_rows':len(ids),'all_titles_preserved':True,'cleanup':'Only IDs created by this test are removed'}
 finally:
  for i,_ in ids:request('/notes/'+str(i),method='DELETE')
results={'docker':run('http://127.0.0.1:8016')}
with forward('notes-lab','notes-api-alpine',80) as base:results['kubernetes']=run(base)
(ROOT/'.local/api-alpine/unicode-tests.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results,indent=2))
