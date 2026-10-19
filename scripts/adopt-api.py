#!/usr/bin/env python3
"""API-only adoption and actual image rollback on the sibling live labs."""
import json,os,subprocess,time,urllib.request,urllib.error,uuid,hashlib,argparse
from pathlib import Path
os.umask(0o077)
ROOT=Path(__file__).resolve().parents[2];PRIVATE=ROOT/'security-lab/.local/api-adoption';PUBLIC=ROOT/'security-lab/evidence/api-adoption'
BASIC='ghcr.io/tommmdl/docker-lab@sha256:ae2e93fdbab7bc912897e6524b3e17b982e97cfb29bcb4fc36d9c014d615eb91'
TRACED='ghcr.io/tommmdl/docker-lab@sha256:e01c467c0987cc2d999778a4e9ee429bee1d6af4bcdef80e38ce620b95a0b8da'
DEBIAN='ghcr.io/tommmdl/docker-lab@sha256:343f2b23294c09bea9c3250a3b3fd1f95d817acea9db0231dfaaaf406f22fbac'
ROWS="SELECT coalesce(json_agg(n ORDER BY id),'[]'::json) FROM (SELECT id,title,created_at FROM notes) n"
SCHEMA="SELECT column_name,data_type,is_nullable,is_identity FROM information_schema.columns WHERE table_schema='public' AND table_name='notes' ORDER BY ordinal_position"
INDEXES="SELECT indexdef FROM pg_indexes WHERE schemaname='public' AND tablename='notes' ORDER BY indexname"
def run(a,data=None):return subprocess.check_output(a,input=data)
def write(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,indent=2)+'\n')
def k(*a,data=None):return run(['bash',str(ROOT/'kubernetes-lab/scripts/k.sh'),*a],data)
def obj(*a):return json.loads(k('get',*a,'-o','json'))
def compose(file,*a,data=None):return run(['bash',str(ROOT/'docker-lab/scripts/compose.sh'),'-p','docker-lab','-f',str(file),*a],data)
def sql(kind,query,db='notes'):
 args=['psql','-U','notes_admin','-d',db,'-Atc',query]
 return (compose(PRIVATE/'docker-target.json','exec','-T','db',*args) if kind=='docker' else k('exec','postgres-alpine-0','--',*args)).decode().strip()
def dbcmd(kind,*a,data=None):
 return compose(PRIVATE/'docker-target.json','exec','-T','db',*a,data=data) if kind=='docker' else k('exec','-i','postgres-alpine-0','--',*a,data=data)
def call(port,path='/notes',body=None,method=None):
 request=urllib.request.Request('http://127.0.0.1:'+str(port)+path,data=None if body is None else json.dumps(body).encode(),method=method,headers={'Content-Type':'application/json'})
 attempts=4 if body is None and method in [None,'GET'] else 1
 for attempt in range(attempts):
  try:
   with urllib.request.urlopen(request,timeout=10) as response:return json.load(response) if response.status!=204 else None
  except urllib.error.HTTPError as error:
   if error.code not in [502,503,504] or attempt==attempts-1:raise
  except (TimeoutError,urllib.error.URLError,ConnectionError):
   if attempt==attempts-1:raise
  time.sleep(1)
def ready(port):
 for _ in range(120):
  try:
   if call(port,'/readyz')['status']=='ready':return
  except (OSError,ValueError):pass
  time.sleep(1)
 raise AssertionError('API readiness timeout')
def baseline(kind):
 assert not (PRIVATE/(kind+'-before.dump')).exists(),'Backup already exists: preserve it and recover the interrupted stage rather than repeating writes'
 backup=dbcmd(kind,'pg_dump','-U','notes_admin','-d','notes','-Fc','--no-owner','--no-acl');(PRIVATE/(kind+'-before.dump')).write_bytes(backup)
 rows=json.loads(sql(kind,ROWS));write(PRIVATE/(kind+'-before-rows.json'),rows)
 schema=sql(kind,SCHEMA);indexes=sql(kind,INDEXES);sequence=sql(kind,'SELECT last_value,is_called FROM notes_id_seq')
 name='api_backup_check_'+uuid.uuid4().hex[:10]
 dbcmd(kind,'createdb','-U','notes_admin','-O','lab',name)
 try:
  dbcmd(kind,'pg_restore','-U','lab','-d',name,'--no-owner','--no-acl','--exit-on-error','--single-transaction',data=backup)
  assert json.loads(sql(kind,ROWS,name))==rows and sql(kind,SCHEMA,name)==schema and sql(kind,INDEXES,name)==indexes and sql(kind,'SELECT last_value,is_called FROM notes_id_seq',name)==sequence
 finally:dbcmd(kind,'dropdb','-U','notes_admin',name)
 data={'rows':rows,'schema':schema,'indexes':indexes,'sequence':sequence,'backup_sha256':hashlib.sha256(backup).hexdigest()}
 write(PRIVATE/(kind+'-baseline.json'),data);return data
