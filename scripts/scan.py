#!/usr/bin/env python3
"""Collect complete reports, then enforce the policy without hiding findings."""
import hashlib,json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT)
if len(sys.argv)!=2:raise SystemExit('Use: python3 scripts/scan.py notes-api|postgres')
target=next((t for t in json.loads((ROOT/'config/targets.json').read_text()) if t['name']==sys.argv[1]),None)
if target is None:raise SystemExit('Unknown target')
output=ROOT/'.local/reports'/target['name'];output.mkdir(parents=True,exist_ok=True)
# Prevent a failed new scan from leaving yesterday's apparently valid report.
for name in ['scan.json','scan.sarif','gate.json','run.json']:(output/name).unlink(missing_ok=True)
trivy=ROOT/'.local/bin/trivy'
report=output/'scan.json'
command=[str(trivy),'image','--cache-dir',str(ROOT/'.local/cache'),'--scanners','vuln','--no-progress','--image-src','remote','--platform','linux/amd64','--list-all-pkgs','--ignore-unfixed=false','--ignorefile',str(ROOT/'config/empty.ignore'),'--severity','UNKNOWN,LOW,MEDIUM,HIGH,CRITICAL','--format','json','--output',str(report),'--timeout','10m','--exit-code','0',target['image']]
subprocess.run(command,check=True)
subprocess.run([str(trivy),'convert','--format','sarif','--output',str(output/'scan.sarif'),str(report)],check=True)
metadata=ROOT/'.local/cache/db/metadata.json'
record={'scanned_at_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'target':target,'platform':'linux/amd64','trivy':json.loads((ROOT/'config/tool.json').read_text()),'database_metadata':json.loads(metadata.read_text()) if metadata.exists() else None,'report_sha256':hashlib.sha256(report.read_bytes()).hexdigest()}
(output/'run.json').write_text(json.dumps(record,indent=2)+'\n')
status=subprocess.run([sys.executable,str(ROOT/'scripts/gate.py'),str(report),'--output',str(output/'gate.json')]).returncode
summary=os.environ.get('GITHUB_STEP_SUMMARY')
if summary:
    with open(summary,'a') as f:
        if (output/'gate.json').exists():
            gate=json.loads((output/'gate.json').read_text())
            f.write(f"## {target['name']}\n\n- Image: `{target['image']}`\n- Decision: **{gate['decision']}**\n- Blocking HIGH/CRITICAL: {gate['blocking_count']}\n- Blocking findings without a fix: {gate['blocking_without_fix']}\n\nFull JSON and SARIF are in the workflow artifact.\n")
sys.exit(status)
