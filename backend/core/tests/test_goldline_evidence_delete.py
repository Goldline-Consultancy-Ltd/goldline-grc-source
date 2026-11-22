"""Goldline v4.1.1-goldline.12: only administrators and domain managers delete evidence (R-IAM-03).

A contributor (built-in Analyst, the role the client contributor holds), a reader, the Goldline auditor, a
third-party respondent and an auditee cannot delete evidence, an evidence revision or an evidence file, by any
endpoint; domain managers (own domain only) and administrators still can. Two domains, A and B, prove that a
contributor or domain manager in B cannot delete A's evidence. Every test builds its own users and domains in the
test database; nothing here touches a real instance.
"""

import importlib
import uuid

import pytest
from django.apps import apps as django_apps
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from knox.models import AuthToken
from rest_framework.test import APIClient

from core.apps import startup
from core.goldline_evidence_delete import (
    EVIDENCE_DELETE_PERMISSIONS,
    ROLES_WITHOUT_EVIDENCE_DELETE,
    may_delete_evidence,
)
from core.models import Evidence, EvidenceRevision
from core.utils import RoleCodename
from global_settings.models import GlobalSettings
from iam.models import Folder, Role, RoleAssignment, User, UserGroup

PASSWORD = "Correct-Horse-Battery-9"
MIGRATION = importlib.import_module("iam.migrations.0032_goldline_no_evidence_delete_for_contributors")


@pytest.fixture
def app_config():
    startup(sender=None, **{})
    general, _ = GlobalSettings.objects.get_or_create(name=GlobalSettings.Names.GENERAL, defaults={"value": {}})
    value = dict(general.value or {})
    value["enforce_mfa"] = False
    general.value = value
    general.save()


def _client(user) -> APIClient:
    client = APIClient()
    _, token = AuthToken.objects.create(user=user)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    return client


def _domain(name):
    return Folder.objects.create(
        name=f"{name}-{uuid.uuid4().hex[:6]}",
        parent_folder=Folder.get_root_folder(),
        content_type=Folder.ContentType.DOMAIN,
    )


def _user_with(role_name, domain, label):
    user = User.objects.create_user(email=f"{label}-{uuid.uuid4().hex[:6]}@tests.com", password=PASSWORD)
    ra = RoleAssignment.objects.create(
        user=user, role=Role.objects.get(name=role_name), folder=Folder.get_root_folder(), is_recursive=False
    )
    ra.perimeter_folders.add(domain)
    return user


def _evidence(domain, tag="ev"):
    evidence = Evidence.objects.create(name=f"{tag}-{uuid.uuid4().hex[:6]}", folder=domain)
    revision = EvidenceRevision.objects.create(
        evidence=evidence, attachment=SimpleUploadedFile(f"{tag}.txt", b"evidence text\n", content_type="text/plain")
    )
    return evidence, revision


def _alive(evidence, revision):
    revision = EvidenceRevision.objects.filter(id=revision.id).first()
    return (
        Evidence.objects.filter(id=evidence.id).exists(),
        revision is not None,
        bool(revision and revision.attachment and revision.attachment.storage.exists(revision.attachment.name)),
    )


def _try_every_delete(client, domain):
    """Every evidence delete path, each on fresh evidence. Returns {path: (status, (evidence, revision, file) alive)}."""
    out = {}
    e, r = _evidence(domain, "rest")
    out["DELETE evidences/{id}/"] = (client.delete(f"/api/evidences/{e.id}/").status_code, _alive(e, r))
    e, r = _evidence(domain, "rev")
    out["DELETE evidence-revisions/{id}/"] = (client.delete(f"/api/evidence-revisions/{r.id}/").status_code, _alive(e, r))
    e, r = _evidence(domain, "file")
    out["POST evidence-revisions/{id}/delete_attachment/"] = (
        client.post(f"/api/evidence-revisions/{r.id}/delete_attachment/").status_code,
        _alive(e, r),
    )
    e, r = _evidence(domain, "batch")
    resp = client.post("/api/evidences/batch-action/", {"action": "delete", "ids": [str(e.id)]}, format="json")
    out["POST evidences/batch-action/ delete"] = (
        200 if resp.status_code == 200 and resp.json().get("succeeded") else 403,
        _alive(e, r),
    )
    e, r = _evidence(domain, "batchrev")
    resp = client.post("/api/evidence-revisions/batch-action/", {"action": "delete", "ids": [str(r.id)]}, format="json")
    out["POST evidence-revisions/batch-action/ delete"] = (
        200 if resp.status_code == 200 and resp.json().get("succeeded") else 403,
        _alive(e, r),
    )
    return out


def _assert_all_refused(results, who):
    for path, (code, alive) in results.items():
        assert code in (403, 404), f"{who}: {path} answered {code}"
        assert alive == (True, True, True), f"{who}: {path} removed something {alive}"


