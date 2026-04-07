"""SyncService — orchestrates controlled schema catalog synchronisation.

No real network I/O is performed in v1.  The service iterates the source
catalog, applies policy scope filters, and calls
target.import_synced_version() for each eligible schema version.

v2 Extension:
    Override _transfer_version() in a subclass to replace the direct
    target.import_synced_version() call with a network operation (REST,
    message queue, etc.).  The orchestration logic in run_sync() does not
    need to change.

Excluded from v1:
    - Network calls
    - Authentication for remote catalogs
    - Conflict resolution strategies (v1 records conflicts; v2 can add policies)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from packages.catalog.catalog_service import CatalogService
from packages.catalog.models.catalog_entry import CatalogEntry
from packages.catalog.models.schema_descriptor import ApprovalStatus, SchemaType
from packages.catalog.models.schema_version import SchemaVersion
from packages.catalog.models.sync import (
    SyncAction,
    SyncActionType,
    SyncJob,
    SyncJobStatus,
    SyncPolicy,
    SyncScope,
)
from packages.core.models.audit_event import AuditAction


class SyncService:
    """Simulated sync orchestrator for controlled central ↔ on-prem sync.

    Args:
        source: The catalog that is the origin of schemas for this sync.
        target: The catalog that receives schemas from this sync.
    """

    def __init__(self, source: CatalogService, target: CatalogService) -> None:
        self._source = source
        self._target = target

    def run_sync(self, policy: SyncPolicy, actor: str) -> SyncJob:
        """Execute a sync job according to *policy*.

        Iterates all entries in the source catalog, applies the policy scope
        filter, and transfers eligible versions to the target catalog.

        Each transfer decision (add / skip / conflict / filter) is recorded
        as a SyncAction on the returned SyncJob.  Audit events are emitted
        to the target catalog's audit log.

        Args:
            policy: The SyncPolicy governing direction and scope.
            actor:  Identity of the user or scheduler that triggered the sync.

        Returns:
            A completed SyncJob with status COMPLETED (or FAILED on exception).
        """
        job = SyncJob(
            id=str(uuid.uuid4()),
            policy_id=policy.id,
            triggered_by=actor,
            started_at=datetime.now(timezone.utc).isoformat(),
            status=SyncJobStatus.RUNNING,
        )

        try:
            for entry in self._source.list_entries():
                if not self._scope_matches(entry, policy.scope):
                    for version in entry.versions:
                        job.actions.append(
                            SyncAction(
                                job_id=job.id,
                                action_type=SyncActionType.SCHEMA_FILTERED,
                                schema_id=entry.descriptor.id,
                                schema_name=entry.descriptor.name,
                                version_label=version.version_label,
                                details=(
                                    f"Excluded by scope={policy.scope.value}: "
                                    f"type={entry.descriptor.schema_type.value}, "
                                    f"approval={entry.descriptor.approval_status.value}"
                                ),
                            )
                        )
                    continue

                for version in entry.versions:
                    action = self._transfer_version(
                        job_id=job.id,
                        entry=entry,
                        version=version,
                        actor=actor,
                    )
                    job.actions.append(action)

            job.status = SyncJobStatus.COMPLETED

        except Exception:
            job.status = SyncJobStatus.FAILED
            raise

        finally:
            job.completed_at = datetime.now(timezone.utc).isoformat()

        # Emit a single audit event summarising the completed job
        added = sum(
            1 for a in job.actions
            if a.action_type == SyncActionType.SCHEMA_VERSION_ADDED
        )
        self._target._emit(  # noqa: SLF001 — intentional use of internal helper
            actor=actor,
            action=AuditAction.CATALOG_SYNC,
            object_type="sync_job",
            object_id=job.id,
            after={
                "policy_id": policy.id,
                "status": job.status.value,
                "total_actions": len(job.actions),
                "versions_added": added,
            },
        )

        return job

    # ------------------------------------------------------------------
    # v2 extension hook
    # ------------------------------------------------------------------

    def _transfer_version(
        self,
        job_id: str,
        entry: CatalogEntry,
        version: SchemaVersion,
        actor: str,
    ) -> SyncAction:
        """Transfer one schema version from source to target.

        Override this method in a subclass to replace local-copy transfer
        with a real network operation in v2.  The run_sync() orchestration
        loop does not need to change.

        Returns:
            A SyncAction recording the outcome.
        """
        outcome = self._target.import_synced_version(
            descriptor_dict=entry.descriptor.to_dict(),
            version=version,
            actor=actor,
        )
        action_map = {
            "added": SyncActionType.SCHEMA_VERSION_ADDED,
            "skipped": SyncActionType.SCHEMA_SKIPPED,
            "conflict": SyncActionType.SCHEMA_CONFLICT,
        }
        return SyncAction(
            job_id=job_id,
            action_type=action_map[outcome],
            schema_id=entry.descriptor.id,
            schema_name=entry.descriptor.name,
            version_label=version.version_label,
            details=f"transfer_outcome={outcome}",
        )

    # ------------------------------------------------------------------
    # Scope evaluation
    # ------------------------------------------------------------------

    @staticmethod
    def _scope_matches(entry: CatalogEntry, scope: SyncScope) -> bool:
        """Return True if *entry* is eligible under the given *scope*."""
        if scope == SyncScope.ALL:
            return True
        if scope == SyncScope.STANDARDS_ONLY:
            return entry.descriptor.schema_type == SchemaType.STANDARD
        if scope == SyncScope.CUSTOM_ONLY:
            return entry.descriptor.schema_type == SchemaType.CUSTOM
        if scope == SyncScope.APPROVED_ONLY:
            return entry.descriptor.approval_status == ApprovalStatus.APPROVED
        return False
