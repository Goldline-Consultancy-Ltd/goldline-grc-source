"""Goldline v4.1.1-goldline.7 (FND-254, R-SEC-02): wrong second-factor codes are limited per user, across workers.

Each test creates its own user in the test database; nothing here touches a real instance.
"""

import pytest
from allauth.mfa.totp.internal.auth import (
    TOTP,
    format_hotp_value,
    generate_totp_secret,
    hotp_value,
    yield_hotp_counters_from_time,
)
from django.core.cache import caches
from django.test import Client

from iam import goldline_mfa_limit as limit
from iam.models import User

PASSWORD = "Goldline-test-pw-1A!"
LOGIN = "/api/_allauth/app/v1/auth/login"
MFA = "/api/_allauth/app/v1/auth/2fa/authenticate"


@pytest.fixture(autouse=True)
def fresh_counts():
    caches[limit.CACHE_ALIAS].clear()
    caches["default"].clear()
    limit.install()
    yield
    caches[limit.CACHE_ALIAS].clear()


def _user_with_totp(email):
    user = User.objects.create_user(email=email, password=PASSWORD)
    secret = generate_totp_secret()
    TOTP.activate(user, secret)
    return user, secret


def _current_code(secret):
    return format_hotp_value(hotp_value(secret, next(yield_hotp_counters_from_time())))


def _wrong_code(secret, i):
    right = _current_code(secret)
    code = str(100000 + i)
    return code if code != right else str(200000 + i)


def _pending_sign_in(client, email):
    r = client.post(
        LOGIN, {"email": email, "password": PASSWORD}, content_type="application/json"
    )
    assert r.status_code == 401, r.content
    return r.json()["meta"]["session_token"]


def _mfa(client, token, code):
    return client.post(
        MFA, {"code": code}, content_type="application/json", HTTP_X_SESSION_TOKEN=token
    )


@pytest.mark.django_db
class TestSecondFactorLimit:
    def test_repeated_wrong_codes_answer_429_and_close_the_sign_in(self):
        user, secret = _user_with_totp("mfa-limit@tests.com")
        client = Client()
        token = _pending_sign_in(client, user.email)
        statuses = [
            _mfa(client, token, _wrong_code(secret, i)).status_code for i in range(12)
        ]
        assert statuses[: limit.LIMIT] == [400] * limit.LIMIT, statuses
        assert statuses[limit.LIMIT] == 429, statuses
        # The pending sign-in is closed: the same session cannot try again
        assert all(s in (401, 409, 410, 429) for s in statuses[limit.LIMIT + 1 :]), (
            statuses
        )

    def test_limit_response_keeps_the_error_shape_the_screen_reads(self):
        user, secret = _user_with_totp("mfa-limit-shape@tests.com")
        client = Client()
        token = _pending_sign_in(client, user.email)
        for i in range(limit.LIMIT):
            _mfa(client, token, _wrong_code(secret, i))
        r = _mfa(client, token, _wrong_code(secret, 99))
        assert r.status_code == 429
        body = r.json()
        assert body["status"] == 429
        assert {"code": limit.ERROR_CODE, "param": "code"}.items() <= body["errors"][
            0
        ].items()
        assert r["Retry-After"] == str(limit.WINDOW_SECONDS)

    def test_new_sign_in_does_not_reset_the_count_and_right_code_is_refused_while_locked(
        self,
    ):
        user, secret = _user_with_totp("mfa-limit-relogin@tests.com")
        client = Client()
        token = _pending_sign_in(client, user.email)
        for i in range(limit.LIMIT):
            _mfa(client, token, _wrong_code(secret, i))
        token2 = _pending_sign_in(Client(), user.email)
        r = _mfa(Client(), token2, _current_code(secret))
        assert r.status_code == 429
        assert "access_token" not in r.json().get("meta", {})

    def test_count_is_shared_not_per_process(self):
        # Simulates another worker: the library's own per-process count is empty, the shared count is not
        user, secret = _user_with_totp("mfa-limit-shared@tests.com")
        for _ in range(limit.LIMIT):
            limit.record_attempt(user)
        caches["default"].clear()
        token = _pending_sign_in(Client(), user.email)
        assert _mfa(Client(), token, _current_code(secret)).status_code == 429

    def test_right_code_clears_the_count(self):
        user, secret = _user_with_totp("mfa-limit-clear@tests.com")
        client = Client()
        token = _pending_sign_in(client, user.email)
        for i in range(limit.LIMIT - 1):
            assert _mfa(client, token, _wrong_code(secret, i)).status_code == 400
        r = _mfa(client, token, _current_code(secret))
        assert r.status_code == 200, r.content
        assert not limit.is_locked(user)
        assert caches[limit.CACHE_ALIAS].get(f"gl-mfa-fail-{user.pk}") is None

    def test_window_slides(self):
        user, _ = _user_with_totp("mfa-limit-window@tests.com")
        start = 1_800_000_000.0
        for i in range(limit.LIMIT):
            limit.record_attempt(user, now=start + i)
        assert limit.is_locked(user, now=start + limit.LIMIT)
        assert not limit.is_locked(user, now=start + limit.WINDOW_SECONDS + 1)

    def test_users_are_counted_separately(self):
        a, _ = _user_with_totp("mfa-limit-a@tests.com")
        b, _ = _user_with_totp("mfa-limit-b@tests.com")
        for _ in range(limit.LIMIT):
            limit.record_attempt(a)
        assert limit.is_locked(a)
        assert not limit.is_locked(b)

    def test_install_is_idempotent(self):
        from allauth.mfa.base import forms

        limit.install()
        limit.install()
        assert forms.check_rate_limit.goldline_wrapped
        assert not getattr(
            forms.check_rate_limit.goldline_original, "goldline_wrapped", False
        )
