"""Goldline v4.1.1-goldline.9 (TC-AUTH-006): a second-factor code is accepted once, whichever worker checks it.

Each test creates its own user in the test database; nothing here touches a real instance.
"""

import multiprocessing
import os
import shutil
import time

import pytest
from allauth.mfa import app_settings as mfa_settings
from allauth.mfa.models import Authenticator
from allauth.mfa.totp.internal.auth import (
    TOTP,
    format_hotp_value,
    generate_totp_secret,
    hotp_value,
)
from django.core.cache import caches
from django.test import Client

from iam import goldline_mfa_limit as limit
from iam import goldline_totp_replay as replay
from iam.models import User

PASSWORD = "Goldline-test-pw-1A!"
LOGIN = "/api/_allauth/app/v1/auth/login"
MFA = "/api/_allauth/app/v1/auth/2fa/authenticate"


@pytest.fixture(autouse=True)
def fresh_state():
    shutil.rmtree(replay._directory(), ignore_errors=True)
    caches[limit.CACHE_ALIAS].clear()
    caches["default"].clear()
    limit.install()
    replay.install()
    yield
    shutil.rmtree(replay._directory(), ignore_errors=True)


def _user_with_totp(email):
    user = User.objects.create_user(email=email, password=PASSWORD)
    secret = generate_totp_secret()
    TOTP.activate(user, secret)
    return user, secret


def _step(now=None):
    return int(time.time() if now is None else now) // mfa_settings.TOTP_PERIOD


def _code(secret, step):
    return format_hotp_value(hotp_value(secret, step))


def _sign_in(email, code):
    """A whole sign-in from a new client (as from another browser), returning the second-factor status."""
    client = Client()
    r = client.post(LOGIN, {"email": email, "password": PASSWORD}, content_type="application/json")
    assert r.status_code == 401, r.content
    token = r.json()["meta"]["session_token"]
    return client.post(MFA, {"code": code}, content_type="application/json", HTTP_X_SESSION_TOKEN=token)


def _race(directory_env, user_id, code, n, queue):
    os.environ.update(directory_env)
    queue.put(replay.mark_code_used(user_id, code))


class TestMarker:
    def test_first_use_wins_reuse_refused(self, settings):
        assert replay.mark_code_used("u1", "123456") is True
        assert replay.mark_code_used("u1", "123456") is False

    def test_reuse_refused_when_the_process_cache_is_empty(self):
        # Another worker has its own empty default cache: the shared record still refuses the code
        assert replay.mark_code_used("u2", "654321") is True
        caches["default"].clear()
        assert replay.mark_code_used("u2", "654321") is False

    def test_users_and_codes_are_separate(self):
        assert replay.mark_code_used("u3", "111111") is True
        assert replay.mark_code_used("u4", "111111") is True
        assert replay.mark_code_used("u3", "222222") is True

    def test_stale_marker_is_replaced(self):
        start = time.time()
        assert replay.mark_code_used("u5", "333333", now=start) is True
        later = start + replay._lifetime() + 5
        os.utime(replay._marker(replay._directory(), "u5", "333333"), (start, start))
        assert replay.mark_code_used("u5", "333333", now=later) is True

    def test_code_is_not_written_to_disk(self):
        replay.mark_code_used("u6", "987654")
        names = os.listdir(replay._directory())
        assert names and not any("987654" in n for n in names)

    @pytest.mark.skipif("fork" not in multiprocessing.get_all_start_methods(), reason="needs fork")
    def test_simultaneous_workers_exactly_one_accepted(self):
        ctx = multiprocessing.get_context("fork")
        queue = ctx.Queue()
        procs = [ctx.Process(target=_race, args=({}, "u7", "444444", i, queue)) for i in range(8)]
        for p in procs:
            p.start()
        for p in procs:
            p.join(30)
        results = [queue.get(timeout=5) for _ in procs]
        assert results.count(True) == 1, results
        assert results.count(False) == 7, results


@pytest.mark.django_db
class TestSignInReplay:
    def test_same_code_refused_on_second_sign_in_from_another_worker(self):
        user, secret = _user_with_totp("totp-replay@tests.com")
        step = _step()
        code = _code(secret, step)
        if _step() != step:  # the step changed while setting up
            code = _code(secret, _step())
        first = _sign_in(user.email, code)
        assert first.status_code == 200, first.content
        caches["default"].clear()  # the second request lands on a worker with an empty process cache
        second = _sign_in(user.email, code)
        assert second.status_code in (400, 429), second.content
        assert "access_token" not in second.json().get("meta", {})

    def test_fresh_code_in_the_next_step_still_works(self, monkeypatch):
        user, secret = _user_with_totp("totp-next-step@tests.com")
        step = _step()
        assert _sign_in(user.email, _code(secret, step)).status_code == 200
        next_time = (step + 1) * mfa_settings.TOTP_PERIOD + 1
        monkeypatch.setattr(time, "time", lambda: float(next_time))
        r = _sign_in(user.email, _code(secret, step + 1))
        assert r.status_code == 200, r.content

    def test_reauthentication_goes_through_the_shared_record(self):
        user, secret = _user_with_totp("totp-reauth@tests.com")
        totp = TOTP(Authenticator.objects.get(user=user, type=Authenticator.Type.TOTP))
        code = _code(secret, _step())
        assert totp.validate_code(code) is True
        caches["default"].clear()
        assert totp.validate_code(code) is False

    def test_install_is_idempotent(self):
        replay.install()
        replay.install()
        assert TOTP._mark_code_used.goldline_wrapped
