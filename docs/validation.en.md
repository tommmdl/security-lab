# What was exercised

English · [Português](validation.md) · [Home](../README.en.md)

All [15 local tests](../evidence/local-tests.json) passed. Thirteen use explicitly synthetic reports to exercise approval, blocking and error exits: no findings, medium severity, HIGH with/without fixes, CRITICAL, OS end-of-life, missing inventory, unexpected severity, malformed JSON, missing files, a JSON array instead of an image report and an invalid findings collection.

Two further tests run actual Trivy config scans. USER root was rejected by DS-0002; the non-root example with a healthcheck passed at HIGH/CRITICAL threshold. This verifies configuration scanning, not removal of base-image vulnerabilities.

Actual scans also ran against both remote images by digest on linux/amd64. Both commands exited 1 because the gates blocked their reports. Full JSON and SARIF were produced first. The [local summary](../evidence/local-summary.json) records counts; notes-api and postgres under evidence contain decisions, blocking occurrences and scan identification.

Trivy completed both collections without an operational error. Policy blocked 48 API occurrences and 99 PostgreSQL occurrences. These reflect the database used at scan time; they do not establish exploitability, an incident or completed remediation.

Exploitation, runtime reachability, private registry authentication, Code Scanning, branch protection, secrets and licenses were not tested. Scanner/archive versions are fixed while vulnerability data and the checks bundle remain updateable. The Trivy archive checksum was checked; Sigstore provenance was not verified.

The [final GitHub Actions run](https://github.com/tommmdl/security-lab/actions/runs/39173470418) passed all **15 laboratory tests** and blocked both images: 48 API occurrences and 99 PostgreSQL occurrences. Its overall conclusion is **failure**, as required by policy. See [test results](../evidence/ci-tests.json), [scan summary](../evidence/ci-summary.json) and [job conclusions/tested revision](../evidence/ci-run.json). Full JSON report hashes and SARIF structure were checked after artifact download. Configuration tests delete old reports and require newly generated JSON before accepting an expected exit 1. Later documentation commits do not alter tested code.
