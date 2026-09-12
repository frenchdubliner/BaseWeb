from django.contrib.auth.backends import ModelBackend


class EmailBackend(ModelBackend):
    """
    Standard email/password backend, except it does not reject inactive
    (unverified) users at the credential-check stage. Access control for
    unverified accounts is instead enforced per-endpoint via permission
    classes (see apps.accounts.permissions.IsVerified), because unverified
    users must still be able to log in, log out, view their profile and
    resend the verification email.
    """

    def user_can_authenticate(self, user):
        return True
