"""Goldline (v4.1.1-goldline.4): access checks made at request time.

Account expiry. A user whose expiry_date has passed can no longer authenticate: password sign-in fails (the
authentication backend) and every API request with an existing token is refused (the token authentication),
from the first day after the expiry date. The nightly deactivate_expired_users task still runs; it is no longer
the only safeguard.
"""

from datetime import date

from django.contrib.auth.backends import ModelBackend
from knox.auth import TokenAuthentication
from rest_framework import exceptions


def is_expired(user) -> bool:
    expiry = getattr(user, "expiry_date", None)
    return bool(expiry) and expiry < date.today()


class ExpiryAwareModelBackend(ModelBackend):
    """The default backend, except that an expired user cannot authenticate."""

    def user_can_authenticate(self, user):
        return super().user_can_authenticate(user) and not is_expired(user)


class GoldlineTokenAuthentication(TokenAuthentication):
    """Knox token authentication with the request-time checks above."""

    def authenticate_credentials(self, token):
        user, auth_token = super().authenticate_credentials(token)
        if is_expired(user):
            raise exceptions.AuthenticationFailed("This account has expired.", code="account_expired")
        return user, auth_token