def preserved(kind,before):
 current={n['id']:n for n in json.loads(sql(kind,ROWS))};assert all(current.get(n['id'])==n for n in before['rows'])
 assert sql(kind,SCHEMA)==before['schema'] and sql(kind,INDEXES)==before['indexes']
 assert int(sql(kind,'SELECT last_value FROM notes_id_seq'))>=int(before['sequence'].split('|')[0])
def check_note(port,n):assert next(x for x in call(port)['notes'] if x['id']==n['id'])==n
def report(kind,before,checks,extra):
 write(PUBLIC/(kind+'.json'),{'executed_at_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'checks_passed':len(checks),'checks':checks,'source_rows':len(before['rows']),'backup_sha256':before['backup_sha256'],'backup_restore_verified':True,'all_original_note_fields_preserved':True,'schema_and_indexes_unchanged':True,'identity_sequence_not_rewound':True,'database_image_and_volume_unchanged':True,**extra,'scope':'API image changes only; actual rollback serves a post-cutover note from the same database. Private logical backups restored separately as a recovery check; never restored over live notes.'})
def docker():
 source=PRIVATE/'docker-source.json';assert source.exists(),'Capture source configuration first'
 target=PRIVATE/'docker-target.json';write(target,json.loads(run(['bash',str(ROOT/'docker-lab/scripts/compose.sh'),'config','--format','json'])))
 current=json.loads(run(['docker','inspect','docker-lab-api-1']))[0];assert current['Config']['Image']!=BASIC,'Already adopted; do not repeat the one-time rehearsal'
 olddb=json.loads(run(['docker','inspect','docker-lab-db-1']))[0];compose(source,'stop','api');before=baseline('docker');checks=['Logical backup restored in a separate check database with identical rows, schema, indexes and sequence']
 compose(target,'up','-d','--no-build','--no-deps','--wait','--wait-timeout','180','api');ready(8000);preserved('docker',before);checks.append('Alpine basic API serves the existing database without replacing its container or volume')
 note=call(8000,body={'title':'Rollback da API — café 🚀 '+uuid.uuid4().hex});write(PRIVATE/'docker-probe.json',note)
 try:
  compose(source,'up','-d','--no-build','--no-deps','--wait','--wait-timeout','180','api');ready(8000);check_note(8000,note);preserved('docker',before);checks.append('Actual Debian image rollback preserves every field of the note written after Alpine cutover')
  assert json.loads(run(['docker','inspect','docker-lab-api-1']))[0]['Config']['Image']==DEBIAN
  compose(target,'up','-d','--no-build','--no-deps','--wait','--wait-timeout','180','api');ready(8000);check_note(8000,note);checks.append('Return to the adopted Alpine digest still serves the same post-cutover note')
 finally:
  if json.loads(run(['docker','inspect','docker-lab-api-1']))[0]['Config']['Image']==BASIC:call(8000,'/notes/'+str(note['id']),method='DELETE')
 after=json.loads(run(['docker','inspect','docker-lab-db-1']))[0];assert after['Id']==olddb['Id'] and after['Mounts']==olddb['Mounts'] and after['Image']==olddb['Image'];preserved('docker',before);checks.append('Database container identity, image and mounts remain identical; original data/schema and sequence remain valid')
 report('docker',before,checks,{'source_image':DEBIAN,'active_image':BASIC,'rollback_note_removed':True});print('Docker adoption and actual rollback passed',flush=True)
def switch(image,policy):
 patch={'spec':{'template':{'spec':{'containers':[{'name':'api','image':image,'imagePullPolicy':policy}]}}}}
 k('patch','deployment','notes-api','--type=strategic','-p',json.dumps(patch));k('rollout','status','deployment/notes-api','--timeout=240s');ready(8005)
 assert obj('deployment','notes-api')['spec']['template']['spec']['containers'][0]['image']==image
 assert obj('deployment','notes-api')['status'].get('availableReplicas')==2

def trace_test(name,image):
 folder=PRIVATE/name;folder.mkdir(exist_ok=True)
 env=dict(os.environ,TRACING_APP_IMAGE=image,TRACING_EVIDENCE_DIR=str(folder))
 with (folder/'test.log').open('w') as output:subprocess.run(['python3',str(ROOT/'tracing-lab/tests/verify.py')],env=env,stdout=output,stderr=subprocess.STDOUT,check=True)
 data=json.loads((folder/'verification.json').read_text());assert data['checks_passed']==19;write(PUBLIC/(name+'.json'),data)
def kubernetes():
 source=json.loads((PRIVATE/'kubernetes-source-deployment.json').read_text());old=source['spec']['template']['spec']['containers'][0]['image'];assert obj('deployment','notes-api')['spec']['template']['spec']['containers'][0]['image']==old and old!=TRACED,'Source image changed or already adopted'
 app=obj('application','notes','-n','argocd');assert app.get('status',{}).get('operationState',{}).get('phase')!='Running'
 k('patch','application','notes','-n','argocd','--type=merge','-p','{"spec":{"syncPolicy":{"automated":null}}}')
 db=obj('statefulset','postgres-alpine');pvc=obj('pvc','data-postgres-alpine-0')['metadata']['uid']
 k('scale','deployment/notes-api','--replicas=0');k('wait','--for=delete','pod','-l','app=notes-api','--timeout=120s')
 before=baseline('kubernetes');k('scale','deployment/notes-api','--replicas=2');k('rollout','status','deployment/notes-api','--timeout=180s');ready(8005);checks=['Logical backup restored in a separate check database with identical rows, schema, indexes and sequence']
 switch(BASIC,'IfNotPresent');note=call(8005,body={'title':'Rollback básico — 日本語 🚀 '+uuid.uuid4().hex});write(PRIVATE/'kubernetes-basic-probe.json',note)
 switch(DEBIAN,'IfNotPresent');check_note(8005,note);preserved('kubernetes',before);checks.append('Basic Kubernetes API rollback to Debian serves the note written by Alpine')
 switch(BASIC,'IfNotPresent');check_note(8005,note);call(8005,'/notes/'+str(note['id']),method='DELETE');checks.append('Basic API returns to Alpine without database changes')
 switch(TRACED,'IfNotPresent');note=call(8005,body={'title':'Rollback instrumentado — café 🚀 '+uuid.uuid4().hex});write(PRIVATE/'kubernetes-traced-probe.json',note)
 switch(old,'Never' if old.startswith('tracing-lab-api:') else 'IfNotPresent');check_note(8005,note);trace_test('tracing-rollback',old);preserved('kubernetes',before);checks.append('Actual original OpenTelemetry image rollback preserves the post-cutover note and passes all 19 tracing checks')
 switch(TRACED,'IfNotPresent');check_note(8005,note);call(8005,'/notes/'+str(note['id']),method='DELETE');trace_test('tracing-adopted',TRACED);checks.append('Adopted published OpenTelemetry image passes all 19 tracing checks after rollback and return')
 preserved('kubernetes',before);assert obj('pvc','data-postgres-alpine-0')['metadata']['uid']==pvc and obj('statefulset','postgres-alpine')['spec']['template']['spec']['containers'][0]['image']==db['spec']['template']['spec']['containers'][0]['image'];checks.append('Original PostgreSQL image/PVC and all original note fields, schema and indexes remain unchanged')
 report('kubernetes',before,checks,{'basic_image':BASIC,'active_image':TRACED,'original_traced_image':old,'pvc_uid_preserved':True,'rollback_notes_removed':True,'argocd_automation':'Paused until new Git manifests are published'})
 print('Kubernetes basic/traced adoption and actual rollbacks passed; publish Git before restoring Argo automation',flush=True)
def snapshot():
 assert not (PRIVATE/'docker-source.json').exists(),'Keep the existing recovery snapshots; do not overwrite them'
 cfg=json.loads(run(['bash',str(ROOT/'docker-lab/scripts/compose.sh'),'config','--format','json']))
 current=json.loads(run(['docker','inspect','docker-lab-api-1']))[0]
 assert current['Config']['Image']!=BASIC,'Already adopted'
 cfg['services']['api']['image']=DEBIAN;write(PRIVATE/'docker-source.json',cfg)
 for kind,name in [('deployment','notes-api'),('statefulset','postgres-alpine'),('pvc','data-postgres-alpine-0'),('application','notes')]:
  extra=['-n','argocd'] if kind=='application' else []
  write(PRIVATE/('kubernetes-source-'+kind+'.json'),obj(kind,name,*extra))
 write(PRIVATE/'docker-db-inspect.json',json.loads(run(['docker','inspect','docker-lab-db-1'])))
 write(PRIVATE/'docker-api-inspect.json',[current])
 print('Private source snapshots captured; execute each adoption stage separately')
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('stage',choices=['snapshot','docker','kubernetes']);args=parser.parse_args()
 PRIVATE.mkdir(exist_ok=True);PUBLIC.mkdir(exist_ok=True);{'snapshot':snapshot,'docker':docker,'kubernetes':kubernetes}[args.stage]()
