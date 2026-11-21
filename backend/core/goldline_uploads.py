"""Goldline (v4.1.1-goldline.8): evidence uploads are checked by content, not only by file name.

Refused, whatever the file is called:
- executables and scripts: Windows (MZ), Linux (ELF), macOS (Mach-O, thin and fat), Java class files, WebAssembly,
  Windows shortcuts (.lnk) and any file that starts with "#!";
- content that does not match the declared type (the file name's extension, and the content type the client sent);
- files over 25 MB (the Director's limit, 20 Nov 2026, the same as the workspace).

Only a new upload is read; a file already stored is not read again.
"""

from __future__ import annotations

import mimetypes
import os

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile

EVIDENCE_MAX_BYTES = 25 * 1024 * 1024
_HEAD = 64 * 1024

_EXECUTABLE_SIGNATURES: tuple[tuple[bytes, str], ...] = (
    (b"MZ", "a Windows executable"),
    (b"\x7fELF", "a Linux executable"),
    (b"\xfe\xed\xfa\xce", "a macOS executable"),
    (b"\xfe\xed\xfa\xcf", "a macOS executable"),
    (b"\xce\xfa\xed\xfe", "a macOS executable"),
    (b"\xcf\xfa\xed\xfe", "a macOS executable"),
    (b"\xca\xfe\xba\xbe", "a macOS executable or Java class file"),
    (b"\xca\xfe\xba\xbf", "a macOS executable"),
    (b"\x00asm", "a WebAssembly module"),
    (b"L\x00\x00\x00\x01\x14\x02\x00", "a Windows shortcut"),
    (b"#!", "a script"),
)

_EXECUTABLE_CONTENT_TYPES = {
    "application/x-msdownload",
    "application/x-msdos-program",
    "application/x-dosexec",
    "application/vnd.microsoft.portable-executable",
    "application/x-executable",
    "application/x-elf",
    "application/x-mach-binary",
    "application/x-sharedlib",
    "application/x-sh",
    "application/x-shellscript",
    "text/x-shellscript",
    "application/x-csh",
    "application/x-perl",
    "text/x-perl",
    "text/x-python",
    "application/x-python-code",
    "application/java-vm",
    "application/x-java-applet",
    "application/java-archive",
    "application/x-java-archive",
    "application/wasm",
    "application/x-ms-shortcut",
    "application/x-bat",
    "application/x-msi",
    "application/x-ms-installer",
}

_OLE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
_ZIP = (b"PK\x03\x04", b"PK\x05\x06")
_MEDIA_BOXES = (b"ftyp", b"moov", b"mdat", b"wide", b"free", b"skip", b"pnot")

# Binary formats: the content must start with one of these (or match the check).
_BINARY_CHECKS = {
    "pdf": lambda h: h.startswith(b"%PDF-"),
    "png": lambda h: h.startswith(b"\x89PNG\r\n\x1a\n"),
    "jpg": lambda h: h.startswith(b"\xff\xd8\xff"),
    "jpeg": lambda h: h.startswith(b"\xff\xd8\xff"),
    "gif": lambda h: h.startswith((b"GIF87a", b"GIF89a")),
    "webp": lambda h: h[:4] == b"RIFF" and h[8:12] == b"WEBP",
    "docx": lambda h: h.startswith(_ZIP),
    "xlsx": lambda h: h.startswith(_ZIP),
    "pptx": lambda h: h.startswith(_ZIP),
    "odt": lambda h: h.startswith(_ZIP),
    "ods": lambda h: h.startswith(_ZIP),
    "zip": lambda h: h.startswith(_ZIP),
    "doc": lambda h: h.startswith(_OLE),
    "xls": lambda h: h.startswith(_OLE),
    "ppt": lambda h: h.startswith(_OLE),
    "msg": lambda h: h.startswith(_OLE),
    "7z": lambda h: h.startswith(b"7z\xbc\xaf\x27\x1c"),
    "gz": lambda h: h.startswith(b"\x1f\x8b"),
    "tar": lambda h: h[257:262] == b"ustar",
    "mp4": lambda h: h[4:8] in _MEDIA_BOXES,
    "mov": lambda h: h[4:8] in _MEDIA_BOXES,
}

# Text formats: no NUL byte and no binary signature in the first 64 KB.
_TEXT_EXTENSIONS = {"txt", "csv", "md", "json", "yaml", "yml", "toml", "xml", "log", "eml", "svg"}

_BINARY_MAGIC = (b"%PDF-", b"\x89PNG", b"\xff\xd8\xff", b"GIF8", *_ZIP, _OLE, b"7z\xbc\xaf", b"\x1f\x8b")

# A client-declared content type that names one of these formats must agree with the extension.
_STRICT_DECLARED = {
    "application/pdf": {"pdf"},
    "image/png": {"png"},
    "image/jpeg": {"jpg", "jpeg"},
    "image/gif": {"gif"},
    "image/webp": {"webp"},
    "video/mp4": {"mp4"},
    "video/quicktime": {"mov"},
    "application/zip": {"zip", "docx", "xlsx", "pptx", "odt", "ods"},
}


def _upload_of(value):
    """The new upload behind a validator value, or None when the file is already stored."""
    if isinstance(value, UploadedFile):
        return value
    if getattr(value, "_committed", True) is False:
        inner = getattr(value, "file", None)
        return inner if inner is not None else value
    return None


def _head(upload) -> bytes:
    pos = upload.tell() if hasattr(upload, "tell") else 0
    upload.seek(0)
    head = upload.read(_HEAD)
    upload.seek(pos)
    return head or b""


def check_evidence_upload(value) -> None:
    """Raise ValidationError when a new evidence file is too large, executable or not what it says it is."""
    upload = _upload_of(value)
    if upload is None:
        return

    size = getattr(upload, "size", None)
    if size is not None and size > EVIDENCE_MAX_BYTES:
        raise ValidationError("The file is larger than 25 MB, the maximum for evidence.")

    name = getattr(value, "name", None) or getattr(upload, "name", "") or ""
    extension = os.path.splitext(name)[1].lstrip(".").lower()
    declared = (getattr(upload, "content_type", None) or "").split(";")[0].strip().lower()
    head = _head(upload)

    if declared in _EXECUTABLE_CONTENT_TYPES:
        raise ValidationError("Executable files are not accepted as evidence.")
    for signature, what in _EXECUTABLE_SIGNATURES:
        if head.startswith(signature):
            raise ValidationError(f"The file looks like {what}; executable files are not accepted as evidence.")

    if declared in _STRICT_DECLARED and extension not in _STRICT_DECLARED[declared]:
        raise ValidationError("The file's declared type does not match its name.")

    if not head:
        return  # an empty file holds nothing to check
    check = _BINARY_CHECKS.get(extension)
    if check is not None:
        if not check(head):
            raise ValidationError(f"The file's content does not match its type (.{extension}).")
    elif extension in _TEXT_EXTENSIONS:
        if b"\x00" in head or head.startswith(_BINARY_MAGIC):
            raise ValidationError(f"The file's content does not match its type (.{extension}).")
    else:
        guessed = mimetypes.guess_type(name)[0]
        if guessed is None:
            raise ValidationError("The file's type is not recognised.")
