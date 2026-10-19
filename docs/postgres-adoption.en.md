# Alpine is now the labs' database

English · [Português](postgres-adoption.md)

Docker and Kubernetes now use PostgreSQL 17.11/Alpine 3.24.2 with libxml2 2.13.9-r2, zlib 1.3.2-r1 and the rebuilt gosu helper. This is the same image tested and published before adoption:

`ghcr.io/tommmdl/docker-lab@sha256:8b6813ec76804698c33e4dac8f501ca8f641affcbd27cbc3b7dd6fdb02874fc3`

The [earlier analysis](postgres-alternative.en.md) preserves full reports for every attempt. Adoption does not turn earlier findings into false positives: the Debian recovery image remains affected, and the API remains blocked. The matrix tracks the active database and keeps a separate Bookworm rollback target. Zero findings is a dated Trivy result, not a permanent guarantee.

## Protecting the data

This was a logical migration: custom-format pg_dump without owner/ACL, followed by pg_restore into an empty volume, in one transaction and stopping on errors. Alpine never opened Debian PGDATA. Both run PostgreSQL 17, but libc/glibc changes to musl, UID 999 to 70, and libc/en_US.utf8 locale to ICU/en-US/UTF8.

Writes were paused for every backup and switch: the Compose API was stopped; Kubernetes API replicas were set to zero and their Pods were allowed to terminate. In this lab the API is the only external writer. Local administrative access remained available. Global credentials were not blindly restored; the hook recreated accounts with existing privilege restrictions and limits.

Private backups live under `security-lab/.local/postgres-adoption/`: source dumps, reverse dumps, recovery configurations and row comparisons. Git ignores this directory. Public reports include hashes and results without note contents or passwords. Original volumes remain retained. This does not cover losing the machine or replace an external backup copy.

Docker's active volume is `docker-lab_pgdata_alpine_v1`; original `docker-lab_pgdata` is intact. Kubernetes uses `data-postgres-alpine-0`; `data-postgres-0` keeps its original UID. StatefulSet `postgres` has zero replicas; `postgres-alpine` receives connections through stable Service `postgres`. The old database is outside the active selector.

## The application actually exercised rollback

In each lab we created a controlled note after the first Alpine cutover. We paused writes again, dumped current state and restored into **another empty Debian volume**. Every note field and the identity sequence state matched. We then connected the real API to Debian and read the note created after migration.

After returning to Alpine we removed only the controlled note. All pre-existing rows matched at the end. Tests can advance the sequence; it is not rewound. Database container/Pod replacement also preserved the data. The original live databases were empty during this run; the earlier seven-Unicode-note test and this post-cutover write test complement that scenario without pretending user data existed.

Restored rollback volumes are retained too. The temporary Kubernetes rollback StatefulSet ends with zero replicas, outside Argo CD management; its actual name is recorded in private `kubernetes-state.json`. No existing environment was cleaned up using volume deletion.

## Repeating adoption on a still-Debian copy

The [operation script](../scripts/adopt-postgres.py) supports these sibling portfolio checkouts with already-hardened accounts and the existing Argo CD `notes` application. It is not a general migration tool. Run from the directory containing `docker-lab`, `kubernetes-lab` and `security-lab`:

```bash
python3 security-lab/scripts/adopt-postgres.py snapshot
python3 security-lab/scripts/adopt-postgres.py docker
python3 security-lab/scripts/adopt-postgres.py kubernetes
```

Snapshot creation refuses to overwrite an existing snapshot. Stages reject an already-switched source or an existing destination; do not repeat adoption on the migrated labs. The script saves source configuration and pauses writes. Private configuration files support recovery from an interrupted stage. Errors stop the operation without deleting volumes or automatically resuming writes.

The Kubernetes stage pauses Argo automation before modifying live resources. After testing, publish the updated `argocd-lab/workloads/notes/postgres.yaml`, inspect rendered `workloads/notes-traced`, then restore `automated: {prune: false, selfHeal: true}`. The instrumented API and observability destinations stay unchanged. Applying the Kubernetes repository alone does not update Argo's Git source.

New Compose installations use the approved digest and an Alpine volume directly. The wrapper rejects an automatic switch when it recognizes the original Debian volume. Kubernetes bootstrap also refuses to proceed while the old StatefulSet is active. Existing installations need the migration rather than expecting `up` to perform it.

## Recovery after more writes

Retained dumps have a timestamp. Pointing the API back to the original volume later would discard writes made only on Alpine. For a future rollback, pause writes, take a **new dump of current Alpine**, restore into a **new empty Debian volume**, compare rows, schema, relevant permissions and sequence, then switch the application's destination. Verify readiness and reads before allowing writes. Reassess the return locale if text-dependent queries/indexes or new extensions are introduced.

Private Docker files `docker-target-compose.json` and `docker-rollback-compose.json` record the tested configurations. Each configuration was operated with:

```bash
bash docker-lab/scripts/compose.sh -p docker-lab -f PRIVATE_CONFIG_PATH up -d --no-build --wait
```

Do not use the old rollback file to accept current writes: it is a rehearsal snapshot. For a permanent rollback also update default Compose to the restored image and volume before normal operation; default `up` must not reconnect the API to stale Alpine data.

For Kubernetes, pause Argo, scale the API to zero, restore into a new PVC using Debian image/UID, and change Service `postgres` selector to that database. Update Git to the chosen destination before restoring self-heal. Image `rollout undo` cannot convert data directories or replace logical restoration.

Public results: [Docker](../evidence/postgres-adoption/docker.json), [Kubernetes](../evidence/postgres-adoption/kubernetes.json). Additional API, privilege, GitOps and scanner evidence accompanies that directory. Earlier reports remain in their historical directories.

## Integration checks

The active image still has zero findings in the recorded full remote scan. Docker passed 23 API and 20 privilege/resource checks; Kubernetes passed 20 privilege/security checks. Argo self-heal corrected two replica drifts while preserving the active PVC and test note. Logging passed 16 checks and tracing 19. Alloy discovery and the PostgreSQL dashboard query now include `notes-db-alpine` and retain `notes-db` history; the logging test selects the active database through the Service. The standalone GHCR demo remains on its earlier image and is outside this two-lab cutover.
