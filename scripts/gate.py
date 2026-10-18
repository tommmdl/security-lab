#!/usr/bin/env python3
"""Evaluate a full Trivy image report. 0=allowed, 1=blocked, 2=invalid/error."""
import argparse,json,sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SEVERITIES={'UNKNOWN','LOW','MEDIUM','HIGH','CRITICAL'}
def evaluate(report,policy):
    if not isinstance(report,dict) or not isinstance(policy,dict):raise ValueError('Report and policy must be JSON objects')
    if policy.get('version')!=1 or policy.get('include_unfixed') is not True:raise ValueError('Policy v1 requires unfixed vulnerabilities to stay included')
    if not policy.get('block_severities') or not set(policy['block_severities']).issubset(SEVERITIES):raise ValueError('Invalid severity policy')
    if report.get('SchemaVersion')!=2 or report.get('ArtifactType')!='container_image':raise ValueError('Expected a schema 2 Trivy container image report')
    results=report.get('Results')
    if not isinstance(results,list) or not results:raise ValueError('Image report has no scan results')
    if any(not isinstance(r,dict) for r in results):raise ValueError('Malformed scan result')
    if policy['require_package_inventory'] and not any(r.get('Packages') for r in results):raise ValueError('Image report has no package inventory')
    findings=[]
    for result in results:
        vulnerabilities=result.get('Vulnerabilities') or []
        if not isinstance(vulnerabilities,list):raise ValueError('Vulnerabilities must be a list')
        for finding in vulnerabilities:
            if not isinstance(finding,dict):raise ValueError('Malformed vulnerability finding')
            if finding.get('Severity') not in SEVERITIES or not finding.get('VulnerabilityID') or not finding.get('PkgName'):raise ValueError('Malformed vulnerability finding')
            findings.append({'target':result['Target'],'id':finding['VulnerabilityID'],'package':finding['PkgName'],'installed':finding.get('InstalledVersion',''),'fixed':finding.get('FixedVersion',''),'severity':finding['Severity'],'status':finding.get('Status','unknown')})
    blocked=[v for v in findings if v['severity'] in policy['block_severities']]
    eol=bool(report.get('Metadata',{}).get('OS',{}).get('EOSL'))
    allowed=not blocked and not (eol and policy['block_end_of_life_os'])
    return {'decision':'allow' if allowed else 'block','policy':policy,'artifact':report['ArtifactName'],'severity_counts':dict(Counter(v['severity'] for v in findings)),'finding_count':len(findings),'blocking_count':len(blocked),'blocking_without_fix':sum(not v['fixed'] for v in blocked),'os_end_of_life':eol,'blocking_findings':blocked}
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report',type=Path);parser.add_argument('--output',type=Path);args=parser.parse_args()
    try:
        policy=json.loads((ROOT/'config/policy.json').read_text())
        result=evaluate(json.loads(args.report.read_text()),policy)
        if args.output:args.output.write_text(json.dumps(result,indent=2)+'\n')
        print(f"{result['decision'].upper()}: {result['blocking_count']} HIGH/CRITICAL findings; {result['blocking_without_fix']} without a published fix; EOL={result['os_end_of_life']}")
        return 0 if result['decision']=='allow' else 1
    except (OSError,ValueError,KeyError,TypeError) as error:
        print('ERROR: '+str(error),file=sys.stderr);return 2
if __name__=='__main__':sys.exit(main())
