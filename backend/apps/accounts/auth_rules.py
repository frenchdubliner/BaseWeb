def allow_inactive_user_authentication_rule(user):
    """
    Unlike SimpleJWT's default rule, this permits unverified (is_active=False)
    users to obtain a token pair, because the spec requires them to still be
    able to log in, log out, view their profile, and resend the verification
    email. Every other endpoint enforces IsVerified separately.
    """
    return user is not None
