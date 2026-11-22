"""Goldline v4.1.1-goldline.12: who may delete evidence (R-IAM-03; Director, 22 Nov 2026).

Only administrators and domain managers may delete evidence, an evidence revision or an evidence file.
Contributors (built-in Analyst, the role client contributors hold), third-party respondents, auditees,
approvers, readers and auditors may not.

Two layers:
1. The role definitions (core/startup.py) no longer carry delete_evidence or delete_evidencerevision for
   the Analyst, third-party respondent and auditee roles, and migration iam 0032 removes them from the
   stored roles.
2. This module is a server-side check that does not trust the role definitions: every evidence delete
   path also asks `may_delete_evidence`, which allows only superusers, members of the global
   administrators group, and holders of the built-in Administrator or Domain manager role on the
   evidence's domain. A role misconfigured later (a custom role, or delete rights added back to the
   Analyst) still cannot delete evidence.
"""

from __future__ import annotations

from rest_framework import status
from rest_framework.response import Response

from core.utils import RoleCodename

# Roles that may delete evidence on the folders they cover.
EVIDENCE_DELETE_ROLES = frozenset({RoleCodename.ADMINISTRATOR.value, RoleCodename.DOMAIN_MANAGER.value})

# Permissions removed from every other built-in role that held them.
EVIDENCE_DELETE_PERMISSIONS = ("delete_evidence", "delete_evidencerevision")
ROLES_WITHOUT_EVIDENCE_DELETE = (
    RoleCodename.ANALYST.value,
    RoleCodename.THIRD_PARTY_RESPONDENT.value,
    RoleCodename.AUDITEE.value,
)

REFUSAL = {"detail": "You do not have permission to delete evidence."}


def refused() -> Response:
    return Response(REFUSAL, status=status.HTTP_403_FORBIDDEN)


def may_delete_evidence(user, folder) -> bool:
    """True only for a superuser, a global administrator, or a holder of an allowed role covering `folder`."""
    from iam.models import RoleAssignment, User

    if not isinstance(user, User) or not user.is_active or folder is None:
        return False
    if user.is_superuser or user.is_admin():
        return True
    assignments = RoleAssignment.get_role_assignments_from_user(user).filter(
        role__name__in=EVIDENCE_DELETE_ROLES, role__builtin=True
    )
    ancestor_ids = None
    for ra in assignments.prefetch_related("perimeter_folders"):
        ids = {f.id for f in ra.perimeter_folders.all()}
        if folder.id in ids:
            return True
        if ra.is_recursive and ids:
            if ancestor_ids is None:
                ancestor_ids = set(folder.ancestors.values_list("id", flat=True))
            if ids & ancestor_ids:
                return True
    return False


def may_delete_evidence_object(user, obj) -> bool:
    """Evidence or EvidenceRevision: checked on the folder that owns it (a revision's evidence folder)."""
    from iam.models import Folder

    folder = None
    evidence = getattr(obj, "evidence", None)
    if evidence is not None:
        folder = Folder.get_folder(evidence)
    if folder is None:
        folder = Folder.get_folder(obj)
    return may_delete_evidence(user, folder)
