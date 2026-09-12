import ipaddress


def get_client_ip(request) -> str:
    """
    Returns the client IP resolved by TrustedProxyMiddleware. Falls back to
    REMOTE_ADDR directly if the middleware has not run (e.g. management
    commands, tests constructing a bare request).
    """
    return getattr(request, "client_ip", None) or request.META.get("REMOTE_ADDR", "")


def ip_matches(ip: str, ip_or_cidr: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    try:
        if "/" in ip_or_cidr:
            return addr in ipaddress.ip_network(ip_or_cidr, strict=False)
        return addr == ipaddress.ip_address(ip_or_cidr)
    except ValueError:
        return False


def ip_in_list(ip: str, entries) -> bool:
    return any(ip_matches(ip, entry) for entry in entries)
