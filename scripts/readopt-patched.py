#!/usr/bin/env python3
"""Re-adopt patched images in docker-lab with a real rollback. Run from the folder that holds docker-lab.

Same PostgreSQL 17.11 / Alpine 3.24 base on both sides, so the image swap reuses the adopted volume.
The logical backup is still taken and verified before the swap. Dumps and row contents stay private."""
import argparse,hashlib,json,os,subprocess,time,urllib.request,uuid
os.umask(0o077)
from pathlib import Path
ROOT=Path.cwd();LAB=Path(__file__).resolve().parents[1]
PRIVATE=LAB/'.local/readopt';PUBLIC=LAB/'evidence/readopt';PRIVATE.mkdir(parents=True,exist_ok=True);PUBLIC.mkdir(parents=True,exist_ok=True)
# Adopted before the new findings (scans of 2026-10-19 allowed them; run 40933751374 blocked them).
OLD={'postgres':'ghcr.io/tommmdl/docker-lab@sha256:8b6813ec76804698c33e4dac8f501ca8f641affcbd27cbc3b7dd6fdb02874fc3','notes-api-otel':'ghcr.io/tommmdl/docker-lab@sha256:e01c467c0987cc2d999778a4e9ee429bee1d6af4bcdef80e38ce620b95a0b8da'}
NEW={t['name']:t['image'] for t in json.loads((LAB/'config/targets.json').read_text()) if t['name'] in OLD}
BASIC_API=next(t['image'] for t in json.loads((LAB/'config/targets.json').read_text()) if t['name']=='notes-api')
QUERY="SELECT coalesce(json_agg(n ORDER BY id),'[]'::json) FROM (SELECT id,title,created_at FROM notes) n"
PORT=8000
def run(args,data=None):return subprocess.check_output(args,input=data)
def write(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
def api(path='/notes',body=None,method=None):
 req=urllib.request.Request(f'http://127.0.0.1:{PORT}'+path,data=None if body is None else json.dumps(body).encode(),method=method,headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=10) as r:return json.load(r) if r.status!=204 else None
def ready():
 for _ in range(120):
  try:
   if api('/readyz')['status']=='ready':return
  except Exception:pass
  time.sleep(1)
 raise RuntimeError('API not ready')
def compose(file,*args,data=None):return run(['bash',str(ROOT/'docker-lab/scripts/compose.sh'),'-p','docker-lab','-f',str(file),*args],data)
def variant(name,db,api_image,api_env=None):
 c=json.loads(run(['bash',str(ROOT/'docker-lab/scripts/compose.sh'),'-p','docker-lab','config','--format','json']))
 c['services']['db']['image']=db;c['services']['api']['image']=api_image
 if api_env:c['services']['api'].setdefault('environment',{}).update(api_env)
 p=PRIVATE/(name+'.json');write(p,c);return p
def sql(file,q):return compose(file,'exec','-T','db','psql','-U','notes_admin','-d','notes','-Atc',q).decode().strip()
def rows(file):return json.loads(sql(file,QUERY))
def digest(r):return hashlib.sha256(json.dumps(r,sort_keys=True).encode()).hexdigest()
def healthy(file):
 for _ in range(90):
  if '"healthy"' in compose(file,'ps','--format','json','db').decode():return
  time.sleep(1)
 raise RuntimeError('database not healthy')
def gosu(file):return compose(file,'exec','-T','db','gosu','--version').decode().strip()
def certifi(file):return compose(file,'exec','-T','api','python','-c',"import importlib.metadata as m;print(m.version('certifi'))").decode().strip()
def running_image(service):return run(['docker','inspect','--format','{{.Config.Image}}','docker-lab-'+service+'-1']).decode().strip()
def proof(name,checks,extra):
 result={'verified_at_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'checks_passed':len(checks),'checks':checks,**extra}
 write(PUBLIC/(name+'.json'),result);print(json.dumps(result,indent=2),flush=True)
def postgres():
 old=variant('postgres-old',OLD['postgres'],BASIC_API);new=variant('postgres-new',NEW['postgres'],BASIC_API);checks=[];started=time.time()
 compose(old,'up','-d','--no-build','db','api');healthy(old);ready()
 assert running_image('db')==OLD['postgres'] and 'go1.27.2' in gosu(old);checks.append('Database runs the previously adopted image, whose gosu reports go1.27.2')
 # Probe notes from an interrupted earlier attempt are removed so the comparison starts from the lab's own notes.
 for n in api()['notes']:
  if n['title'].startswith('readopt-'):api(f"/notes/{n['id']}",method='DELETE')
 original=rows(old)
 pre=api('/notes',{'title':'readopt-pre-'+uuid.uuid4().hex[:8]},'POST')['id']
 compose(old,'stop','api');before=rows(old);assert any(r['id']==pre for r in before);checks.append('API stopped after a pre-cutover write; writes paused for the backup')
 dump=compose(old,'exec','-T','db','pg_dump','-U','notes_admin','-d','notes','-Fc','--no-owner','--no-acl');(PRIVATE/'notes-before.dump').write_bytes(dump)
 sql(old,'SELECT 1');compose(old,'exec','-T','db','createdb','-U','notes_admin','notes_readopt_check')
 try:
  compose(old,'exec','-T','db','pg_restore','-U','notes_admin','-d','notes_readopt_check','--no-owner','--no-acl','--exit-on-error','--single-transaction',data=dump)
  check=json.loads(compose(old,'exec','-T','db','psql','-U','notes_admin','-d','notes_readopt_check','-Atc',QUERY).decode())
 finally:compose(old,'exec','-T','db','dropdb','-U','notes_admin','notes_readopt_check')
 assert digest(check)==digest(before);checks.append('Logical backup restored in a separate check database with identical rows')
 compose(new,'up','-d','--no-build','db');healthy(new)
 assert running_image('db')==NEW['postgres'] and 'go1.27.3' in gosu(new);checks.append('Patched image runs on the same volume and its gosu reports go1.27.3')
 assert digest(rows(new))==digest(before);checks.append('Every row is unchanged after the cutover')
 compose(new,'up','-d','--no-build','api');ready()
 post=api('/notes',{'title':'readopt-post-'+uuid.uuid4().hex[:8]},'POST')['id'];checks.append('API accepts a post-cutover write on the patched database')
 compose(old,'up','-d','--no-build','db');healthy(old);ready()
 assert running_image('db')==OLD['postgres'] and 'go1.27.2' in gosu(old);back=rows(old)
 assert any(r['id']==post for r in back) and any(n['id']==post for n in api()['notes']);checks.append('Real rollback to the previous image keeps the post-cutover note, read through the API')
 compose(new,'up','-d','--no-build','db');healthy(new);ready()
 assert running_image('db')==NEW['postgres'] and digest(rows(new))==digest(back);checks.append('Return to the patched image keeps every row, including the rollback-period state')
 api(f'/notes/{pre}',method='DELETE');api(f'/notes/{post}',method='DELETE')
 final=rows(new);assert digest(final)==digest(original);checks.append('Removing the two probe notes leaves exactly the original notes')
 proof('postgres',checks,{'previous_image':OLD['postgres'],'patched_image':NEW['postgres'],'volume':'docker-lab_pgdata_alpine_v1','lab_notes_before':len(original),'lab_notes_after':len(final),'probe_notes_written_and_removed':2,'backup_sha256':hashlib.sha256(dump).hexdigest(),'backup_content_published':False,'rollback_includes_post_cutover_write':True,'duration_seconds':round(time.time()-started,1),'scope':'Local docker-lab Compose project. Same PostgreSQL 17.11/Alpine 3.24 base, so the image swap reuses the adopted volume; only gosu changed.'})
def api_otel():
 # Traces have no collector in this project; exporters are off so the test measures the API itself.
 env={'OTEL_TRACES_EXPORTER':'none','OTEL_METRICS_EXPORTER':'none','OTEL_LOGS_EXPORTER':'none','OTEL_SERVICE_NAME':'notes-api-readopt'}
 new=variant('otel-new',NEW['postgres'],NEW['notes-api-otel'],env);old=variant('otel-old',NEW['postgres'],OLD['notes-api-otel'],env);base=variant('otel-base',NEW['postgres'],BASIC_API);checks=[];started=time.time()
 compose(old,'up','-d','--no-build','db','api');healthy(old);ready()
 assert running_image('api')==OLD['notes-api-otel'] and certifi(old)=='2026.7.22';checks.append('API starts on the previously adopted OpenTelemetry image with certifi 2026.7.22')
 compose(new,'up','-d','--no-build','api');ready()
 assert running_image('api')==NEW['notes-api-otel'] and certifi(new)=='2026.10.18';checks.append('Patched OpenTelemetry image serves the API with certifi 2026.10.18')
 post=api('/notes',{'title':'readopt-otel-'+uuid.uuid4().hex[:8]},'POST')['id'];api(f'/notes/{post}',method='DELETE');kept=api('/notes',{'title':'readopt-otel-kept-'+uuid.uuid4().hex[:8]},'POST')['id'];checks.append('Create, list and delete work on the patched image')
 compose(old,'up','-d','--no-build','api');ready()
 assert running_image('api')==OLD['notes-api-otel'] and any(n['id']==kept for n in api()['notes']);checks.append('Real rollback to the previous image reads the note written on the patched image')
 compose(new,'up','-d','--no-build','api');ready()
 assert running_image('api')==NEW['notes-api-otel'] and any(n['id']==kept for n in api()['notes']);checks.append('Return to the patched image keeps the same data')
 api(f'/notes/{kept}',method='DELETE')
 compose(base,'up','-d','--no-build','api');ready();assert running_image('api')==BASIC_API;checks.append('docker-lab is back on its default basic Alpine API')
 proof('notes-api-otel',checks,{'previous_image':OLD['notes-api-otel'],'patched_image':NEW['notes-api-otel'],'duration_seconds':round(time.time()-started,1),'scope':'Stateless API image swap in the local docker-lab Compose project, OTLP exporters disabled. The Kubernetes tracing path is validated by the tracing-lab CI.'})
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('stage',choices=['postgres','notes-api-otel']);args=parser.parse_args()
 assert NEW['postgres']!=OLD['postgres'] and NEW['notes-api-otel']!=OLD['notes-api-otel'],'Update config/targets.json with the patched digests first'
 {'postgres':postgres,'notes-api-otel':api_otel}[args.stage]()
