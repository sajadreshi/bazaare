from urllib.parse import urlsplit


def is_safe_next(target):
    """Only allow redirects to a path on this site (blocks //evil.com, /\\evil.com, http://...)."""
    if not target or not target.startswith("/") or target.startswith("//") or "\\" in target:
        return False
    parsed = urlsplit(target)
    return not parsed.scheme and not parsed.netloc
