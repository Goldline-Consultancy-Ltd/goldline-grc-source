"""Goldline (v4.1.1-goldline.4): access checks made at request time.

Account expiry. A user whose expiry_date has passed can no longer authenticate: password sign-in fails (the
authentication backend) and every API request with an existing token is refused (the token authentication),
from the first day after the expiry date. The nightly deactivate_expired_users task still runs; it is no longer
the only safeguard.

MFA. When the general setting enforce_mfa is on, a local user who has not set up MFA (not an SSO user) can use the
API only for what the MFA set-up page needs (MFA_SETUP_PATHS). Unlike the screens (routes/(app)/+layout.server.ts),
superusers are not exempt: they also need MFA for API use (Director, 19 Nov 2026). Every other API request is
refused with 403 mfa_setup_required, so a password sign-in can no longer be used for anything until MFA is set up,
whether through the screens or the API.
"""

from datetime import date

from django.contrib.auth.backends import ModelBackend
from knox.auth import TokenAuthentication
from rest_framework import exceptions

# What the screens call before and during MFA set-up (hooks.server.ts, routes/(app)/setup-mfa). The set-up itself
# goes through the allauth endpoints, which do not use this authentication class.
MFA_SETUP_PATHS = frozenset({
    "/api/iam/current-user/",
    "/api/iam/session-token/",
    "/api/settings/general/object/",
    "/api/settings/feature-flags/effective/",
    "/api/settings/general/default-language/",
    "/api/csrf/",
})


def is_expired(user) -> bool:
    expiry = getattr(user, "expiry_date", None)
    return bool(expiry) and expiry < date.today()


def mfa_setup_required(user) -> bool:
    """True when the MFA requirement applies to this user and they have not set MFA up."""
    from global_settings.models import GlobalSettings

    try:
        general = GlobalSettings.objects.get(name=GlobalSettings.Names.GENERAL).value or {}
    except GlobalSettings.DoesNotExist:
        return False
    if not general.get("enforce_mfa"):
        return False
    if not user.is_local or user.is_sso:
        return False
    has_mfa = user.has_mfa_enabled
    return not (has_mfa() if callable(has_mfa) else has_mfa)


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

    def authenticate(self, request):
        result = super().authenticate(request)
        if result is not None and request.path not in MFA_SETUP_PATHS and mfa_setup_required(result[0]):
            raise exceptions.PermissionDenied(
                "Set up multi-factor authentication before using the application.", code="mfa_setup_required"
            )
        return result
