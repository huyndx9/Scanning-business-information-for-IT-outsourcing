"""URL validation + SSRF protection.

Spec section 19: only http/https, block localhost / private ranges / metadata IPs.
Every hop (including redirects) must be re-validated before a request is issued.
"""
from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit

ALLOWED_SCHEMES = {"http", "https"}

BLOCKED_HOSTNAMES = {
    "localhost",
    "localhost.localdomain",
    "ip6-localhost",
    "ip6-loopback",
    "metadata.google.internal",
    "metadata",
    "instance-data",
}

# Ports other than plain web ports are refused (no ssh/smtp/redis probing).
ALLOWED_PORTS = {80, 443, 8080, 8443}


class UrlNotAllowed(Exception):
    """Raised when a URL fails validation."""


class DomainNotResolved(UrlNotAllowed):
    """The URL is well-formed but its domain has no public address."""


@dataclass(frozen=True)
class SafeUrl:
    url: str
    scheme: str
    host: str
    port: int


def _ip_is_public(ip: ipaddress._BaseAddress) -> bool:
    if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast:
        return False
    if ip.is_reserved or ip.is_unspecified:
        return False
    # 169.254.169.254 is caught by is_link_local; keep the explicit guard anyway.
    if str(ip) in {"169.254.169.254", "0.0.0.0", "::"}:
        return False
    if isinstance(ip, ipaddress.IPv6Address):
        if ip.ipv4_mapped is not None:
            return _ip_is_public(ip.ipv4_mapped)
        if ip.is_site_local:
            return False
    return True


def normalize_input_url(raw: str) -> str:
    """Turn what a user typed into an absolute http(s) URL (no validation yet)."""
    value = (raw or "").strip()
    if not value:
        raise UrlNotAllowed("Empty URL.")
    if "://" not in value:
        value = "https://" + value
    parts = urlsplit(value)
    if parts.scheme.lower() not in ALLOWED_SCHEMES:
        raise UrlNotAllowed("Only http:// and https:// URLs are supported.")
    if not parts.hostname:
        raise UrlNotAllowed("Invalid URL.")
    return urlunsplit((parts.scheme.lower(), parts.netloc, parts.path or "/", parts.query, ""))


def validate_url(url: str) -> SafeUrl:
    """Validate scheme, host and every resolved IP. Raises UrlNotAllowed."""
    parts = urlsplit(url)
    scheme = (parts.scheme or "").lower()
    if scheme not in ALLOWED_SCHEMES:
        raise UrlNotAllowed("Only http:// and https:// URLs are supported.")

    host = (parts.hostname or "").lower().rstrip(".")
    if not host:
        raise UrlNotAllowed("Invalid URL.")
    if host in BLOCKED_HOSTNAMES or host.endswith(".localhost") or host.endswith(".local"):
        raise UrlNotAllowed("This host is not allowed.")

    try:
        port = parts.port or (443 if scheme == "https" else 80)
    except ValueError:
        raise UrlNotAllowed("Invalid port.")
    if port not in ALLOWED_PORTS:
        raise UrlNotAllowed("This port is not allowed.")

    # Literal IP in the URL.
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None
    if literal is not None:
        if not _ip_is_public(literal):
            raise UrlNotAllowed("Private or loopback addresses are not allowed.")
        return SafeUrl(url=url, scheme=scheme, host=host, port=port)

    try:
        infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        raise DomainNotResolved("Domain could not be resolved.")

    addresses = {info[4][0] for info in infos}
    if not addresses:
        raise DomainNotResolved("Domain could not be resolved.")
    for address in addresses:
        try:
            ip = ipaddress.ip_address(address.split("%")[0])
        except ValueError:
            raise DomainNotResolved("Domain could not be resolved.")
        if not _ip_is_public(ip):
            raise UrlNotAllowed("Private or loopback addresses are not allowed.")

    return SafeUrl(url=url, scheme=scheme, host=host, port=port)
