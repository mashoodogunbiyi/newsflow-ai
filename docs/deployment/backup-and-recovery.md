# NewsFlow AI backup and recovery guide

## 1. Status and safety statement

NewsFlow AI does not currently have a production backup system or completed production restore exercise. The controls in this document are a proposed minimum for selecting and configuring an approved hosting environment. They must be implemented, tested, and approved before production release.

A local Docker named volume is persistent development storage. It is not a backup.

## 2. Recovery objectives

The following are proposed planning targets, not measured service commitments:

| Objective | Proposed target | Status |
| --- | --- | --- |
| PostgreSQL recovery point objective | No more than 24 hours of committed data loss, with point-in-time recovery preferred | Pending product, technical, privacy, and cost approval |
| PostgreSQL recovery time objective | Restore core authenticated read and write service within 8 hours | Pending platform selection and restore proof |
| Private image recovery point objective | No more than 24 hours for approved retained objects | Pending object-storage adapter and policy approval |
| Private image recovery time objective | Restore owner-authorised image delivery within 12 hours | Pending platform selection and restore proof |

Before deployment, accountable owners must either approve these values or replace them with measured, funded targets. A target is not achieved until an isolated recovery exercise demonstrates it.

## 3. Backup scope and proposed schedule

| Asset | Proposed method and frequency | Proposed retention | Important restrictions |
| --- | --- | --- | --- |
| PostgreSQL | Provider-managed encrypted backup every day; enable continuous point-in-time recovery where the approved provider supports it | 30 rolling days | Private network, least privilege, separate backup access, deletion tombstones reapplied after restore |
| Private image objects | Encrypted provider backup or versioning plus daily inventory and database-to-object reconciliation | Maximum 30 rolling days unless privacy and deletion policy approves another period | Public access blocked; do not keep deleted user objects indefinitely; shared references protected |
| Infrastructure and deployment definitions | Version-controlled repository plus immutable release metadata for every deployment | Repository history and approved release-record retention | Do not store secret values in configuration exports or release records |
| Managed secrets | Provider-managed protected recovery and rotation procedure | According to approved secret-store policy | Do not export plaintext secrets into application backups |
| Operational logs and audit exports | Access-controlled central storage with integrity and lifecycle controls | Use the approved security and privacy retention, not an unlimited default | Exclude article text, drafts, prompts, credentials, cookies, and private object keys |

The 30-day proposal aligns with the current deleted-draft content window but still requires privacy and legal approval. `GENERATION_USAGE_RETENTION_DAYS`, `GENERATION_AUDIT_RETENTION_DAYS`, `DRAFT_DELETION_RETENTION_DAYS`, and `DELETION_AUDIT_RETENTION_DAYS` govern live application records. Backup lifecycle controls must be designed so they do not silently defeat those policies.

## 4. Backup security controls

- Encrypt backups in transit and at rest with provider-managed or approved customer-managed keys.
- Use a dedicated backup identity that cannot run the application or read unrelated secrets.
- Restrict restore permission to named operational and security roles with strong authentication.
- Keep backup control-plane access separate from normal application administration where practical.
- Record backup creation, failure, access, export, restore, expiry, and deletion events.
- Prevent production backups from being restored into ordinary developer or CI environments.
- Use synthetic records for routine application tests.
- Do not include container images, `.env` files, plaintext secrets, temporary provider responses, or local caches as backup data.
- Monitor missed backups, capacity, expiry, and restore-test age.

## 5. Consistency model

PostgreSQL and private object storage do not share one atomic transaction. Recovery therefore requires reconciliation.

The database is the authoritative record of:

- User ownership.
- Active and deleted draft state.
- Selected image relationships.
- Image metadata and expected digest.
- Cleanup and retry status.
- Deletion tombstones and audit evidence.

Object storage holds private bytes only. An object without a valid owned database reference must not become accessible. A database record whose object is missing must return a controlled unavailable response and enter reconciliation; it must not expose a substitute or another user's object.

After restoring either system:

1. Block normal traffic and generation.
2. Compare database object references with a private storage inventory.
3. Verify key ownership, size, MIME type, and digest where available.
4. Mark missing objects unavailable and queue bounded recovery or cleanup work.
5. Quarantine or delete unreferenced objects according to the approved retention policy.
6. Reapply deletion tombstones and cleanup work that occurred after the restored recovery point.
7. Resume access only after owner isolation and deletion behavior are verified.

## 6. Backup verification

Automated backup status alone is not proof of recoverability.

### Daily automated review

- Latest backup or recovery point completed.
- Backup age and storage capacity are within the approved policy.
- No unexpected access, export, retention, or encryption change occurred.
- Required object inventory and reconciliation jobs completed.

### Quarterly isolated restore exercise

1. Select a recovery point approved for testing.
2. Restore into an isolated private environment with no public traffic or provider keys.
3. Use restricted operator access and record every action.
4. Apply the application migrations expected by the selected release.
5. Verify users, ownership, article provenance, rights, drafts, history, audit, and deletion state.
6. Restore or reconcile approved image objects.
7. Reapply deletion tombstones before allowing any content access.
8. Run authentication, cross-user isolation, content lifecycle, and safe logging checks.
9. Measure actual recovery point and recovery time.
10. Destroy the temporary restored environment according to policy.
11. Record result, defects, owners, and deadlines without copying private content into the report.

