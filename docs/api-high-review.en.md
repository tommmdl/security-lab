# What is behind the API's 44 HIGH findings

English · [Português](api-high-review.md)

This is the historical Debian review. The active API is now Alpine; the affected image is retained as `notes-api-debian`. [Current adoption](api-adoption.en.md).

A new full scan of image `sha256:343f2b23294c09bea9c3250a3b3fd1f95d817acea9db0231dfaaaf406f22fbac` confirmed **164 findings, including 44 HIGH occurrences across eight distinct CVEs**. These are package/CVE occurrences: the same util-linux source issue is reported against several binary packages. None of these HIGH findings was attributed to Flask, Gunicorn or Psycopg in this snapshot.

The decision remains **block**. We did not change severities, ignorefile, policy, dpkg metadata or historical reports. This round limits exposure and impact; it does not patch the affected Debian binaries or approve the image.

## Reviewing each CVE

| CVE | HIGH occurrences | Affected path and lab assessment |
| --- | ---: | --- |
| [CVE-2026-76642](https://security-tracker.debian.org/tracker/CVE-2026-76642) | 9 | Privileged mount hooks after a helper fails. `mount` exists and retains SUID; the API has no mount privileges and the benign attempt was denied. |
| [CVE-2026-78408](https://security-tracker.debian.org/tracker/CVE-2026-78408) | 9 | Privileged descriptor inheritance through `nsenter --join-cgroup`. No privileged operator takes this path through the API; benign namespace entry was denied. |
| [CVE-2026-78409](https://security-tracker.debian.org/tracker/CVE-2026-78409) | 9 | Symlink resolution in `X-mount.subdir`, with kernel/fstab prerequisites. The application has no authorized mount operation. We do not rely on the current kernel version as permanent protection. |
| [CVE-2026-78410](https://security-tracker.debian.org/tracker/CVE-2026-78410) | 9 | Source redirection in restricted bind mounts. The API performs no such operation and lacks the necessary capability. |
| [CVE-2026-54369](https://security-tracker.debian.org/tracker/CVE-2026-54369) | 1 | Path-based libacl functions invoked by a privileged caller. No such caller was identified in the notes endpoints; the process is unprivileged with a read-only rootfs. This does not patch the library. |
| [CVE-2025-69720](https://security-tracker.debian.org/tracker/CVE-2025-69720) | 4 | Overflow in CLI tool `infocmp`. The executable is present; this is not an absence conclusion. Endpoints do not invoke it or accept terminfo files. |
| [CVE-2026-16742](https://security-tracker.debian.org/tracker/CVE-2026-16742) | 2 | An issue in service `systemd-homed`. systemd/udev libraries exist, but the specific binary is absent and the service is not running in the API. The source-package finding stays visible. |
| [CVE-2026-9538](https://security-tracker.debian.org/tracker/CVE-2026-9538) | 1 | Memory exhaustion in `Archive::Tar`. `perl-base` is installed but module import fails. There is no archive-upload/extraction endpoint. The finding is retained. |

All packages and versions are listed in [triage.json](../evidence/api-high-review/triage.json). Exposure assessments are inferences from image inspection, endpoint review and benign tests, not proof that future exploitation is impossible. The tracing image derives from the basic API but adds components; testing its controls is not a replacement for its own complete scan.

## Available fixes and why we avoided an untested replacement

The sources above record upstream/newer-release fixes: util-linux 2.42.3/2.42.4, acl 2.4.0, later ncurses branches, later systemd versions and Archive::Tar 3.10. That does not mean those fixes have reached the installed Trixie release.

We queried Trixie and Trixie-security repositories inside a disposable container after refreshing apt indexes. For all five groups, candidates still match installed versions. The [recorded query](../evidence/api-high-review/stable-package-candidates.txt) and vendor trackers make that distinction explicit. Trivy reports no FixedVersion for any of these 44 HIGH occurrences on this distribution in this snapshot.

Mixing sid/forky packages into the stable runtime was not treated as a safe upgrade. Some changes affect ABI. Nor did we force removal of Essential packages such as util-linux, ncurses-bin or perl-base, which could break the image and maintenance tools. `infocmp` and mount utilities remain acknowledged in the evidence; inventory was not deleted to reduce counts.

A smaller base or another distribution can be tested separately with real dependency installation, complete package inventory and API/OpenTelemetry checks. That experiment was not performed here and is not presented as a ready fix.

## What actually changed

Compose now bounds the API to **256 MiB, one CPU and 128 processes**. `/tmp` becomes a **64 MiB** tmpfs with noexec, nosuid and nodev. UID/GID 10001, dropped capabilities, no-new-privileges and read-only rootfs remain. The API is published only on localhost and receives no Docker socket or host application-data mounts.

Kubernetes already had 256 MiB memory and a 64 MiB memory-backed emptyDir. We added a **one-CPU limit per API container** in both basic manifests and Argo CD's Git source. UID/GID 10001, RuntimeDefault seccomp, allowPrivilegeEscalation=false, dropped capabilities and no ServiceAccount token remain active. No per-container PID limit was introduced in the Kubernetes manifest; observed effective values are recorded. We do not claim Kubernetes emptyDir acquired noexec.

Resource limits contain excessive consumption without guaranteeing availability against DoS. Runtime restrictions must accompany the image: running the same digest with privileged settings would invalidate substantial parts of this assessment. No image patch or rebuild occurred in this round; runtime settings were changed and validated. Database, credentials and volumes were not replaced.

## Verification

`tests/api_runtime.py` checks real Docker and Kubernetes processes, cgroup values, read-only rootfs enforcement, denied mount/nsenter operations, absent systemd-homed/Archive::Tar and HTTP 413 rejection above 4 KiB. It does not use an exploit payload, malformed terminfo or memory bomb.

```bash
python3 scripts/scan.py notes-api-debian     # expected exit 1: blocked
python3 scripts/triage-api.py
python3 tests/api_runtime.py          # requires sibling checkouts and both running labs
```

Do not run runtime checks alongside API lifecycle tests. Remote scanning and triage need no Docker/cluster, using the available report. Synthetic policy tests remain separate from live controls and vulnerability analysis.

The [complete reports, checks and limits](../evidence/api-high-review) preserve before/after snapshots. Reduced exposure was not converted into an artificial finding reduction: all 44 HIGH occurrences remain visible and blocking.

Recorded verification: **16 Docker runtime checks, 13 Kubernetes runtime checks and 23 API integration checks passed**. Docker cgroups reported 256 MiB, 100000/100000 CPU quota and 128 PIDs. Kubernetes reported 256 MiB and 100000/100000 CPU quota; its existing effective PID bound is recorded without attributing it to a new manifest setting. The post-mitigation full scan still reports 164 findings/44 HIGH and remains blocked.

The instrumented API also passed 19 tracing checks after the CPU limit rollout. All 15 policy tests passed independently. The deployment record confirms the Docker image matches the scanned digest, the tracing derivative is unchanged, and Argo is Synced/Healthy with self-heal enabled.

The [security workflow](https://github.com/tommmdl/security-lab/actions/runs/39249785138) reproduced the result: 15 policy tests passed, the API remained blocked by 44 HIGH, active Alpine PostgreSQL passed and retained Bookworm remained blocked. The [Kubernetes workflow](https://github.com/tommmdl/kubernetes-lab/actions/runs/39249676675) passed all 24 functional recovery/persistence/rollback checks after adding the CPU quota. Full API CI JSON/SARIF reports are preserved alongside the local reports.
