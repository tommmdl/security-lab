# What was exercised

English · [Português](validation.md) · [Home](../README.en.md)

All [13 local tests](../evidence/local-tests.json) passed. Eleven use explicitly synthetic reports to exercise approval, blocking and error exits: no findings, medium severity, HIGH with/without fixes, CRITICAL, OS end-of-life, missing inventory, unexpected severity, malformed JSON and missing files.

Two further tests run actual Trivy config scans. USER root was rejected by DS-0002; the non-root example with a healthcheck passed at HIGH/CRITICAL threshold. This verifies configuration scanning, not removal of base-image vulnerabilities.

Actual scans also ran against both remote images by digest on linux/amd64. Both commands exited 1 because the gates blocked their reports. Full JSON and SARIF were produced first. The [local summary](../evidence/local-summary.json) records counts; notes-api and postgres under evidence contain decisions, blocking occurrences and scan identification.

Trivy completed both collections without an operational error. Policy blocked 48 API occurrences and 99 PostgreSQL occurrences. These reflect the database used at scan time; they do not establish exploitability, an incident or completed remediation.

Exploitation, runtime reachability, private registry authentication, Code Scanning, branch protection, secrets and licenses were not tested. Scanner/archive versions are fixed while vulnerability data and the checks bundle remain updateable. The Trivy archive checksum was checked; Sigstore provenance was not verified.

The GitHub Actions result will be recorded after the first run.
