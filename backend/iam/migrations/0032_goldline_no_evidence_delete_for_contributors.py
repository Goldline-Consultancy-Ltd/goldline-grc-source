"""Goldline v4.1.1-goldline.12 (R-IAM-03; Director, 22 Nov 2026): contributors cannot delete evidence.

Removes delete_evidence and delete_evidencerevision from the stored built-in Analyst (the role client
contributors hold), third-party respondent and auditee roles. The start-up handler re-syncs built-in roles
from core/startup.py, whose lists no longer carry these permissions, so this migration only makes the change
take effect before the first start and records it in the migration history.

Idempotent: removing a permission a role does not hold is a no-op, and a missing role or permission (a fresh
database, where permissions are created after migrations) is skipped. Reversible: the reverse adds the two
permissions back to the same roles (it restores the upstream defaults; the start-up handler would then remove
them again unless core/startup.py is reverted too).
"""

from django.db import migrations

ROLES = ("BI-RL-ANA", "BI-RL-TPR", "BI-RL-ADE")
PERMISSIONS = ("delete_evidence", "delete_evidencerevision")


def _targets(apps):
    Role = apps.get_model("iam", "Role")
    Permission = apps.get_model("auth", "Permission")
    perms = list(Permission.objects.filter(content_type__app_label="core", codename__in=PERMISSIONS))
    roles = list(Role.objects.filter(name__in=ROLES, builtin=True))
    return roles, perms


def remove_evidence_delete(apps, schema_editor):
    roles, perms = _targets(apps)
    for role in roles:
        if perms:
            role.permissions.remove(*perms)


def restore_evidence_delete(apps, schema_editor):
    roles, perms = _targets(apps)
    for role in roles:
        if perms:
            role.permissions.add(*perms)


class Migration(migrations.Migration):
    dependencies = [
        ("iam", "0031_remove_iam_is_published_fields"),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("core", "0195_compliance_assessment_computed_values"),
    ]

    operations = [migrations.RunPython(remove_evidence_delete, restore_evidence_delete)]
