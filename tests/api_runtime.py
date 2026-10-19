#!/usr/bin/env python3
"""Benign runtime checks for the two existing API labs; never stress memory."""
import json,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];WORKSPACE=ROOT.parent
probe=r'''
import errno,json,os,pathlib,subprocess,tempfile,uuid,urllib.request,urllib.error
checks=[]
def check(name,ok):
 if not ok:raise AssertionError(name)
 checks.append(name)
status=dict(line.split(':',1) for line in pathlib.Path('/proc/self/status').read_text().splitlines() if ':' in line)
check('API process runs as UID/GID 10001',os.getuid()==10001 and os.getgid()==10001)
check('Effective capabilities are empty',int(status['CapEff'].strip(),16)==0)
check('Privilege gains are disabled',status['NoNewPrivs'].strip()=='1')
check('Seccomp filtering is active',status['Seccomp'].strip()=='2')
p=pathlib.Path('/app')/('.security-probe-'+uuid.uuid4().hex)
try:p.write_text('probe')
except OSError as e:check('Application root is read-only',e.errno==errno.EROFS)
else:p.unlink();raise AssertionError('Writable application root')
with tempfile.TemporaryDirectory(prefix='security-probe-') as folder:
 attempt=subprocess.run(['mount','-t','tmpfs','security-probe',folder],capture_output=True,text=True)
 if attempt.returncode==0:subprocess.run(['umount',folder],check=True)
 check('Benign mount attempt is denied',attempt.returncode!=0 and ('permission denied' in attempt.stderr.lower() or 'must be superuser' in attempt.stderr.lower()))
attempt=subprocess.run(['nsenter','--mount=/proc/self/ns/mnt','true'],capture_output=True,text=True)
check('Namespace entry is denied',attempt.returncode!=0 and 'not permitted' in attempt.stderr.lower())
check('systemd-homed binary is absent',not any(pathlib.Path(p).exists() for p in ['/usr/lib/systemd/systemd-homed','/lib/systemd/systemd-homed']))
perl=subprocess.run(['perl','-MArchive::Tar','-e','print $Archive::Tar::VERSION'],capture_output=True,text=True)
check('Archive::Tar is not importable',perl.returncode!=0 and "Can't locate Archive/Tar.pm" in perl.stderr)
check('No Kubernetes service account token is mounted',not pathlib.Path('/var/run/secrets/kubernetes.io/serviceaccount/token').exists())
request=urllib.request.Request('http://127.0.0.1:8000/notes',data=json.dumps({'title':'x'*5000}).encode(),headers={'Content-Type':'application/json'})
try:urllib.request.urlopen(request,timeout=8);raise AssertionError('Oversized request accepted')
except urllib.error.HTTPError as e:check('Oversized request is rejected before SQL processing',e.code==413)
limits={n:pathlib.Path('/sys/fs/cgroup/'+n).read_text().strip() for n in ['memory.max','cpu.max','pids.max']}
check('Cgroup memory limit is 256 MiB',limits['memory.max']=='268435456')
quota,period=limits['cpu.max'].split();check('Cgroup CPU quota is at most one core',quota!='max' and int(quota)<=int(period))
try:maps=pathlib.Path('/proc/1/maps').read_text();libs=sorted(set(pathlib.Path(line.split()[-1]).name for line in maps.splitlines() if '/' in line and '.so' in line))
except PermissionError:libs=['unavailable']
tmp_mount=next((line.split()[5].split(',') for line in pathlib.Path('/proc/self/mountinfo').read_text().splitlines() if line.split()[4]=='/tmp'),[])
stat=os.statvfs('/tmp');tmp_bytes=stat.f_frsize*stat.f_blocks
helptext=subprocess.run(['nsenter','--help'],capture_output=True,text=True).stdout
print(json.dumps({'checks_passed':len(checks),'checks':checks,'cgroup_limits':limits,'kernel':os.uname().release,'tmp_mount_options':tmp_mount,'tmp_filesystem_bytes':tmp_bytes,'infocmp_present':pathlib.Path('/usr/bin/infocmp').exists(),'mount_setuid_bit_present':bool(pathlib.Path('/usr/bin/mount').stat().st_mode&0o4000),'nsenter_join_cgroup_option_present':'--join-cgroup' in helptext,'observed_pid1_shared_libraries':libs,'scope':'Benign control tests and component inspection; no CVE exploit, untrusted terminfo or memory-exhaustion payload.'}))
'''
results={}
for name,command in [('docker',['bash',str(WORKSPACE/'docker-lab/scripts/compose.sh'),'exec','-T','api','python','-c',probe]),('kubernetes',['bash',str(WORKSPACE/'kubernetes-lab/scripts/k.sh'),'exec','deployment/notes-api','--','python','-c',probe])]:
 results[name]=json.loads(subprocess.check_output(command,text=True))
 if name=='docker':
  assert results[name]['cgroup_limits']['pids.max']=='128'
  assert {'noexec','nosuid','nodev'}<=set(results[name]['tmp_mount_options'])
  assert results[name]['tmp_filesystem_bytes']==64*1024*1024
  results[name]['checks']+=['Docker API PID limit is 128','Docker tmpfs enforces noexec/nosuid/nodev','Docker tmpfs capacity is 64 MiB']
  results[name]['checks_passed']+=3
results['verified_at_utc']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
(ROOT/'.local/api-high-review').mkdir(parents=True,exist_ok=True)
(ROOT/'.local/api-high-review/runtime-checks.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2))
