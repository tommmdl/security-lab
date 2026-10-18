#!/usr/bin/env python3
"""Exercise policy decisions and actual Trivy Dockerfile checks."""
import copy,json,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
local=ROOT/'.local/tests';local.mkdir(parents=True,exist_ok=True)
checks=[]
def check(label,value):
    assert value,label
    checks.append(label);print('OK:',label,flush=True)
base={'SchemaVersion':2,'ArtifactName':'synthetic-policy-fixture','ArtifactType':'container_image','Metadata':{'OS':{'Family':'debian','EOSL':False}},'Results':[{'Target':'fixture','Class':'os-pkgs','Packages':[{'Name':'demo','Version':'1.0'}],'Vulnerabilities':[]}]}
def run(report):
    path=local/'policy-input.json';path.write_text(json.dumps(report))
    return subprocess.run([sys.executable,str(ROOT/'scripts/gate.py'),str(path)],capture_output=True,text=True).returncode
def finding(severity,fixed='2.0'):
    report=copy.deepcopy(base)
    report['Results'][0]['Vulnerabilities']=[{'VulnerabilityID':'LAB-EXAMPLE-001','PkgName':'demo','InstalledVersion':'1.0','FixedVersion':fixed,'Severity':severity}]
    return report
check('Valid image report without findings is allowed',run(base)==0)
check('Medium findings remain reported without blocking',run(finding('MEDIUM'))==0)
check('High finding with a fix blocks',run(finding('HIGH'))==1)
check('High finding without a fix also blocks',run(finding('HIGH',''))==1)
check('Critical finding blocks',run(finding('CRITICAL'))==1)
eol=copy.deepcopy(base);eol['Metadata']['OS']['EOSL']=True
check('End-of-life operating system blocks',run(eol)==1)
empty=copy.deepcopy(base);empty['Results']=[]
check('Missing scan results are an error rather than approval',run(empty)==2)
missing=copy.deepcopy(base);missing['Results'][0]['Packages']=[]
check('Missing package inventory is an error',run(missing)==2)
check('Unexpected severity is an error',run(finding('SUPER_HIGH'))==2)
invalid=local/'invalid.json';invalid.write_text('{not-json')
check('Malformed report exits with error code 2',subprocess.run([sys.executable,str(ROOT/'scripts/gate.py'),str(invalid)],capture_output=True).returncode==2)
check('Missing report exits with error code 2',subprocess.run([sys.executable,str(ROOT/'scripts/gate.py'),str(local/'absent.json')],capture_output=True).returncode==2)
statuses={}
for fixture in ['unsafe','improved']:
    report=local/(fixture+'.json')
    result=subprocess.run([str(ROOT/'.local/bin/trivy'),'config','--cache-dir',str(ROOT/'.local/cache'),'--severity','HIGH,CRITICAL','--exit-code','1','--format','json','--output',str(report),str(ROOT/'fixtures/dockerfiles'/fixture)])
    statuses[fixture]=result.returncode
    if result.returncode not in [0,1]:raise RuntimeError('Trivy config failed: '+fixture)
    data=json.loads(report.read_text())
    failures=[{'id':v['ID'],'severity':v['Severity'],'status':v['Status']} for target in data.get('Results',[]) for v in target.get('Misconfigurations',[]) if v['Status']=='FAIL']
    statuses[fixture+'_findings']=failures
check('Actual Trivy scan rejects the root-user Dockerfile',statuses['unsafe']==1 and bool(statuses['unsafe_findings']))
check('Actual Trivy scan accepts the improved Dockerfile at HIGH/CRITICAL threshold',statuses['improved']==0 and not statuses['improved_findings'])
output={'executed_at_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'checks_passed':len(checks),'checks':checks,'config_drill':statuses,'scope':'Synthetic fixtures test policy exits; separate actual Trivy config scans test Dockerfile findings. Neither fixture is a vulnerability scan of a production image.'}
(ROOT/'.local/verification.json').write_text(json.dumps(output,indent=2)+'\n')
print(json.dumps(output,indent=2))
