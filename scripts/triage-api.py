#!/usr/bin/env python3
"""Group the complete API report without editing or suppressing any finding."""
import collections,json,hashlib,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
report=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'evidence/api-high-review/after-scan.json'
d=json.loads(report.read_text());groups=collections.defaultdict(list)
for result in d['Results']:
 for v in result.get('Vulnerabilities') or []:
  if v['Severity']=='HIGH':groups[v['VulnerabilityID']].append(v)
reviews={
'CVE-2026-76642':('util-linux','Privileged post-mount hooks after a failed mount helper','Non-root, no effective capabilities, no-new-privileges; benign mount denied'),
'CVE-2026-78408':('util-linux','Privileged nsenter --join-cgroup descriptor inheritance','No privileged namespace entry; no host PID namespace or Docker socket'),
'CVE-2026-78409':('util-linux','X-mount.subdir intermediate symlink resolution','No authorized custom fstab mount path; no mounting capability'),
'CVE-2026-78410':('util-linux','Restricted bind-mount source redirection','No bind-mount privileges or privileged API mount operation'),
'CVE-2026-54369':('acl','Privileged pathname-based libacl calls follow symlinks','No privileged ACL caller identified in the notes API; non-root and read-only root'),
'CVE-2025-69720':('ncurses','infocmp CLI stack overflow','infocmp is present; notes routes do not invoke it or accept terminfo input'),
'CVE-2026-16742':('systemd','systemd-homed local group manipulation','Specific systemd-homed binary/service is absent; package finding retained'),
'CVE-2026-9538':('perl','Archive::Tar entry size can exhaust memory','Archive::Tar is not importable; no archive-upload route; resource limits'),
}
rows=[]
for c,vs in sorted(groups.items()):
 source,prerequisite,mitigation=reviews.get(c,('unreviewed','Requires new analysis','No classification yet'))
 rows.append({'cve':c,'high_occurrences':len(vs),'source_family':source,'packages':[{'name':v['PkgName'],'installed_version':v['InstalledVersion'],'fixed_version_reported':v.get('FixedVersion') or None} for v in vs],'vendor_source':'https://security-tracker.debian.org/tracker/'+c,'prerequisite':prerequisite,'mitigation_or_reachability':mitigation,'scanner_decision':'still HIGH and blocking','patch_status':'No fixed version reported for the installed release in this scan; stable candidates inspected separately','not_a_vex_or_ignore_rule':True})
result={'image':d['ArtifactName'],'high_occurrences':sum(len(v) for v in groups.values()),'distinct_high_cves':len(groups),'report_sha256':hashlib.sha256(report.read_bytes()).hexdigest(),'reviews':rows,'scope':'Source-package occurrence grouping, vendor review and benign runtime controls. No exploitation proof, no suppression, no severity change and no claim of patched binaries.'}
(ROOT/'.local/api-high-review').mkdir(parents=True,exist_ok=True)
(ROOT/'.local/api-high-review/triage.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
