# Fixing what we can, keeping the rest visible

[Português](remediation.md) · English

We started with the findings that had a published fix in the Trivy database. We kept the scanner version, platform and blocking policy unchanged. No CVE was added to an ignore list, and unfixed findings still count.

| Image | Total before → after | HIGH before → after | CRITICAL before → after | Findings with a fix after |
|---|---:|---:|---:|---:|
| API | 173 → 164 | 48 → 44 | 0 → 0 | 0 |
| PostgreSQL | 472 → 412 | 95 → 71 | 4 → 3 | 0 |

These are reported occurrences, not counts of unique CVEs. The [comparison](../evidence/remediation/comparison.json) records the database timestamp and report hashes. Full before/after reports are stored alongside it, including LOW, MEDIUM, UNKNOWN and unfixed findings. The earlier laboratory evidence remains unchanged.

## What changed

The API installs its requirements during the build, then removes pip and ensurepip from the runtime image. Vulnerable copies of msgpack, setuptools and urllib3 belonged to pip's internal tooling; installing newer top-level packages would not replace those copies. We remove the unneeded installer itself, including its embedded wheels, rather than hiding package metadata. Flask becomes 3.1.3, and Debian liblzma5 becomes 5.8.1-1+deb13u2.

The PostgreSQL image keeps version 17.11, Bookworm, the original entrypoint and the data layout. Its gosu 1.19 helper is rebuilt from upstream commit `6456aaa0f3c854d199d0f037f068eb97515b7513` using Go 1.27.2, moby/sys/user 0.4.1 and x/sys 0.44.0. The module updates intentionally modify that source checkout; Go build metadata reports `vcs.modified=true`. The compiler stays in the build stage. UID switching is checked during the build and database initialization is exercised by Compose integration tests.

The API and database sources live in [docker-lab](https://github.com/tommmdl/docker-lab). [github-actions-lab](https://github.com/tommmdl/github-actions-lab) builds both images, tests them together and publishes the exact tested image IDs. Both use the existing public GHCR package; database tags have the `postgres-` prefix. Publication does not depend on the separate security gate, so a published remediation image is not a security approval.

## What still needs work

The gate still blocks both images: 44 HIGH occurrences in the API and 71 HIGH plus 3 CRITICAL in PostgreSQL. No remaining finding has a FixedVersion in this database snapshot. That does not establish that no mitigation exists or that an advisory cannot change.

The remaining critical IDs in PostgreSQL are CVE-2025-7458 (libsqlite3-0), CVE-2026-6653 (libxml2) and CVE-2023-45853 (zlib1g). They remain in the reports and gate output. Vendor status and actual reachability need individual review before any exception is considered. This change makes no exceptions and does not claim that either image is ready for production.

## Checks

We run the 23 API/Compose integration checks on a separate project and volume, including fresh database initialization, persistence after container recreation, database outage responses and recovery. Before touching the running cluster, we save a private pg_dump and restore it into a separate database on the rebuilt PostgreSQL image. Row count and a content checksum must match. Backups and note contents stay outside Git.

Reproduce collection without filtering: `python3 scripts/scan.py notes-api` and `python3 scripts/scan.py postgres`. Exit 1 means the unchanged gate blocked remaining findings. The full JSON and SARIF reports are uploaded by Actions even when it fails. Counts may change when the vulnerability database changes.

Sources: [upstream PostgreSQL Dockerfile](https://github.com/docker-library/postgres/blob/master/17/bookworm/Dockerfile), [gosu source](https://github.com/tianon/gosu/tree/6456aaa0f3c854d199d0f037f068eb97515b7513), [Go releases](https://go.dev/dl/).

## The API running with tracing

The local instrumented variant was also rebuilt from the published corrected API digest. OpenTelemetry dependencies are installed in a separate build stage; pip and ensurepip stay out of the final image. Its full `traced-api-before.json` and `traced-api-after.json` reports show the same reduction from 173 to 164 findings and zero remaining findings with a published fix in this snapshot. This additional local scan does not add a third image to the remote CI matrix.

## Running environments and validation

The published digests were rescanned directly from GHCR and reproduced the local counts. [Actions](https://github.com/tommmdl/security-lab/actions/runs/39174255658) passed all 15 policy/configuration checks and correctly blocked both images. [Publication](https://github.com/tommmdl/github-actions-lab/actions/runs/39174023844) passed the 23 integration checks. The corrected basic Kubernetes setup passed [24 checks on a disposable cluster](https://github.com/tommmdl/kubernetes-lab/actions/runs/39174243152).

Argo CD applied the new database digest and instrumented API tag; the application is Synced/Healthy, the PVC UID and volume remain the same, and 19 local tracing checks passed, including log correlation and Prometheus/Loki datasource health. Readiness returns 200 on ports 8000, 8001 and 8005. See `deployment-checks.json`, `tracing-tests.json` and the CI records beside the reports.

All three running note databases were empty at update time. Their private backups were restored and checked, but that alone would not demonstrate a nonempty restore. We therefore also created three controlled notes, including Portuguese text, in the original official PostgreSQL image, dumped them and restored them into the rebuilt image. Row count and content checksums matched. The integration suite separately verifies persistence with a real test note. These checks cover this lab configuration, not every PostgreSQL extension or production workload.

Loading the registry image through Docker save/kind encountered a missing content digest from the registry index. Pulling the pinned image directly with the Kubernetes container runtime on each node succeeded before rollout. No live volume was recreated.
