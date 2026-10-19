# Alpine becomes the labs' default API

English · [Português](api-adoption.md)

Docker and basic Kubernetes manifests now select the published Alpine API. The primary OpenTelemetry workload managed by Argo CD selects the instrumented Alpine derivative. These are the same digests validated in the [isolated experiment](api-alpine.en.md):

- Basic: `ghcr.io/tommmdl/docker-lab@sha256:ae2e93fdbab7bc912897e6524b3e17b982e97cfb29bcb4fc36d9c014d615eb91`.
- OpenTelemetry: `ghcr.io/tommmdl/docker-lab@sha256:e01c467c0987cc2d999778a4e9ee429bee1d6af4bcdef80e38ce620b95a0b8da`.

Runtime retains Python 3.13.16, Flask 3.1.3 and Psycopg 3.3.6 on Alpine 3.24.2/musl. The derivative retains the tested OpenTelemetry versions. This adoption did not convert a database, change credentials or migrate schema. Existing Alpine PostgreSQL databases, containers/PVCs and data stay in place.

## Data protection and actual rollback

We privately saved resolved Compose configuration, the Deployment and Argo Application configuration before cutover. Both databases received custom-format pg_dump backups. Each backup was restored into a separate temporary database, comparing every note field, columns, indexes and identity sequence. Only those uniquely named verification databases were removed. Dumps and recovery configuration remain outside Git under `security-lab/.local/api-adoption/`.

APIs were briefly stopped during capture to compare a consistent state. The API is the lab's only expected external writer. Later Kubernetes transitions used rolling updates with two replicas; this does not certify general zero downtime. Docker API container replacement causes a short interruption.

This was more than an empty `rollout undo`. On Docker, Alpine created a controlled Unicode note. We returned to the previous Debian digest, read **every field of that same note**, returned to Alpine and checked again. The database container itself was never replaced.

On the primary Kubernetes Service we exercised basic Alpine → basic Debian → basic Alpine, then OpenTelemetry Alpine → original instrumented image → OpenTelemetry Alpine. A note written after each first cutover remained available during rollback. The original instrumented version also ran actual tracing checks before returning to the adopted image.

Only operation-owned notes were deleted. Pre-existing records were compared at the end. Tests can advance the identity sequence; it was not rewound. Backups remain retained. No stale dump was restored over the live database, which would have discarded newer writes.

## Retained recovery versions

The previous Debian basic API remains published by digest:

`ghcr.io/tommmdl/docker-lab@sha256:343f2b23294c09bea9c3250a3b3fd1f95d817acea9db0231dfaaaf406f22fbac`

The original instrumented image was local: `tracing-lab-api:otel-c5d4e188167922bd`. We retained the image and a checksummed private Docker archive rather than relying solely on node caches. Previous build sources remain in `instrumentation/Dockerfile.debian` and `docker-lab/images/api-debian/Dockerfile`. The exact retained image/archive supports recovery; rebuilding old sources does not guarantee identical bytes.

For an interrupted stage, control writes and inspect private snapshots. Docker's `docker-source.json` records the previous image with the same volume and Secrets:

```bash
bash docker-lab/scripts/compose.sh -p docker-lab -f PRIVATE_PATH/docker-source.json up -d --no-build --no-deps --wait api
```

This changes only the API. For a permanent rollback, also update default Compose before returning to normal commands; default `up` reapplies the repository's declared digest.

For Kubernetes, temporarily pause Application automation, select the previous image with the appropriate pull policy, then check rollout, data and tracing. Reload the local instrumented image with kind if it has left node caches. Update Git before restoring self-heal or Argo will restore the adopted digest. These API versions need no PostgreSQL rollback because schema remains compatible. A future destructive schema migration would invalidate this procedure.

## Aligning the configuration

Default Compose uses the approved basic digest without implicitly building another image. `docker-lab/Dockerfile` now describes Alpine for explicit development builds; that does not change published image identity. API and schema Job manifests in both Kubernetes and GitOps use basic Alpine. The `notes-traced` overlay and tracing patch use the released derivative with `IfNotPresent` instead of a local image name with `Never`.

