"""Goldline (v4.1.1-goldline.9, TC-AUTH-006): a second-factor code is accepted once, whichever worker checks it.

The sign-in library records a used code in Django's default cache, which is the process's own memory: the API runs
several worker processes, so the same code sent again within its 30 seconds was accepted when the second request
reached another worker.

The record now lives next to the shared rate-limit cache (settings.CACHES["goldline_ratelimit"], a directory in the
container's temporary directory that every worker shares): one marker file per user and code, created with O_EXCL so
exactly one request wins even when two arrive at the same moment. A marker older than the code's lifetime is stale and
is replaced. The file name is a hash; the code itself is never written to disk.

This covers every check that goes through the library's TOTP.validate_code: the sign-in second factor and
reauthentication. Activating an authenticator checks a code against a secret that is not stored yet and creates the
authenticator once, so there is nothing to replay there.
"""

from __future__ import annotations

import hashlib
import os
import random
import time

from django.conf import settings

SUBDIR = "totp-used"
PRUNE_AFTER_SECONDS = 3600


def _directory() -> str:
    base = settings.CACHES.get("goldline_ratelimit", {}).get("LOCATION") or os.path.join(
        os.environ.get("TMPDIR", "/tmp"), "goldline-ratelimit"
    )
    path = os.path.join(base, SUBDIR)
    os.makedirs(path, mode=0o700, exist_ok=True)
    return path


def _lifetime() -> int:
    from allauth.mfa import app_settings

    return int(app_settings.TOTP_PERIOD) * (2 * int(app_settings.TOTP_TOLERANCE) + 1)


def _marker(directory: str, user_id, code: str) -> str:
    digest = hashlib.sha256(f"{settings.SECRET_KEY}|{user_id}|{code}".encode()).hexdigest()
    return os.path.join(directory, digest)


def _prune(directory: str, now: float) -> None:
    try:
        for name in os.listdir(directory):
            full = os.path.join(directory, name)
            try:
                if now - os.path.getmtime(full) > PRUNE_AFTER_SECONDS:
                    os.unlink(full)
            except OSError:
                pass
    except OSError:
        pass


def mark_code_used(user_id, code: str, now: float | None = None) -> bool:
    """True the first time a user's code is seen within its lifetime, False on any reuse (from any worker)."""
    now = time.time() if now is None else now
    directory = _directory()
    path = _marker(directory, user_id, code)
    for _ in range(2):
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            try:
                age = now - os.path.getmtime(path)
            except FileNotFoundError:
                continue  # removed meanwhile: try again
            if age <= _lifetime():
                return False
            try:
                os.unlink(path)  # stale marker from an earlier step
            except FileNotFoundError:
                pass
            continue
        os.close(fd)
        os.utime(path, (now, now))
        if random.random() < 0.01:
            _prune(directory, now)
        return True
    return False


def _mark_code_used(self, code: str) -> bool:
    return mark_code_used(self.instance.user_id, code)


_mark_code_used.goldline_wrapped = True


def install() -> None:
    """Replaces TOTP._mark_code_used in the library. Safe to call more than once."""
    from allauth.mfa.totp.internal.auth import TOTP

    if not getattr(TOTP._mark_code_used, "goldline_wrapped", False):
        TOTP._mark_code_used = _mark_code_used
