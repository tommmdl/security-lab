"""One-time controlled adoption. All dumps and row contents stay private."""
import json,os,subprocess,time,urllib.request,uuid,hashlib
os.umask(0o077)
from pathlib import Path
ROOT=Path.cwd();PRIVATE=ROOT/'security-lab/.local/postgres-adoption';PUBLIC=ROOT/'security-lab/evidence/postgres-adoption';PUBLIC.mkdir(exist_ok=True)
ALPINE='ghcr.io/tommmdl/docker-lab@sha256:8b6813ec76804698c33e4dac8f501ca8f641affcbd27cbc3b7dd6fdb02874fc3'
DEBIAN='ghcr.io/tommmdl/docker-lab@sha256:be42c09595d7059956490eeab607b742afc96268db48f91f4eb1fd53edc89b52'
QUERY="SELECT coalesce(json_agg(n ORDER BY id),'[]'::json) FROM (SELECT id,title,created_at FROM notes) n"
def run(args,data=None):return subprocess.check_output(args,input=data)
def write(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
def api(port,path='/notes',body=None,method=None):
 req=urllib.request.Request(f'http://127.0.0.1:{port}'+path,data=None if body is None else json.dumps(body).encode(),method=method,headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=10) as r:return json.load(r) if r.status!=204 else None
def ready(port):
 for _ in range(120):
  try:
   if api(port,'/readyz')['status']=='ready':return
  except Exception:pass
  time.sleep(1)
 raise RuntimeError('API not ready')
def compose(file,*args,data=None):return run(['bash',str(ROOT/'docker-lab/scripts/compose.sh'),'-p','docker-lab','-f',str(file),*args],data)
def docker_sql(file,q):return compose(file,'exec','-T','db','psql','-U','notes_admin','-d','notes','-Atc',q).decode().strip()
def docker_dump(file):return compose(file,'exec','-T','db','pg_dump','-U','notes_admin','-d','notes','-Fc','--no-owner','--no-acl')
def docker_restore(file,d):compose(file,'exec','-T','db','pg_restore','-U','lab','-d','notes','--no-owner','--no-acl','--exit-on-error','--single-transaction',data=d)
def k(*args,data=None):return run(['bash',str(ROOT/'kubernetes-lab/scripts/k.sh'),*args],data)
def obj(*args):return json.loads(k('get',*args,'-o','json'))
def ksql(pod,q):return k('exec',pod,'--','psql','-U','notes_admin','-d','notes','-Atc',q).decode().strip()
def kdump(pod):return k('exec',pod,'--','pg_dump','-U','notes_admin','-d','notes','-Fc','--no-owner','--no-acl')
def krestore(pod,d):return k('exec','-i',pod,'--','pg_restore','-U','lab','-d','notes','--no-owner','--no-acl','--exit-on-error','--single-transaction',data=d)
def apply(d):return k('apply','-f','-',data=json.dumps(d).encode())
def clean(d):
 d=json.loads(json.dumps(d));d.pop('status',None)
 d['metadata']={a:b for a,b in d['metadata'].items() if a in ['name','namespace','labels','annotations']};d['metadata'].get('annotations',{}).pop('kubectl.kubernetes.io/last-applied-configuration',None);return d
def endpoint(label):k('patch','service','postgres','--type=merge','-p',json.dumps({'spec':{'selector':{'app':label}}}))
def scaleapi(n):
 k('scale','deployment/notes-api','--replicas='+str(n))
 if n:k('rollout','status','deployment/notes-api','--timeout=180s');ready(8005)
 else:k('wait','--for=delete','pod','-l','app=notes-api','--timeout=120s')
def proof(name,checks,backup,original_count):
 result={'verified_at_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'source_image':DEBIAN,'target_image':ALPINE,'source_rows':original_count,'checks_passed':len(checks),'checks':checks,'backup_sha256':hashlib.sha256(backup).hexdigest(),'backup_content_published':False,'rollback_includes_post_cutover_write':True,'original_volume_retained':True,'scope':'Local notes schema; writes paused for each dump/cutover. Fresh restore volumes, no physical PGDATA reuse.'}
 write(PUBLIC/(name+'.json'),result);print(json.dumps(result,indent=2),flush=True)
def docker():
 source=PRIVATE/'docker-source-compose.json';target=PRIVATE/'docker-target-compose.json';rollback=PRIVATE/'docker-rollback-compose.json'
 s=json.loads(source.read_text());s['services']['db']['image']=DEBIAN;write(source,s)
 t=json.loads(run(['bash',str(ROOT/'docker-lab/scripts/compose.sh'),'config','--format','json']));write(target,t)
 assert s['volumes']['pgdata']['name']!=t['volumes']['pgdata']['name']
 assert not subprocess.run(['docker','volume','inspect',t['volumes']['pgdata']['name']],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0,'Target volume already exists; refusing overwrite'
 assert t['services']['db']['image']==ALPINE
 current=json.loads(run(['docker','inspect','docker-lab-db-1']))[0]
 assert any(m.get('Name')==s['volumes']['pgdata']['name'] for m in current['Mounts']),'Source volume is no longer active; refusing to repeat migration'
 checks=[]
 compose(source,'stop','api');rows=docker_sql(source,QUERY);seq=docker_sql(source,'SELECT last_value,is_called FROM notes_id_seq');write(PRIVATE/'docker-before-rows.json',json.loads(rows));backup=docker_dump(source);(PRIVATE/'docker-before.dump').write_bytes(backup)
 compose(source,'stop','db');compose(target,'up','-d','--no-build','--wait','--wait-timeout','180','db');docker_restore(target,backup)
 assert docker_sql(target,QUERY)==rows and docker_sql(target,'SELECT last_value,is_called FROM notes_id_seq')==seq;checks.append('Final source dump restores all note fields and identity sequence into a different Alpine volume')
 compose(target,'up','-d','--no-build','--wait','--wait-timeout','180');ready(8000)
 probe=api(8000,body={'title':'Migração com rollback — Docker '+uuid.uuid4().hex})
 compose(target,'stop','api');after=docker_sql(target,QUERY);afterseq=docker_sql(target,'SELECT last_value,is_called FROM notes_id_seq');reverse=docker_dump(target);(PRIVATE/'docker-reverse.dump').write_bytes(reverse)
 rb=json.loads(source.read_text());rb['volumes']['pgdata']['name']='docker-lab_pgdata_rollback_'+uuid.uuid4().hex[:8];write(rollback,rb)
 compose(target,'stop','db');compose(rollback,'up','-d','--no-build','--wait','--wait-timeout','180','db');docker_restore(rollback,reverse)
 assert docker_sql(rollback,QUERY)==after and docker_sql(rollback,'SELECT last_value,is_called FROM notes_id_seq')==afterseq;checks.append('Reverse dump restores every row and current sequence in a fresh Debian volume')
 compose(rollback,'up','-d','--no-build','--wait','--wait-timeout','180');ready(8000);assert any(n['id']==probe['id'] for n in api(8000)['notes']);checks.append('Actual API rollback serves the note written after Alpine cutover')
 compose(rollback,'stop','api','db');compose(target,'up','-d','--no-build','--wait','--wait-timeout','180');ready(8000);api(8000,'/notes/'+str(probe['id']),method='DELETE')
 assert docker_sql(target,QUERY)==rows;checks.append('Return to Alpine preserves original notes; only the controlled rollback probe is removed')
 cid=compose(target,'ps','-q','db').decode().strip();d=json.loads(run(['docker','inspect',cid]))[0];assert d['Config']['Image']==ALPINE
 checks.append('Running database uses the tested immutable Alpine image')
 compose(target,'up','-d','--no-build','--force-recreate','--wait','--wait-timeout','180','db');ready(8000);assert docker_sql(target,QUERY)==rows;checks.append('Original notes survive database container replacement')
 assert subprocess.run(['docker','volume','inspect',s['volumes']['pgdata']['name']],stdout=subprocess.DEVNULL).returncode==0;checks.append('Original Debian volume and a restored rollback volume remain retained')
 write(PRIVATE/'docker-state.json',{'source_config':str(source),'target_config':str(target),'rollback_config':str(rollback),'source_volume':s['volumes']['pgdata']['name'],'target_volume':t['volumes']['pgdata']['name'],'rollback_volume':rb['volumes']['pgdata']['name'],'active':'alpine','probe_id':probe['id']})
 proof('docker',checks,backup,len(json.loads(rows)))
def kubernetes():
 assert obj('service','postgres')['spec']['selector']=={'app':'notes-db'},'Source is no longer active'
 assert subprocess.run(['bash',str(ROOT/'kubernetes-lab/scripts/k.sh'),'get','pvc','data-postgres-alpine-0'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode!=0,'Target PVC already exists'
 checks=[];app=json.loads((PRIVATE/'argocd-before.json').read_text());assert app['spec']['syncPolicy']['automated']['selfHeal']
 k('patch','application','notes','-n','argocd','--type=merge','-p','{"spec":{"syncPolicy":{"automated":null}}}')
 # Let any in-flight synchronization complete before maintenance.
 current=obj('application','notes','-n','argocd');assert current.get('status',{}).get('operationState',{}).get('phase')!='Running'
 old=obj('statefulset','postgres');oldpvc=obj('pvc','data-postgres-0')['metadata']['uid']
 scaleapi(0);rows=ksql('postgres-0',QUERY);seq=ksql('postgres-0','SELECT last_value,is_called FROM notes_id_seq');write(PRIVATE/'kubernetes-before-rows.json',json.loads(rows));backup=kdump('postgres-0');(PRIVATE/'kubernetes-before.dump').write_bytes(backup)
 # Render with kubectl locally; apply only the new StatefulSet before changing routing.
 raw=k('create','--dry-run=client','-f',str(ROOT/'kubernetes-lab/manifests/postgres.yaml'),'-o','json').decode().strip()
 items=[]
 while raw:
  item,end=json.JSONDecoder().raw_decode(raw);items.append(item);raw=raw[end:].strip()
 rendered={'items':items}
 target=next(i for i in rendered['items'] if i['kind']=='StatefulSet' and i['metadata']['name']=='postgres-alpine')
 assert subprocess.run(['bash',str(ROOT/'kubernetes-lab/scripts/k.sh'),'get','pvc','data-postgres-alpine-0'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode!=0,'Target PVC exists; refusing overwrite'
 apply(target);k('rollout','status','statefulset/postgres-alpine','--timeout=240s');krestore('postgres-alpine-0',backup)
 assert ksql('postgres-alpine-0',QUERY)==rows and ksql('postgres-alpine-0','SELECT last_value,is_called FROM notes_id_seq')==seq;checks.append('Final source dump restores all note fields and sequence into a new Alpine PVC')
 endpoint('notes-db-alpine');scaleapi(2)
 probe=api(8005,body={'title':'Migração com rollback — Kubernetes '+uuid.uuid4().hex})
 scaleapi(0);after=ksql('postgres-alpine-0',QUERY);afterseq=ksql('postgres-alpine-0','SELECT last_value,is_called FROM notes_id_seq');reverse=kdump('postgres-alpine-0');(PRIVATE/'kubernetes-reverse.dump').write_bytes(reverse)
 rb=clean(old);rb['metadata'].get('annotations',{}).pop('argocd.argoproj.io/tracking-id',None);rb['metadata'].get('labels',{}).pop('app.kubernetes.io/instance',None);name='postgres-rollback-'+uuid.uuid4().hex[:8];rb['metadata']['name']=name;rb['spec']['selector']['matchLabels']={'app':name};rb['spec']['template']['metadata']['labels']={'app':name};rb['spec']['replicas']=1
 apply(rb);pod=name+'-0';k('rollout','status','statefulset/'+name,'--timeout=240s');krestore(pod,reverse)
 assert ksql(pod,QUERY)==after and ksql(pod,'SELECT last_value,is_called FROM notes_id_seq')==afterseq;checks.append('Reverse dump restores all rows and current sequence into a fresh Debian rollback PVC')
 endpoint(name);scaleapi(2);assert any(n['id']==probe['id'] for n in api(8005)['notes']);checks.append('Actual Kubernetes Service rollback serves the note created after Alpine cutover')
 scaleapi(0);endpoint('notes-db-alpine');scaleapi(2);api(8005,'/notes/'+str(probe['id']),method='DELETE');assert ksql('postgres-alpine-0',QUERY)==rows;checks.append('Return to Alpine preserves original notes; only the controlled probe is removed')
 k('scale','statefulset/postgres','--replicas=0');k('scale','statefulset/'+name,'--replicas=0')
 newpvc=obj('pvc','data-postgres-alpine-0')['metadata']['uid'];assert newpvc!=oldpvc and obj('pvc','data-postgres-0')['metadata']['uid']==oldpvc;checks.append('Active Alpine PVC is separate and original Debian PVC retains its identity')
 olduid=obj('pod','postgres-alpine-0')['metadata']['uid'];k('delete','pod','postgres-alpine-0','--wait=true');k('rollout','status','statefulset/postgres-alpine','--timeout=240s');ready(8005);assert ksql('postgres-alpine-0',QUERY)==rows and obj('pod','postgres-alpine-0')['metadata']['uid']!=olduid;checks.append('Notes survive Alpine database Pod replacement')
 assert k('exec','postgres-alpine-0','--','id','-u').decode().strip()=='70';checks.append('Database runs as non-root UID 70 with the existing restricted security context')
 write(PRIVATE/'kubernetes-state.json',{'active_statefulset':'postgres-alpine','source_pvc':'data-postgres-0','source_pvc_uid':oldpvc,'target_pvc':'data-postgres-alpine-0','target_pvc_uid':newpvc,'rollback_statefulset':name,'rollback_pvc':'data-'+name+'-0','probe_id':probe['id'],'argocd_automation':'paused until committed manifests are deployed'})
 proof('kubernetes',checks,backup,len(json.loads(rows)))
def snapshot():
 PRIVATE.mkdir(parents=True,exist_ok=True)
 assert not (PRIVATE/'docker-source-compose.json').exists(),'Snapshot already exists; keep original recovery files'
 current=json.loads(run(['docker','inspect','docker-lab-db-1']))[0]
 volume=next(m['Name'] for m in current['Mounts'] if m['Destination']=='/var/lib/postgresql/data')
 assert volume=='docker-lab_pgdata','Expected original Debian volume'
 cfg=json.loads(run(['bash',str(ROOT/'docker-lab/scripts/compose.sh'),'config','--format','json']))
 cfg['services']['db']['image']=DEBIAN
 cfg['services']['db']['environment']['POSTGRES_INITDB_ARGS']='--encoding=UTF8 --locale=en_US.utf8'
 cfg['volumes']['pgdata']['name']=volume
 write(PRIVATE/'docker-source-compose.json',cfg)
 for kind,name in [('statefulset','postgres'),('service','postgres'),('deployment','notes-api')]:
  write(PRIVATE/('kubernetes-source-'+kind+'.json'),obj(kind,name))
 write(PRIVATE/'argocd-before.json',obj('application','notes','-n','argocd'))
 print('Private source snapshots saved. Run docker and kubernetes stages separately.')
if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser(description='One-time adoption for the sibling docker-lab and Argo-managed kubernetes-lab checkouts. See docs/postgres-adoption.md; not a generic cluster migration tool.')
 parser.add_argument('stage',choices=['snapshot','docker','kubernetes'])
 args=parser.parse_args()
 for folder in ['docker-lab','kubernetes-lab','security-lab']:
  assert (ROOT/folder).is_dir(),'Run from the parent directory containing the portfolio checkouts'
 {'snapshot':snapshot,'docker':docker,'kubernetes':kubernetes}[args.stage]()
