"""Goldline (v4.1.1-goldline.7, FND-254, R-SEC-02): repeated wrong second-factor codes are limited per user.

The sign-in library already counts wrong codes, but in the process's own memory: the API runs several worker
processes, each with its own count, so a run of wrong codes spread over the workers never reached the limit, and a
reached limit answered 400 like any wrong code while the pending sign-in stayed open.

This module adds a count that every worker shares (a file cache in the container's temporary directory, so no
database change) and, once a user reaches the limit:
  - every further code for that user is refused, right or wrong, until the window has passed;
  - the sign-in step answers 429 (body unchanged apart from the status: code too_many_login_attempts on the code
    field, which the sign-in screen already shows next to the field);
  - the pending sign-in is closed, so the password has to be entered again (itself rate-limited).
A correct code clears the user's count. The library's own per-process limit still applies on top.

LIMIT failures within WINDOW_SECONDS lock the second factor for the rest of the window (sliding window).
"""

import json
import re
import time
from importlib import import_module

from django.conf import settings
from django.core.cache import caches
from django.http import JsonResponse

# Defined in settings.CACHES (a file cache under the temporary directory, shared by the worker processes)
CACHE_ALIAS = "goldline_ratelimit"
LIMIT = 5
WINDOW_SECONDS = 15 * 60
ERROR_CODE = "too_many_login_attempts"

# The second-factor step of a pending sign-in, for the app (token) and browser (cookie) clients
AUTHENTICATE_PATH = re.compile(
    r"^/api/_allauth/(app|browser)/v1/auth/2fa/authenticate/?$"
)


def _key(user) -> str:
    return f"gl-mfa-fail-{user.pk}"


def _recent(user, now: float) -> list:
    return [
        t for t in caches[CACHE_ALIAS].get(_key(user), []) if t > now - WINDOW_SECONDS
    ]


def is_locked(user, now: float | None = None) -> bool:
    now = time.time() if now is None else now
    return len(_recent(user, now)) >= LIMIT


def record_attempt(user, now: float | None = None) -> None:
    """Counts an attempt as failed until clear() says otherwise (a crash mid-check still counts)."""
    now = time.time() if now is None else now
    history = _recent(user, now)[-(LIMIT - 1) :] + [now]
    caches[CACHE_ALIAS].set(_key(user), history, WINDOW_SECONDS)


def clear(user) -> None:
    caches[CACHE_ALIAS].delete(_key(user))


def wrap_check_rate_limit(original):
    """Wraps allauth's check_rate_limit(user, error_key=None) -> clear callback with the shared per-user count."""

    def check_rate_limit(user, error_key=None):
        from allauth.account.adapter import get_adapter

        if is_locked(user):
            raise get_adapter().validation_error(error_key or ERROR_CODE)
        clear_original = original(user, error_key=error_key)
        record_attempt(user)

        def clear_all():
            clear(user)
            clear_original()

        return clear_all

    check_rate_limit.goldline_wrapped = True
    check_rate_limit.goldline_original = original
    return check_rate_limit


def install() -> None:
    """Replaces check_rate_limit in each allauth module that imported it by name. Safe to call more than once."""
    for name in (
        "allauth.mfa.base.internal.flows",
        "allauth.mfa.base.forms",
        "allauth.mfa.totp.forms",
        "allauth.mfa.webauthn.forms",
    ):
        module = import_module(name)
        current = module.check_rate_limit
        if not getattr(current, "goldline_wrapped", False):
            module.check_rate_limit = wrap_check_rate_limit(current)


def _is_limit_response(response) -> bool:
    if response.status_code != 400 or "json" not in response.get("Content-Type", ""):
        return False
    try:
        body = json.loads(response.content)
    except ValueError:
        return False
    return any(
        isinstance(e, dict) and e.get("code") == ERROR_CODE
        for e in body.get("errors", [])
    )


def _close_pending_sign_in(request) -> None:
    token = request.headers.get("X-Session-Token")
    if token:
        engine = import_module(settings.SESSION_ENGINE)
        engine.SessionStore(session_key=token).delete()
    elif hasattr(request, "session"):
        request.session.flush()


class MFALimitMiddleware:
    """On the second-factor step: a reached limit answers 429 and closes the pending sign-in."""

    def __init__(self, get_response):
        self.get_response = get_response
        install()
        from iam.goldline_totp_replay import install as install_totp_replay

        install_totp_replay()  # Goldline (v4.1.1-goldline.9): also installed by IamConfig.ready

    def __call__(self, request):
        response = self.get_response(request)
        if (
            request.method == "POST"
            and AUTHENTICATE_PATH.match(request.path)
            and _is_limit_response(response)
        ):
            body = json.loads(response.content)
            body["status"] = 429
            _close_pending_sign_in(request)
            limited = JsonResponse(body, status=429)
            limited["Retry-After"] = str(WINDOW_SECONDS)
            return limited
        return response
