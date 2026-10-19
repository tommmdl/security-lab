# Before approving an image

English · [Português](README.md)

Other labs show the application working. This one asks a different question: what inside an image needs attention before it moves through a pipeline?

Trivy scans three images by digest: the basic API, the Bookworm PostgreSQL used by the labs, and a separately tested Alpine alternative. GitHub Actions preserves reports and blocks HIGH or CRITICAL findings, including those without a published fix.

## A tested alternative for libxml2

The Alpine alternative has **zero findings in the recorded full scan**. Logical restore, API, security and reverse-restore tests passed; original databases remain unchanged. The API and Bookworm gates remain blocked. See the [comparison and complete evidence](docs/postgres-alternative.en.md).

## Review of the remaining PostgreSQL critical findings

SQLite and unused GPG tools were removed from the published image. PostgreSQL goes from 412 to **350 findings**, with **68 HIGH and 2 CRITICAL** remaining. libxml2 has compensating controls and remains affected; Debian's zlib binary does not build the affected MiniZip code, but the scanner finding stays visible and blocking. See the [analysis, sources and complete evidence](docs/postgresql-critical.en.md).

## After the first remediation round

The API went from 173 to 164 findings; PostgreSQL went from 472 to 412. No finding has a published fix in this database snapshot. **44 HIGH findings remain in the API, and 71 HIGH + 3 CRITICAL remain in the database**, so both images are still blocked. The [full reports and comparison](docs/remediation.en.md) show what changed and what still needs attention.


## The initial findings, preserved

The recorded local scan blocked the API for **48 HIGH occurrences** and PostgreSQL for **95 HIGH and 4 CRITICAL**. These are package/advisory occurrences, not necessarily distinct vulnerabilities: the blocking sets contain 12 and 49 distinct identifiers respectively.

All **15 laboratory tests passed**, including one Dockerfile rejected by Trivy and an improved configuration accepted by it. This does not approve the images: tests and image gates have separate results. The complete workflow should remain red while target images violate the policy.

See [results and verification scope](docs/validation.en.md) and [finding triage](docs/triage.en.md).

The [GitHub Actions run](https://github.com/tommmdl/security-lab/actions/runs/39173470418) reproduced this outcome: **15 tests passed, both image gates blocked**.

## Run locally

Use Linux x86_64 or WSL, Git, Python 3 and curl, with access to GitHub, registries and the vulnerability database. These remote targets require neither a Docker socket nor a Kubernetes cluster.

```bash
python3 scripts/prepare.py
python3 tests/verify.py
python3 scripts/scan.py notes-api
python3 scripts/scan.py postgres
python3 scripts/scan.py postgres-alpine
```

Each scan can exit 1 because the image was blocked. Run targets separately or in separate terminals; never add `|| true` to an approval pipeline. Trivy's local cache may serialize concurrent access.

Trivy v0.76.0 is installed under `.local/bin`. Setup compares the official archive SHA-256 against the value committed in `config/tool.json`, without piping a remote installer into a shell. This verifies archive integrity but is not Sigstore provenance verification. Cache stays under Git-ignored `.local/` too.

## How the decision works

Policy is stored in `config/policy.json`:

- HIGH and CRITICAL block with or without an available fixed version.
- An operating system identified as end-of-life also blocks.
- Missing, invalid or inventory-free reports cannot become approval.
- There are no CVE suppressions; `config/empty.ignore` contains no exceptions.

First, Trivy collects full JSON with every severity and package inventory. `--exit-code 0` at that stage allows collection and SARIF conversion to complete. Then `gate.py` evaluates policy and its return code becomes `scan.py`'s final status. Collection exit zero is not the security decision.

| Evaluator exit | Meaning |
| --- | --- |
| 0 | The image meets this policy's criteria, not a guarantee that it has no vulnerabilities. |
| 1 | A valid report was evaluated and the image was blocked. |
| 2 | The report or evaluator configuration is invalid. |

Network, database and scanner failures also fail the command; `gate.json` may be absent in those cases. A new scan removes its previous reports first so stale results cannot appear current.

## Read the outputs

Local results go under `.local/reports/notes-api/` and `.local/reports/postgres/`:

| File | Purpose |
| --- | --- |
| `scan.json` | Full Trivy findings, packages, versions and advisory sources. |
| `scan.sarif` | The same result converted for SARIF-compatible tools. |
| `gate.json` | Policy decision and blocking occurrences. |
| `run.json` | Image, platform, tool version, database metadata and report hash. |

SARIF is uploaded as an artifact, not automatically sent to GitHub Code Scanning. No `security-events: write`, private registry token or additional secret is needed.

Images are pinned in `config/targets.json`, but the vulnerability database keeps changing. Counts can change between scans without an image or code change. Records include database update/download times and describe that scan's snapshot.

## GitHub Actions flow

On code/config pushes to main, pull requests and manual runs, the workflow:

1. Downloads and verifies the pinned Trivy version.
2. Tests approval, blocking, invalid reports and both Dockerfile exercises.
3. Scans API and database in separate jobs without fail-fast cancellation.
4. Uploads JSON, SARIF and decisions even when an image is blocked.

Checkout and artifact actions are pinned by commit. The workflow token only reads repository contents. Gates do not use `continue-on-error`. This workflow neither publishes images nor changes the running application.

To apply the pattern before publication elsewhere, scan before pushing and make publication depend on the approval job. This lab does not configure branch protection or automatically gate another repository's pipeline.

## A small configuration exercise

```bash
.local/bin/trivy config --severity HIGH,CRITICAL --exit-code 1 fixtures/dockerfiles/unsafe
.local/bin/trivy config --severity HIGH,CRITICAL --exit-code 1 fixtures/dockerfiles/improved
```

The first Dockerfile selects USER root and is rejected by DS-0002. The second selects the base image's existing non-root user and declares a healthcheck. Tests verify exit 1 for the first and exit 0 for the second. They do not build or execute either fixture.

This configuration improvement does not fix packages in the base image. Dockerfile configuration and image vulnerability scans answer different questions.

## Scope of this first lab

Targets are the basic API image and the database image. tracing-lab's locally built instrumented variant is outside this CI matrix; it was scanned separately during remediation, with full reports under `evidence/remediation/traced-api-*.json`. Scanning covers known vulnerabilities in Trivy-supported inventory, not exploitation, runtime reachability, secrets, licenses or the entire cluster configuration.

Findings need triage. File paths, package versions, advisory sources, fixed versions and actual use inform impact assessment. Images are not automatically changed and exceptions are not invented to obtain a green result.

Full remediation reports live under `evidence/remediation/` as well as in CI artifacts. The initial scan did not restart containers; image updates have their own checks and records. Setup, tests and records were carried out with assistant help.

References: [pinned release](https://github.com/aquasecurity/trivy/releases/tag/v0.76.0), [image scanning](https://trivy.dev/docs/latest/guide/target/container_image/), [vulnerabilities and severity](https://trivy.dev/docs/latest/guide/scanner/vulnerability/) and [CI integration](https://trivy.dev/docs/latest/ecosystem/cicd/).

The [first remediation round](docs/remediation.en.md) compares complete reports before and after the fixes. Both images still fail the unchanged gate.