@pytest.fixture
def two_domains(app_config):
    a, b = _domain("ctb-a"), _domain("ctb-b")
    for d in (a, b):
        Folder.create_default_ug_and_ra(d)  # the per-domain built-in groups the screens use
    return a, b


@pytest.mark.django_db
class TestRoleDefinitions:
    def test_contributor_like_roles_hold_no_evidence_delete(self, app_config):
        for name in ROLES_WITHOUT_EVIDENCE_DELETE + (
            RoleCodename.READER.value,
            RoleCodename.APPROVER.value,
            RoleCodename.GOLDLINE_AUDITOR.value,
        ):
            granted = set(Role.objects.get(name=name).permissions.values_list("codename", flat=True))
            assert not granted & set(EVIDENCE_DELETE_PERMISSIONS), name

    def test_contributor_keeps_add_and_change(self, app_config):
        granted = set(Role.objects.get(name=RoleCodename.ANALYST.value).permissions.values_list("codename", flat=True))
        assert {"add_evidence", "change_evidence", "add_evidencerevision", "change_evidencerevision"} <= granted

    def test_administrator_and_domain_manager_keep_delete(self, app_config):
        for name in (RoleCodename.ADMINISTRATOR.value, RoleCodename.DOMAIN_MANAGER.value):
            granted = set(Role.objects.get(name=name).permissions.values_list("codename", flat=True))
            assert set(EVIDENCE_DELETE_PERMISSIONS) <= granted, name

    def test_startup_resync_does_not_bring_delete_back(self, app_config):
        startup(sender=None, **{})
        granted = set(Role.objects.get(name=RoleCodename.ANALYST.value).permissions.values_list("codename", flat=True))
        assert "delete_evidence" not in granted


@pytest.mark.django_db
class TestContributorRefused:
    def test_contributor_refused_on_every_delete_path(self, two_domains):
        a, _ = two_domains
        _assert_all_refused(_try_every_delete(_client(_user_with("BI-RL-ANA", a, "ctb")), a), "contributor")

    def test_contributor_rest_delete_is_403(self, two_domains):
        a, _ = two_domains
        client = _client(_user_with("BI-RL-ANA", a, "ctb"))
        e, r = _evidence(a)
        assert client.get(f"/api/evidences/{e.id}/").status_code == 200  # it can see it
        assert client.delete(f"/api/evidences/{e.id}/").status_code == 403
        assert client.delete(f"/api/evidence-revisions/{r.id}/").status_code == 403
        assert client.post(f"/api/evidence-revisions/{r.id}/delete_attachment/").status_code == 403
        assert _alive(e, r) == (True, True, True)

    def test_contributor_still_adds_evidence(self, two_domains):
        a, _ = two_domains
        client = _client(_user_with("BI-RL-ANA", a, "ctb"))
        resp = client.post("/api/evidences/", {"name": f"ctb add {uuid.uuid4().hex[:6]}", "folder": str(a.id)}, format="json")
        assert resp.status_code == 201, resp.content

    def test_refused_even_if_the_role_is_misconfigured(self, two_domains):
        """Delete rights added back to the Analyst role: the server-side check still refuses."""
        a, _ = two_domains
        analyst = Role.objects.get(name="BI-RL-ANA")
        analyst.permissions.add(*Permission.objects.filter(codename__in=EVIDENCE_DELETE_PERMISSIONS))
        _assert_all_refused(_try_every_delete(_client(_user_with("BI-RL-ANA", a, "ctb")), a), "misconfigured contributor")

    def test_custom_role_with_delete_rights_refused(self, two_domains):
        a, _ = two_domains
        custom = Role.objects.create(name=f"custom-{uuid.uuid4().hex[:6]}", folder=Folder.get_root_folder())
        custom.permissions.set(
            Permission.objects.filter(codename__in=("view_evidence", "view_evidencerevision", "view_folder") + EVIDENCE_DELETE_PERMISSIONS)
        )
        _assert_all_refused(_try_every_delete(_client(_user_with(custom.name, a, "custom")), a), "custom role")

    @pytest.mark.parametrize(
        "role",
        ["BI-RL-AUD", "BI-RL-APP", RoleCodename.GOLDLINE_AUDITOR.value, "BI-RL-TPR", "BI-RL-ADE"],
    )
    def test_other_roles_refused(self, two_domains, role):
        a, _ = two_domains
        _assert_all_refused(_try_every_delete(_client(_user_with(role, a, "other")), a), role)


