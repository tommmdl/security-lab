# What was exercised

English · [Português](validation.md) · [Home](../README.en.md)

All [15 local tests](../evidence/local-tests.json) passed. Thirteen use explicitly synthetic reports to exercise approval, blocking and error exits: no findings, medium severity, HIGH with/without fixes, CRITICAL, OS end-of-life, missing inventory, unexpected severity, malformed JSON, missing files, a JSON array instead of an image report and an invalid findings collection.

Two further tests run actual Trivy config scans. USER root was rejected by DS-0002; the non-root example with a healthcheck passed at HIGH/CRITICAL threshold. This verifies configuration scanning, not removal of base-image vulnerabilities.

Actual scans also ran against both remote images by digest on linux/amd64. Both commands exited 1 because the gates blocked their reports. Full JSON and SARIF were produced first. The [local summary](../evidence/local-summary.json) records counts; notes-api and postgres under evidence contain decisions, blocking occurrences and scan identification.

Trivy completed both collections without an operational error. Policy blocked 48 API occurrences and 99 PostgreSQL occurrences. These reflect the database used at scan time; they do not establish exploitability, an incident or completed remediation.

Exploitation, runtime reachability, private registry authentication, Code Scanning, branch protection, secrets and licenses were not tested. Scanner/archive versions are fixed while vulnerability data and the checks bundle remain updateable. The Trivy archive checksum was checked; Sigstore provenance was not verified.

The [final GitHub Actions run](https://github.com/tommmdl/security-lab/actions/runs/39173470418) passed all **15 laboratory tests** and blocked both images: 48 API occurrences and 99 PostgreSQL occurrences. Its overall conclusion is **failure**, as required by policy. See [test results](../evidence/ci-tests.json), [scan summary](../evidence/ci-summary.json) and [job conclusions/tested revision](../evidence/ci-run.json). Full JSON report hashes and SARIF structure were checked after artifact download. Configuration tests delete old reports and require newly generated JSON before accepting an expected exit 1. Later documentation commits do not alter tested code.

## A real cycle: a new vulnerability after adoption

The adopted images passed the gate on 2026-10-19. Ten days later, with no image or code change, the vulnerability database reported two new findings with published fixes:

| Adopted image | Finding | Package | Fix |
| --- | --- | --- | --- |
| `postgres` (`sha256:8b6813ec…`) | CVE-2026-111943, HIGH | Go stdlib 1.27.2 in `gosu` | Go 1.27.3 |
| `notes-api-otel` (`sha256:e01c467c…`) | GHSA-6q48-6c7w-9gw2, CRITICAL | `certifi` 2026.7.22 | 2026.10.18 |

1. **Detection.** [Run 40933751374](https://github.com/tommmdl/security-lab/actions/runs/40933751374), on 2026-10-29, was the first with an expected decision per image (`expect` in `config/targets.json`). Both retained Debian images were blocked as expected, and both adopted images were blocked unexpectedly, which turned the workflow red. The gates are kept in [`evidence/readopt/detected-postgres-gate-run-40933751374.json`](../evidence/readopt/detected-postgres-gate-run-40933751374.json) and [`detected-notes-api-otel-gate-run-40933751374.json`](../evidence/readopt/detected-notes-api-otel-gate-run-40933751374.json), because Actions artifacts expire after 30 days.
2. **Fix at the source.** The Alpine PostgreSQL image used to copy `gosu` from the retained Debian image. docker-lab now builds it in the same Dockerfile with a digest-pinned `golang:1.27.3-bookworm` (commit `11223c7`). tracing-lab moved `certifi` to 2026.10.18 (`3ced2dd`). The retained Debian image keeps the old binary and stays blocked.
3. **Rebuild through the existing pipeline.** github-actions-lab pinned the new revisions (`5b49e2f`). [Run 40938591600](https://github.com/tommmdl/github-actions-lab/actions/runs/40938591600) tested and published Alpine PostgreSQL `sha256:d99044c0…`, and [run 40938591556](https://github.com/tommmdl/github-actions-lab/actions/runs/40938591556) tested and published the OpenTelemetry API `sha256:853f73da…`. Both local scans returned ALLOW with zero HIGH/CRITICAL; `postgres-bookworm` stayed BLOCK.
4. **Re-adoption with rollback in docker-lab.** [`scripts/readopt-patched.py`](../scripts/readopt-patched.py) ran against the local Compose project:
   - [PostgreSQL](../evidence/readopt/postgres.json): 9 checks. Writes paused, logical backup verified in a separate database, image swap on the same volume (same PostgreSQL 17.11/Alpine 3.24 base; only `gosu` changed), a write after the swap, a real rollback to the previous image reading that write through the API, and a return to the patched image. `gosu` reported go1.27.2 before and go1.27.3 after.
   - [OpenTelemetry API](../evidence/readopt/notes-api-otel.json): 6 checks. Image swap, CRUD, a real rollback reading the note written on the new image, and a return. `certifi` reported 2026.7.22, then 2026.10.18. OTLP exporters were off because the Compose project has no collector.
5. **Propagation.** The new digests went to docker-lab (`a4a2336`), kubernetes-lab (`07d1df7`), argocd-lab (`283b20f`) and tracing-lab (`d0d2921`), plus this repository's `config/targets.json`. The consumer CIs passed: [tracing-lab 40942613603](https://github.com/tommmdl/tracing-lab/actions/runs/40942613603), on kind with real traces, [kubernetes-lab 40942596923](https://github.com/tommmdl/kubernetes-lab/actions/runs/40942596923) and [argocd-lab 40942605890](https://github.com/tommmdl/argocd-lab/actions/runs/40942605890). [Run 40942678712](https://github.com/tommmdl/security-lab/actions/runs/40942678712) shows the expected gate for all five images.

Limits: the local docker-lab database had no notes of its own (the 2026-10-19 adoptions also recorded zero rows), so the row comparison covered the two probe notes, removed at the end. The backup, DR, failover and chaos labs keep the digests of the runs they document. The Kubernetes path of the OpenTelemetry API was validated by the tracing-lab CI, not by a local in-cluster rollback.
