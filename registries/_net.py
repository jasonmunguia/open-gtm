"""Shared HTTPS opener for registry adapters.

python.org Python on macOS ships without a usable CA bundle, so stock urllib
raises CERTIFICATE_VERIFY_FAILED on perfectly good government sites — a
stranger's first run dies with a cryptic SSL error. certifi (a pip-installed
CA bundle) fixes it; fall back to the system default when it's absent.
"""
import ssl
import urllib.request


def context():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def urlopen(req, timeout=60):
    return urllib.request.urlopen(req, timeout=timeout, context=context())