@pytest.mark.django_db
class TestAllowedRolesStillDelete:
    def test_domain_manager_deletes_on_every_path(self, two_domains):
        a, _ = two_domains
        results = _try_every_delete(_client(_user_with("BI-RL-DMA", a, "dm")), a)
        assert results["DELETE evidences/{id}/"] == (204, (False, False, False))
        assert results["DELETE evidence-revisions/{id}/"][0] == 204
        assert results["DELETE evidence-revisions/{id}/"][1][1:] == (False, False)
        assert results["POST evidence-revisions/{id}/delete_attachment/"] == (200, (True, True, False))
        assert results["POST evidences/batch-action/ delete"] == (200, (False, False, False))
        assert results["POST evidence-revisions/batch-action/ delete"][0] == 200

    def test_administrator_deletes(self, two_domains):
        a, _ = two_domains
        admin = User.objects.create_user(email=f"adm-{uuid.uuid4().hex[:6]}@tests.com", password=PASSWORD)
        admin.user_groups.add(UserGroup.objects.get(name="BI-UG-ADM"))
        client = _client(admin)
        e, r = _evidence(a)
        assert client.delete(f"/api/evidences/{e.id}/").status_code == 204
        assert _alive(e, r) == (False, False, False)

    def test_domain_group_membership_counts(self, two_domains):
        """A domain manager through the domain's built-in group (how the screens assign it)."""
        a, _ = two_domains
        user = User.objects.create_user(email=f"dmg-{uuid.uuid4().hex[:6]}@tests.com", password=PASSWORD)
        group = UserGroup.objects.get(folder=a, name="BI-UG-DMA")
        user.user_groups.add(group)
        e, r = _evidence(a)
        assert _client(user).delete(f"/api/evidences/{e.id}/").status_code == 204

    def test_contributor_group_membership_refused(self, two_domains):
        a, _ = two_domains
        user = User.objects.create_user(email=f"anag-{uuid.uuid4().hex[:6]}@tests.com", password=PASSWORD)
        user.user_groups.add(UserGroup.objects.get(folder=a, name="BI-UG-ANA"))
        _assert_all_refused(_try_every_delete(_client(user), a), "contributor by group")


@pytest.mark.django_db
class TestTenancy:
    def test_contributor_in_b_cannot_delete_a(self, two_domains):
        a, b = two_domains
        client = _client(_user_with("BI-RL-ANA", b, "ctb-b"))
        _assert_all_refused(_try_every_delete(client, a), "contributor in B on A")

    def test_domain_manager_in_b_cannot_delete_a(self, two_domains):
        a, b = two_domains
        client = _client(_user_with("BI-RL-DMA", b, "dm-b"))
        _assert_all_refused(_try_every_delete(client, a), "domain manager in B on A")

    def test_check_is_per_domain(self, two_domains):
        a, b = two_domains
        dm_a = _user_with("BI-RL-DMA", a, "dm-a")
        assert may_delete_evidence(dm_a, a) is True
        assert may_delete_evidence(dm_a, b) is False
        assert may_delete_evidence(dm_a, None) is False
        assert may_delete_evidence(_user_with("BI-RL-ANA", a, "ctb-a"), a) is False

    def test_inactive_domain_manager_refused(self, two_domains):
        a, _ = two_domains
        dm = _user_with("BI-RL-DMA", a, "dm-off")
        dm.is_active = False
        dm.save()
        assert may_delete_evidence(dm, a) is False


@pytest.mark.django_db
class TestMigration:
    def _perms(self, name):
        return set(Role.objects.get(name=name).permissions.values_list("codename", flat=True))

    def test_forward_removes_and_is_idempotent_reverse_restores(self, app_config):
        targets = Permission.objects.filter(codename__in=EVIDENCE_DELETE_PERMISSIONS)
        for name in MIGRATION.ROLES:
            Role.objects.get(name=name).permissions.add(*targets)  # the state before goldline.12
        MIGRATION.remove_evidence_delete(django_apps, None)
        MIGRATION.remove_evidence_delete(django_apps, None)  # second run changes nothing
        for name in MIGRATION.ROLES:
            assert not self._perms(name) & set(EVIDENCE_DELETE_PERMISSIONS), name
        assert set(EVIDENCE_DELETE_PERMISSIONS) <= self._perms("BI-RL-DMA")
        assert set(EVIDENCE_DELETE_PERMISSIONS) <= self._perms("BI-RL-ADM")
        MIGRATION.restore_evidence_delete(django_apps, None)
        for name in MIGRATION.ROLES:
            assert set(EVIDENCE_DELETE_PERMISSIONS) <= self._perms(name), name
        MIGRATION.remove_evidence_delete(django_apps, None)
        assert not self._perms("BI-RL-ANA") & set(EVIDENCE_DELETE_PERMISSIONS)

    def test_migration_roles_match_the_module(self):
        assert tuple(MIGRATION.ROLES) == ROLES_WITHOUT_EVIDENCE_DELETE
        assert tuple(MIGRATION.PERMISSIONS) == EVIDENCE_DELETE_PERMISSIONS
