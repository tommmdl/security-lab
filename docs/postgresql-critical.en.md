# Three critical findings, three different decisions

[Português](postgresql-critical.md) · English

We checked Debian's advisories, inspected the actual image and tested changes on disposable databases. We added no ignore entries or VEX suppression, did not alter reports and kept the blocking policy unchanged.

| Finding | What we found | Decision |
|---|---|---|
| CVE-2025-7458 / SQLite | Affected library brought in by GPG, without a link to the PostgreSQL server. | Remove packages unused at runtime. |
| CVE-2026-6653 / libxml2 | Affected library loaded by PostgreSQL. | Reduce privileges and constrain resources; it remains vulnerable. |
| CVE-2023-45853 / zlib | The affected MiniZip code is not built in the inspected Debian binary. | Record applicability while retaining the finding in the scan and gate. |

## SQLite: remove an unnecessary dependency

[Debian](https://security-tracker.debian.org/tracker/CVE-2025-7458) identifies the installed Bookworm version as affected, without a fix for that stable release. The advisory concerns crafted queries against SQLite, not PostgreSQL SQL. We do not lower severity because of that distinction.

The installed reverse dependency is GPG. `ldd` does not find SQLite in the PostgreSQL server, and apt's simulation preserves server/client packages. The image uses `apt-get purge --auto-remove libsqlite3-0`: the library, package metadata and unused key-management tools leave together. gpgv and Debian archive keyrings remain for signature verification. Future tools/extensions requiring SQLite need another dependency review.

Inventory drops from **144 to 128 packages**; reported occurrences drop from **412 to 350**. HIGH goes from 71 to 68, and CRITICAL from 3 to 2. These are package/advisory occurrences, not unique CVEs. The [full report](../evidence/critical-review/postgres-after.json) includes every severity. The [comparison](../evidence/critical-review/comparison.json) records the database snapshot and report hash; the previous scan remains under `evidence/remediation/`.

## libxml2: compensating controls, without claiming a fix

[Debian](https://security-tracker.debian.org/tracker/CVE-2026-6653) marks this Bookworm version affected, with the fix postponed. Debian's lower assessment and NVD's CRITICAL classification remain recorded; we do not substitute one for the other.

PostgreSQL loads libxml2, including for its [XML functions](https://www.postgresql.org/docs/17/xml-limits-conformance.html). The API uses parameterized queries and stores titles as VARCHAR. XML-looking text stays literal in the tests. This limits the normal HTTP path, but does not establish absence of exposure after SQL access: a benign XMLPARSE query **still works as the ordinary application role**. No malicious XML exploit was run.

The application previously used the initialization superuser. PostgreSQL requires [bootstrap OID 10 to remain a superuser](https://github.com/postgres/postgres/blob/REL_17_STABLE/src/backend/commands/user.c). The script preserves it as `notes_bootstrap`, clears its password and creates a new ordinary `lab` with the same API login/password. It transfers only the notes database/table, not system catalog ownership; identity-sequence ownership follows the table. Old bootstrap client sessions are terminated during the first migration.

`lab` cannot assume administrative roles, create roles, read server files or execute COPY PROGRAM. It still owns the lab database/table for existing migrations: this is not strict DML-only access. `notes_admin` provides maintenance through the Unix socket. Both administrative roles have no password and explicit TCP rejection before upstream rules, including loopback and replication, following [HBA rule ordering](https://www.postgresql.org/docs/17/auth-pg-hba-conf.html). Access to the trusted socket inside the database container remains an administrative boundary.

Compose caps the database at 384 MiB, one CPU and 256 PIDs, adds no-new-privileges and keeps the database port unpublished. Kubernetes adds a one-core limit alongside its existing 384 MiB limit; UID 999, dropped capabilities and seccomp remain. The ClusterIP is still reachable from other pods: we do not claim an enforced NetworkPolicy on kind's default network.

Role defaults set a 5-second statement timeout and a 10-second idle-transaction timeout. SQL users can change these defaults, and native-code failures need not honor an interrupt promptly. Cgroups constrain host resource consumption, but cannot guarantee database availability or prevent a memory-safety flaw. **libxml2 is not patched; its CVE still blocks the gate.**

## zlib: the source advisory and the shipped binary

[Debian](https://security-tracker.debian.org/tracker/CVE-2023-45853) explains that Bookworm's binary package does not build the affected contrib/minizip code. We inspected the actual libz library, saved its checksum and dynamic symbols, and found no `zipOpenNewFileInZip4_64` export. Package/file-name inventory found no MiniZip or pyminizip. See the [applicability evidence](../evidence/critical-review/zlib-applicability.json).

These results support affected-code absence in the inspected packaged library. They do not establish that every possible third-party binary with statically embedded libraries is unaffected. zlib remains required and installed. Trivy still reports this CVE as CRITICAL and the gate still counts it. No exception, VEX suppression or edited JSON is used to make the result green.

## Upgrade and checks

Fresh databases run the image hook. Existing volumes need an explicit migration after image replacement; initialization hooks do not rerun. Data, globals and HBA backups stay outside Git. The [operating guide](https://github.com/tommmdl/docker-lab/blob/main/docs/database-hardening.en.md) explains commands and migration limits, scoped to `notes`/`lab`. Rolling back an image does not undo persisted roles or HBA rules.

The **20 security checks** exercise real privilege denials, admin TCP rejection, timeouts, limits and residual XML reachability. The **23 integration checks** cover API behavior and persistence. The upgrade test creates three notes in the previous image, replaces it on the same volume, migrates roles, terminates a held privileged session and compares every note field. The login is preserved and repeated hardening is tested. It removes only its own temporary environment.

JSON records and inspections live under [critical-review](../evidence/critical-review/). The gate still blocks **68 HIGH and 2 CRITICAL** findings. Removing SQLite, mitigating libxml2 exposure and assessing zlib applicability are different outcomes; none is presented as a clean security scan.
