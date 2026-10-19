# Testing the API on Alpine before changing the default

English · [Português](api-alpine.md)

The alternative retains **Python 3.13.16 and the same application lock**, replacing Debian/glibc with Alpine 3.24.2/musl. We built a basic API image and an OpenTelemetry derivative. Both recorded **zero findings in full local scans**. The primary Debian API remains on its earlier image, with all 44 HIGH findings visible and blocking.

This is a separate test. Docker uses its own project, port and volume; Kubernetes uses another Deployment, Service, database and PVC. The primary Service does not select candidate Pods. Main volumes are never mounted into candidates, and the primary Argo CD application source is unchanged.

## The first base had findings too

| Image/stage | Total | HIGH | Other findings |
| --- | ---: | ---: | --- |
| Debian API, preserved reference | 164 | 44 | 58 MEDIUM, 61 LOW, 1 UNKNOWN |
| Official Alpine Python, before application install | 7 | 4 | 3 MEDIUM |
| Application installed, pip/ensurepip removed | 1 | 0 | 1 MEDIUM in zlib |
| Alpine API with updated zlib | 0 | 0 | none in this snapshot |
| Alpine API with OpenTelemetry | 0 | 0 | none in this snapshot |

The official image had findings in dependencies shipped with installer tooling — msgpack, setuptools and urllib3 — plus zlib. We installed the lock and removed pip/ensurepip from runtime, as already done on Debian. Tool code and its metadata leave together; apk inventory and application metadata remain intact. We then updated **zlib 1.3.2-r0 to 1.3.2-r1**, the reported fix for CVE-2026-85091. Intermediate reports are preserved.

Full scans retain **40 inventory entries for the basic API and 63 for the instrumented variant**, including Alpine packages and Python metadata. Scans include all severities and unfixed findings and use the unchanged policy. No ignore rule was added.

The Debian HIGH findings were not patched inside that Debian image. This alternative has a different package/library set. Distributions also differ in advisory coverage; zero in this Trivy database does not guarantee no vulnerabilities or equivalent coverage. The [review of the original eight CVEs](api-high-review.en.md) and complete reports remain available.

## Native dependencies and tracing

Alpine uses musl. We did not copy glibc extensions from Debian: builds install **only compatible wheels**, using `--only-binary=:all:`. Missing compatible wheels fail the build rather than silently compiling another combination.

Psycopg 3.3.6 loaded its musllinux binary backend and libpq 18.6 against PostgreSQL 17.11. Each variant passed **23 API checks and 20 SQL security/resource checks**, including CRUD, database-outage HTTP 503 behavior and persistence after container replacement. Separate checks round-tripped seven Unicode titles containing Portuguese, Japanese, emoji, quotes and combining accents, removing only their own records.

The derivative installs the OpenTelemetry lock in an Alpine stage matching the API base, then copies those dependencies and unchanged `traced.py`. The portable pipeline performs **13 real Flask/Psycopg → Collector → Tempo checks**, without synthetic span injection. In the existing cluster the candidate passed all **19 integration checks**, including span parentage, SELECT, writes, 404, title privacy, Grafana queries and Loki correlation.

Alloy now also accepts `notes-api-alpine` in the namespace it already reads. RBAC was not expanded. The main application keeps `notes-api`. Tracing verification accepts candidate Service/service-name/log-label values through environment settings, with existing defaults unchanged.

Initial startup exposed a race with test database initialization. An initContainer now waits for an SQL connection before starting the API, inheriting the workload's restrictions and resource bounds. The final integration run was repeated after that adjustment.

## Repeating the test

Build the API from docker-lab:

```bash
docker build -f images/api-alpine/Dockerfile -t docker-lab-api-alpine:local .
```

Build instrumentation from tracing-lab:

```bash
docker build -f instrumentation/Dockerfile.alpine -t docker-lab-api-alpine-otel:local instrumentation
```

Building requires Docker with BuildKit/Buildx. The base is pinned by digest; locks pin application and tracing versions. Tests cover **linux/amd64**, not other architectures.

```bash
# docker-lab: creates/removes only its own unique temporary projects
python3 tests/api_alpine.py

# tracing-lab: disposable Compose stack with real Collector and Tempo
python3 tests/alpine_otlp.py
```

For the prepared local cluster, load the local image with kind or use the published digest, then:

```bash
python3 scripts/alpine-lab.py up
python3 scripts/alpine-lab.py test
python3 scripts/alpine-lab.py status
```

The helper requires sibling kubernetes-lab, its existing notes Secret and observability infrastructure. It creates `notes-api-alpine`, `api-alpine-db` and PVC `data-api-alpine-db-0` with separate selectors. It refuses to replace resources lacking its ownership label. `down` removes only those workloads/Services and **retains the PVC**. It does not create or modify the primary Argo CD Application.

## Preview and decision

An isolated Docker preview runs at **http://localhost:8016**:

```bash
bash scripts/api-alpine.sh up -d --no-build --wait
bash scripts/api-alpine.sh ps
bash scripts/api-alpine.sh down
```

The wrapper fixes the alternative project and rejects Compose builds to avoid accidentally building Debian. `down` retains its volume. Main Docker remains on 8000 and main Kubernetes on 8005. Resource limits, non-root UID, dropped capabilities, read-only rootfs and no-new-privileges accompany the candidate.

A separate github-actions-lab workflow builds both images, tests application/SQL/OTLP behavior, scans the full inventory and applies the gate before publishing. Image identities are checked before publication and after pull by digest. Tags use `api-alpine-` and `api-alpine-otel-`; primary pins are unchanged. Published-image reports are retained beside local reports.

This experiment does not adopt Alpine in the main labs or certify arbitrary native extensions. Later adoption would require controlled pin changes, observability validation and a retained image rollback. This is an API-only experiment with separate test databases; no primary database data was migrated.

See [all reports, comparisons and checks](../evidence/api-alpine). References: [official Python image](https://hub.docker.com/_/python) and [Psycopg installation](https://www.psycopg.org/psycopg3/docs/basic/install.html). Reported compatibility comes from actual execution, not documentation alone.

## Published and checked

The [publication workflow](https://github.com/tommmdl/github-actions-lab/actions/runs/39260441607) passed **23 API + 20 SQL/security checks for each variant**, 13 OTLP/Tempo checks and full gates for both images. The registry manifests were independently fetched and their hashes verified; config digests match the CI-tested image IDs. [Published references](../evidence/api-alpine/published-images.txt), [registry verification](../evidence/api-alpine/registry-verification.json) and the full local/CI/remote scans are retained. Both remote scans also report zero findings. Separate security-matrix targets track both candidates alongside the unchanged Debian API target.
