"""Goldline v4.1.1-goldline.8/9: evidence uploads are refused by content (executables, archives, mismatched type) and over 25 MB.

TC-SR-027 (executable) and TC-SR-028 (over the size limit) test the same through the API on the test copy.
"""

import io
import tarfile
import zipfile

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from iam.models import Folder, User, UserGroup
from knox.models import AuthToken
from rest_framework import status
from rest_framework.test import APIClient

from core.apps import startup
from core.goldline_uploads import EVIDENCE_MAX_BYTES, check_evidence_upload
from core.models import Evidence, EvidenceRevision

def _zip(members: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in members.items():
            zf.writestr(name, data)
    return buf.getvalue()


def _tar() -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tf:
        info = tarfile.TarInfo("notes.txt")
        info.size = 5
        tf.addfile(info, io.BytesIO(b"hello"))
    return buf.getvalue()


DOCX = _zip({"[Content_Types].xml": b"<Types/>", "word/document.xml": b"<w:document/>"})
ODT = _zip({"mimetype": b"application/vnd.oasis.opendocument.text", "content.xml": b"<office/>"})
PLAIN_ZIP = _zip({"notes.txt": b"hello"})

EXECUTABLES = {
    "windows": b"MZ" + b"\x00" * 510,
    "linux": b"\x7fELF\x02\x01\x01" + b"\x00" * 64,
    "macos-64": b"\xcf\xfa\xed\xfe" + b"\x00" * 64,
    "macos-32": b"\xce\xfa\xed\xfe" + b"\x00" * 64,
    "macos-fat-or-java-class": b"\xca\xfe\xba\xbe" + b"\x00" * 64,
    "webassembly": b"\x00asm\x01\x00\x00\x00",
    "windows-shortcut": b"L\x00\x00\x00\x01\x14\x02\x00" + b"\x00" * 64,
    "shell-script": b"#!/bin/sh\necho hello\n",
    "python-script": b"#!/usr/bin/env python3\nprint(1)\n",
}

GOOD = {
    "report.pdf": (b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n", "application/pdf"),
    "chart.png": (b"\x89PNG\r\n\x1a\n" + b"\x00" * 16, "image/png"),
    "photo.jpg": (b"\xff\xd8\xff\xe0" + b"\x00" * 16, "image/jpeg"),
    "notes.txt": (b"Access review completed.\n", "text/plain"),
    "users.csv": (b"name,role\nalice,admin\n", "text/csv"),
    "policy.docx": (DOCX, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
    "minutes.odt": (ODT, "application/vnd.oasis.opendocument.text"),
    "legacy.xls": (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 16, "application/vnd.ms-excel"),
    "config.yaml": (b"key: value\n", "application/x-yaml"),
    "empty.txt": (b"", "text/plain"),
}


def _file(name, content, content_type="application/octet-stream"):
    return SimpleUploadedFile(name, content, content_type=content_type)


class TestCheckEvidenceUpload:
    @pytest.mark.parametrize("kind", sorted(EXECUTABLES))
    def test_executables_refused_by_content_whatever_the_name(self, kind):
        for name in ("evidence.txt", "evidence.pdf", "evidence.log"):
            with pytest.raises(ValidationError):
                check_evidence_upload(_file(name, EXECUTABLES[kind]))

    @pytest.mark.parametrize("name", sorted(GOOD))
    def test_ordinary_evidence_accepted(self, name):
        content, content_type = GOOD[name]
        check_evidence_upload(_file(name, content, content_type))

    @pytest.mark.parametrize(
        "name,content",
        [
            ("report.pdf", b"\x89PNG\r\n\x1a\n" + b"\x00" * 16),  # a PNG called .pdf
            ("chart.png", b"%PDF-1.7\n"),  # a PDF called .png
            ("policy.docx", b"plain text, not a document"),
            ("notes.txt", b"text\x00with a NUL byte"),
            ("notes.txt", b"%PDF-1.7\n"),  # a PDF called .txt
            ("data.csv", b"PK\x03\x04" + b"\x00" * 26),  # an archive called .csv
            ("clip.mp4", b"not a video at all"),
        ],
    )
    def test_content_must_match_the_name(self, name, content):
        with pytest.raises(ValidationError):
            check_evidence_upload(_file(name, content))

    @pytest.mark.parametrize(
        "name,content",
        [
            ("bundle.zip", PLAIN_ZIP),
            ("bundle.7z", b"7z\xbc\xaf\x27\x1c" + b"\x00" * 32),
            ("bundle.rar", b"Rar!\x1a\x07\x01\x00" + b"\x00" * 32),
            ("bundle.tar", _tar()),
            ("bundle.gz", b"\x1f\x8b\x08\x00" + b"\x00" * 32),
            ("bundle.tgz", b"\x1f\x8b\x08\x00" + b"\x00" * 32),
            ("bundle.bz2", b"BZh91AY&SY" + b"\x00" * 32),
            ("bundle.xz", b"\xfd7zXZ\x00" + b"\x00" * 32),
            ("bundle.zst", b"\x28\xb5\x2f\xfd" + b"\x00" * 32),
            ("empty.zip", b""),
        ],
    )
    def test_archives_refused_by_name(self, name, content):
        with pytest.raises(ValidationError, match="rchive"):
            check_evidence_upload(_file(name, content))

    @pytest.mark.parametrize(
        "content",
        [
            PLAIN_ZIP,
            _tar(),
            b"7z\xbc\xaf\x27\x1c" + b"\x00" * 32,
            b"Rar!\x1a\x07\x00" + b"\x00" * 32,
            b"\x1f\x8b\x08\x00" + b"\x00" * 32,
            b"BZh91AY&SY" + b"\x00" * 32,
            b"\xfd7zXZ\x00" + b"\x00" * 32,
        ],
    )
    def test_archives_refused_by_content_whatever_the_name(self, content):
        for name in ("report.pdf", "notes.txt", "data.csv"):
            with pytest.raises(ValidationError, match="rchive"):
                check_evidence_upload(_file(name, content))

    def test_plain_zip_called_docx_refused(self):
        with pytest.raises(ValidationError, match="rchive"):
            check_evidence_upload(_file("policy.docx", PLAIN_ZIP))

    def test_declared_type_must_match_the_name(self):
        with pytest.raises(ValidationError):
            check_evidence_upload(_file("chart.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 16, "application/pdf"))

    def test_executable_declared_type_refused(self):
        with pytest.raises(ValidationError):
            check_evidence_upload(_file("notes.txt", b"harmless", "application/x-msdownload"))

    def test_over_25_mb_refused_and_25_mb_accepted(self):
        with pytest.raises(ValidationError):
            check_evidence_upload(_file("big.txt", b"A" * (EVIDENCE_MAX_BYTES + 1), "text/plain"))
        check_evidence_upload(_file("limit.txt", b"A" * EVIDENCE_MAX_BYTES, "text/plain"))

    def test_the_cursor_is_left_where_it_was(self):
        f = _file("notes.txt", b"hello")
        check_evidence_upload(f)
        assert f.read() == b"hello"


@pytest.fixture
def app_config():
    startup(sender=None)


@pytest.fixture
def client_and_folder(app_config, settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    admin = User.objects.create_superuser("admin@goldline-upload-tests.com")
    admin_group = UserGroup.objects.get(name="BI-UG-ADM")
    admin.folder = admin_group.folder
    admin.save()
    admin_group.user_set.add(admin)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {AuthToken.objects.create(user=admin)[1]}")
    root = Folder.objects.get(content_type=Folder.ContentType.ROOT)
    folder = Folder.objects.create(name="folder-goldline-uploads", parent_folder=root)
    return client, folder


@pytest.mark.django_db
class TestEvidenceUploadApi:
    def _post(self, client, folder, name, content, content_type):
        return client.post(
            "/api/evidences/",
            {"name": f"ev-{name}", "folder": str(folder.id), "attachment": _file(name, content, content_type)},
            format="multipart",
        )

    def test_executable_refused_tc_sr_027(self, client_and_folder):
        client, folder = client_and_folder
        r = self._post(client, folder, "run.exe", EXECUTABLES["windows"], "application/x-msdownload")
        assert r.status_code == status.HTTP_400_BAD_REQUEST
        assert not Evidence.objects.filter(name="ev-run.exe").exists()

    @pytest.mark.parametrize("kind", ["windows", "linux", "shell-script", "webassembly"])
    def test_renamed_executable_refused(self, client_and_folder, kind):
        client, folder = client_and_folder
        r = self._post(client, folder, "notes.txt", EXECUTABLES[kind], "text/plain")
        assert r.status_code == status.HTTP_400_BAD_REQUEST, kind
        assert not EvidenceRevision.objects.filter(evidence__folder=folder).exists()

    def test_mismatched_type_refused(self, client_and_folder):
        client, folder = client_and_folder
        r = self._post(client, folder, "report.pdf", GOOD["chart.png"][0], "application/pdf")
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_over_25_mb_refused_tc_sr_028(self, client_and_folder):
        client, folder = client_and_folder
        r = self._post(client, folder, "big.txt", b"A" * (EVIDENCE_MAX_BYTES + 1), "text/plain")
        assert r.status_code == status.HTTP_400_BAD_REQUEST
        assert not Evidence.objects.filter(name="ev-big.txt").exists()

    def test_archive_refused_with_a_clear_message(self, client_and_folder):
        client, folder = client_and_folder
        r = self._post(client, folder, "bundle.zip", PLAIN_ZIP, "application/zip")
        assert r.status_code == status.HTTP_400_BAD_REQUEST
        assert b"rchive" in r.content
        assert not Evidence.objects.filter(name="ev-bundle.zip").exists()

    def test_office_document_still_accepted(self, client_and_folder):
        client, folder = client_and_folder
        r = self._post(client, folder, "policy.docx", DOCX, GOOD["policy.docx"][1])
        assert r.status_code == status.HTTP_201_CREATED, r.content

    def test_ordinary_pdf_accepted(self, client_and_folder):
        client, folder = client_and_folder
        content, content_type = GOOD["report.pdf"]
        r = self._post(client, folder, "report.pdf", content, content_type)
        assert r.status_code == status.HTTP_201_CREATED, r.content
        revision = EvidenceRevision.objects.get(evidence__name="ev-report.pdf")
        assert revision.attachment.read() == content

    def test_raw_attachment_upload_refuses_an_executable(self, client_and_folder):
        client, folder = client_and_folder
        evidence = Evidence.objects.create(name="ev-raw", folder=folder)
        r = client.post(
            f"/api/evidences/{evidence.id}/upload/",
            data=EXECUTABLES["linux"],
            content_type="text/plain",
            HTTP_CONTENT_DISPOSITION='attachment; filename="notes.txt"',
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST
        ok = client.post(
            f"/api/evidences/{evidence.id}/upload/",
            data=b"%PDF-1.4 fine",
            content_type="application/pdf",
            HTTP_CONTENT_DISPOSITION='attachment; filename="fine.pdf"',
        )
        assert ok.status_code == status.HTTP_200_OK, ok.content

    def test_revision_upload_refuses_an_executable(self, client_and_folder):
        client, folder = client_and_folder
        evidence = Evidence.objects.create(name="ev-rev", folder=folder)
        r = client.post(
            "/api/evidence-revisions/",
            {"evidence": str(evidence.id), "attachment": _file("notes.txt", EXECUTABLES["shell-script"], "text/plain")},
            format="multipart",
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST
