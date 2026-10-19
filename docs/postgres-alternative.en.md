# A PostgreSQL alternative with the libxml2 fix

[Português](postgres-alternative.md) · English

The tested alternative is PostgreSQL 17.11 on Alpine 3.24.2, extended with our corrected static gosu helper, the existing role-hardening scripts and zlib 1.3.2-r1. It has libxml2 2.13.9-r2 and keeps XML functionality available. CVE-2026-6653 is absent from the full report; the library itself was replaced, rather than hidden from the scanner.

[Debian's advisory](https://security-tracker.debian.org/tracker/CVE-2026-6653) records the upstream fix from libxml2 2.11.0 while the Bookworm version remains affected. We confirmed the installed Alpine package version and the server's dynamic link to libxml2. A benign XPath/XML query and the application tests passed. This is version/vendor evidence and functional validation, not an exploit reproduction.

## What the scans found

| Image/stage | Findings | HIGH | CRITICAL |
|---|---:|---:|---:|
| Current Bookworm derivative | 350 | 68 | 2 |
| Unmodified official Alpine image | 61 | 24 | 1 |
| Alpine with the corrected gosu helper | 1 MEDIUM | 0 | 0 |
| Final Alpine candidate, with zlib updated | 0 | 0 | 0 |

The official Alpine image fixes the target libxml2 issue but carries gosu built with Go 1.24.6, reintroducing CVE-2025-68121. The new Dockerfile copies only our static helper from the immutable Bookworm derivative. It does not copy Debian libraries. The remaining medium finding was CVE-2026-85091 in zlib 1.3.2-r0; the available Alpine update 1.3.2-r1 removes it.

All four stages remain visible in [the comparison](../evidence/postgres-alternative/comparison.json) and the full JSON reports alongside it. The same Trivy 0.76.0 database snapshot and unchanged policy were used. All severities, unfixed findings and package inventory stay enabled; no ignore entry or VEX suppression was added. The final image passes the current gate, but zero reported findings is not proof of complete security. OS vendors have different advisory coverage, so these counts are not a general ranking of distributions.

## Preserve the source before testing a restore

Alpine uses musl/UID 70; the existing Bookworm cluster uses glibc/UID 999. We did not put Alpine on an existing PGDATA directory or PVC. We created separate projects/volumes and used custom-format pg_dump/pg_restore, following PostgreSQL's [logical-backup approach](https://www.postgresql.org/docs/17/backup-dump.html).

The target uses UTF8 with ICU/en-US. The source uses libc/en_US.utf8. Actual provider and version metadata is recorded in the test JSON. These are different locale environments; the notes schema sorts by numeric ID and has no title index. Compatibility was tested for this application, not for arbitrary text indexes, extensions or locale-dependent queries. See PostgreSQL's [locale documentation](https://www.postgresql.org/docs/17/locale.html).

The repeatable test seeds seven notes including Portuguese, Japanese, emoji, quotes and combining accents, then checks every row field, column properties, indexes and sequence state after logical restore. It verifies a fresh generated ID, runs the 23 API and 20 privilege/resource checks, and confirms persistence after container recreation. A reverse dump is restored into another Debian database: rows and the current sequence match, while the original source rows and sequence remain unchanged.

The local run also restored private backups of the Kubernetes, Docker and GHCR-demo databases into three separate target databases. Every note field matched. All three live databases were empty; the seven-note fixture provides the nonempty case. Dumps and comparison content stay outside Git. Local results contain 17 controlled migration checks plus these three live-restore checks; CI runs the 17 controlled checks without local data.

Accounts and authentication are recreated using the existing lab hook, not a blind globals restore. The application remains non-superuser, maintenance remains TCP-rejected, and memory/CPU/PID limits remain. The expected database UID is 70 for this image. Ownership/no-owner/no-acl restore is scoped to the notes schema; preservation of every possible cluster privilege is not claimed.

## Test environment and default environment

The alternative runs separately on http://localhost:8015. It contains seven fixture notes and uses its own volume. The three original services and the Kubernetes PVC keep their Bookworm image. Their findings remain visible and blocking in the existing matrix; no production cutover is implied.

[Docker lab instructions](https://github.com/tommmdl/docker-lab/blob/main/docs/postgres-alternative.en.md) cover starting the isolated preview, repeating the tests and stopping it without deleting its volume. `scripts/alternative.sh` restricts operations to the alternative project; the test creates and cleans up only its own source/target projects. The successful local preview is kept separately.

The CI publishes the exact tested alternative under `postgres-alpine-` tags in the existing public GHCR package. Consumers use its digest. Publishing does not attach it to original volumes. A real cutover would need a final consistent export, controlled handling of writes, locale/index/extension review and a retained rollback source; that cutover is outside this isolated test.

Sources: [official image tags](https://hub.docker.com/_/postgres), [Alpine Dockerfile](https://github.com/docker-library/postgres/blob/master/17/alpine3.24/Dockerfile), [CVE vendor record](https://security-tracker.debian.org/tracker/CVE-2026-6653). Immutable image references and report hashes are kept with the evidence.

## Published and verified

[GitHub Actions](https://github.com/tommmdl/github-actions-lab/actions/runs/39181777856) passed the 17 migration, 23 API and 20 security checks, then published the tested images. The Compose alternative pins that API/image pair by digest. A full scan pulled from GHCR still reports zero findings; manifest hashes and image config digests match the CI-tested images. The complete [publication and scan evidence](https://github.com/tommmdl/security-lab/tree/main/evidence/postgres-alternative) remains available. This is a dated scanner snapshot, not a guarantee against future findings.

The [security workflow](https://github.com/tommmdl/security-lab/actions/runs/39182367579) independently confirmed **zero findings and an allowed gate for Alpine**. All 15 policy checks passed. The API and Bookworm gates remain blocked, so the overall workflow is red as intended. Full JSON/SARIF reports for all three targets are preserved in [security-ci-reports](../evidence/postgres-alternative/security-ci-reports). After switching only the isolated preview to the published image pair, all seven notes were identical; original notes and the Kubernetes PVC were also verified unchanged.