Also run a restore exercise after a material database, storage, encryption, backup-provider, or deletion-policy change.

## 7. Recovery decision

Restoration can overwrite or omit newer records. Before recovery, the incident commander and data owner must record:

- Incident and affected environment.
- Whether confidentiality, integrity, availability, rights, or deletion is affected.
- Last known good time and selected recovery point.
- Estimated data loss and user impact.
- Whether current data must be preserved for investigation.
- Database and storage consistency plan.
- Deletion-tombstone reapplication plan.
- Approver and operators.
- Communication and regulatory review requirements.

Do not restore solely because an application release failed. Use an application rollback when the schema is compatible. Use recovery only for data or platform failure with explicit impact approval.

## 8. PostgreSQL recovery procedure

Provider-specific commands must be added after a managed PostgreSQL service is selected.

1. Declare the incident, stop writes, disable scheduled work, and preserve safe evidence.
2. Confirm the failure is not a temporary connection, credential, TLS, capacity, or migration issue.
3. Select an approved recovery point and record the expected data-loss window.
4. Restore to a new isolated database instance rather than overwriting the failed instance first.
5. Restrict network access to recovery operators and the verification application.
6. Verify PostgreSQL version, required extensions, roles, encryption, and migration revision.
7. Run `alembic current`; apply only reviewed forward migrations needed by the selected application image.
8. Reconcile deletion tombstones, sessions, generation reservations, sync leases, retention jobs, and cleanup state.
9. Verify counts and representative relationships without exporting private content.
10. Run `/ready`, authentication, owner isolation, article rights, saved-draft, image, deletion, and audit checks.
11. Reconcile image storage as described in section 5.
12. Obtain accountable approval before changing the application connection to the restored database.
13. Observe the service during the recovery watch period and preserve the old instance until evidence and retention rules allow disposal.

## 9. Private image recovery procedure

This procedure cannot be executed until the approved production adapter and storage provider exist.

1. Disable image generation, regeneration, download, and cleanup changes as required.
2. Preserve PostgreSQL metadata and take a private object inventory.
3. Restore the selected object version set into a quarantined private location.
4. Compare each candidate with the active database reference and expected digest, MIME type, and size.
5. Do not restore an object for a deleted draft unless the deletion and backup policy explicitly requires temporary restricted processing.
6. Never make the recovery bucket or objects public.
7. Move only validated, still-referenced objects into the active private namespace.
8. Queue missing or inconsistent references for controlled user-facing unavailability and operator review.
9. Verify one user cannot retrieve another user's image.
10. Resume image operations only after reconciliation and approval.

## 10. Recovery by scenario

| Scenario | Recovery approach |
| --- | --- |
| Application image defect | Roll back to the previous compatible immutable image; do not restore data by default. |
| Failed migration | Stop traffic, inspect transaction state, prefer a forward fix, and use a rehearsed recovery point only when necessary. |
| Database loss or corruption | Restore PostgreSQL to an isolated instance, verify, reconcile storage and deletions, then cut over. |
| Storage loss or corruption | Keep draft text available where safe, mark images unavailable, restore to quarantine, validate, and reconcile. |
| Secret compromise | Revoke and rotate; do not restore an old secret from backup. |
| Accidental user-content deletion | Follow the approved deletion and privacy policy. Backups are not a normal user-facing undelete service. |
| Region or hosting outage | Use the selected platform's reviewed recovery design; none is currently implemented. |
| Unauthorised source ingestion | Disable ingestion, isolate affected records, preserve rights evidence, and obtain legal and product direction before reuse or deletion. |

## 11. Restore verification checklist

- Correct environment and approved application image.
- Expected PostgreSQL and Alembic versions.
- `/health` and `/ready` succeed without sensitive details.
- Authentication and secure cookie behavior work.
- Cross-user database and image access is denied.
- Article provenance and current rights restrictions are intact.
- Deleted content is not active after tombstone reapplication.
- Saved draft, version, export, and deletion operations work on synthetic verification data.
- Object digest, MIME, size, and owner checks pass.
- Provider modes remain disabled unless separately approved.
- Safe logs and monitoring work.
- Actual recovery point, recovery time, defects, and approvers are recorded.

## 12. Backup and restore evidence record

For every exercise or incident, record:

- Environment and exercise or incident identifier.
- Date, start time, end time, and operators.
- Approved recovery target and actual recovery point.
- Backup identifier without embedding credentials or private paths.
- Application image and migration revision.
- Database and object-storage steps performed.
- Deletion and ownership checks.
- Measured recovery point and recovery time.
- Verification results.
- Defects, residual risks, owners, and target dates.
- Approval to destroy the temporary recovery environment or resume service.

## 13. Known limitations and release gates

- No production backup provider, storage adapter, or recovery environment has been selected.
- The proposed objectives, schedule, and retention have not been approved or measured.
- No production backup has been created.
- No isolated production-like restore has passed.
- No automated deletion-tombstone replay or cross-system inventory process has been implemented for production.
- Disaster recovery across regions is not designed.
- Production release remains No-Go until these controls are implemented and proven.

## 14. Related documents

- [Deployment guide](deployment-guide.md)
- [Operations runbook](operations-runbook.md)
- [Content deletion and retention](../content-deletion-retention.md)
- [Reliability and recovery](../reliability-and-recovery.md)
- [Security threat model](../security-threat-model.md)
