# Turn a report into concrete work

English · [Português](triage.md) · [Home](../README.en.md)

The gate is conservative: it stops approval and provides a report for investigation. Severity comes from Trivy's data sources. Exploitability, application reachability and operational priority require separate assessment.

## What the local scan found

| Image | HIGH | CRITICAL | Blocking occurrences without a published fix |
| --- | ---: | ---: | ---: |
| Basic API | 48 | 0 | 44 |
| PostgreSQL | 95 | 4 | 74 |

Four API HIGH occurrences had FixedVersion populated: msgpack 1.1.2 → 1.2.1, setuptools 70.3.0 → 78.1.1 and two urllib3 advisories for 2.7.0 → 2.8.0. These versions come from the scanner; they were not applied or functionally tested here. Check package locations and advisories before changing the app.

Some PostgreSQL findings belong to `usr/local/bin/gosu`, an executable embedding Go libraries. Others belong to Debian packages. A helper finding does not imply PostgreSQL's server is written in Go, and separately installing a newer Go tool does not rebuild that executable.

The four local CRITICAL findings are CVE-2025-7458 in libsqlite3-0, CVE-2026-6653 in libxml2, CVE-2023-45853 in zlib1g and CVE-2025-68121 in the gosu helper's stdlib, according to the report. Investigate each using Target, version, Status, advisory sources and references rather than treating every occurrence as one exploitation path.

## A triage route

1. Confirm digest and platform in run.json. A changed tag can reference another image.
2. Group by advisory and package. One CVE can affect several packages from a shared source.
3. Inspect Target and package details in scan.json. Distinguish Python packages, OS packages and Go code embedded in a binary.
4. Review FixedVersion, Status and vendor links. An empty fix field does not by itself establish a distribution's maintenance state; vendor-specific decisions may apply.
5. Prepare a base-image or dependency update in the owning project's branch. Rebuild and functional tests come before promoting its new digest.
6. Scan the built image again and compare reports. Editing requirements without rebuilding does not change the old artifact.

security-lab did not deploy any of those updates. It records existing targets and blocks their approval under the chosen policy.

## If another context needs an exception

Risk acceptance needs an owner, advisory/package-specific rationale, scope, evidence and a review deadline. This lab has no approved exceptions, so its ignore file remains empty even for findings without FixedVersion.

## Why results may differ

Full JSON includes LOW, MEDIUM and UNKNOWN; the gate evaluates HIGH/CRITICAL and OS end-of-life. Sources may rate the same vulnerability differently and the database changes over time. Compare database metadata before interpreting count differences as image changes.

The basic and instrumented API are different artifacts. Rescanning the base does not automatically cover all tracing-lab additions. To expand the matrix, publish an appropriate target and add its digest to config/targets.json and the workflow.