`tracing-lab/config/app-image.json` records release/base identities separately from a local build-source fingerprint. `scripts/build.sh` prepares the published image by default; `--local` builds/loads another tag without overwriting the release digest or automatically deploying it. A local source hash is not presented as proof of byte-identical rebuilding.

Tracing infrastructure removal now refuses to delete Tempo/Collector while active notes-lab Deployments export to them, including the separate experimental preview. Restore the primary application through Git and stop instrumented previews before removing that infrastructure.

Self-heal was paused only during live rehearsals. We then published final argocd-lab manifests, restored the original prune=false/selfHeal=true policy and checked reconciliation. Source snapshots and rehearsal reports remain retained.

## Visible findings and limits

Active targets become `notes-api`, `notes-api-otel` and `postgres`, using the scanned Alpine digests. `notes-api-debian` retains the basic recovery API and its **164 findings/44 HIGH**; `postgres-bookworm` retains Debian database recovery findings. The original instrumented image also received a complete local scan with inventory intact.

The same policy still blocks HIGH/CRITICAL, including unfixed findings. No ignore rules, severity reductions or historical-report deletion were introduced. Advisory coverage differs between distributions; zero findings in the current snapshot does not guarantee no future vulnerabilities.

## Repeating on a still-unadopted copy

The helper supports these sibling checkouts and existing local cluster with already-hardened accounts. It is not a general deployment tool. Run from the portfolio parent directory before switching runtimes:

```bash
python3 security-lab/scripts/adopt-api.py snapshot
python3 security-lab/scripts/adopt-api.py docker
python3 security-lab/scripts/adopt-api.py kubernetes
```

Existing snapshots and an already-adopted source are rejected; do not repeat the one-time rehearsal on completed labs. The previous tracing image must be available for rollback. Errors stop stages with backups/data retained; Kubernetes automation remains paused until recovery/final configuration publication. Then publish manifests and restore original Argo policy. Only one operator should modify these labs during the operation.

Public evidence lives under [api-adoption](../evidence/api-adoption); dumps and note contents stay private. Port 8016 remains an experimental preview separate from primary 8000/8005. The publication lab and its GHCR demo remain pinned records of an earlier release and were not silently advanced by this adoption.

## Observed adoption results

Both databases were empty before the rehearsal. We created Unicode notes after cutover and checked every field during rollback and the return to Alpine. This verifies preservation of those controlled writes; it does not simulate a large production dataset.

One `/notes` read timed out immediately after rolling out the previous instrumented image. The operation stopped with its backup and note intact; verification resumed without repeating the POST. The helper now retries only reads on transient failures. All 19 tracing checks passed on both the previous image and the adopted Alpine image.

The 23 Docker application checks, 20 database and resource checks, and the self-heal exercise preserving a note and PVC also passed. Subsequent lifecycle tests intentionally recreate Docker containers while keeping the volume; the database container identity stayed unchanged during the API image switch itself. The old image archive was saved privately with a checksum; archive reload was not rehearsed, and the actual rollback used the image already available on the nodes.

## GitHub verification

The [security workflow](https://github.com/tommmdl/security-lab/actions/runs/39287212349) published complete reports: all three active images have zero findings; the retained Debian API has 164/44 HIGH and PostgreSQL Bookworm has 350/68 HIGH/2 CRITICAL. The blocked overall result is expected for these two recovery targets. JSON/SARIF artifacts are copied into the evidence directory, together with the 15 policy checks.

The [19 tracing checks on the runner](https://github.com/tommmdl/tracing-lab/actions/runs/39286801534) also produced complete evidence. The [first Kubernetes run](https://github.com/tommmdl/kubernetes-lab/actions/runs/39286751167) exposed a test race: after a database restart, HTTP recovered before both replicas' readiness probes updated. We kept the availability requirement and now wait for database recovery's deployment rollout before the independent invalid-image test. The [new run](https://github.com/tommmdl/kubernetes-lab/actions/runs/39287632451) records that fix. This is separate from the read timeout observed during the live rehearsal.

The new Kubernetes run passed all 24 recovery, persistence and rollback checks.
