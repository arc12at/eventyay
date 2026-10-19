import urllib.parse

from django.core import signing
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme


SIGNER = signing.Signer(salt='safe-redirect')


def redirect_view(request: HttpRequest) -> HttpResponse:
    """Show the 'leaving Eventyay' interstitial; never redirect off-site without a click."""
    try:
        url = SIGNER.unsign(request.GET.get('url', ''))
    except signing.BadSignature:
        return HttpResponseBadRequest('Invalid parameter')
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname:
        return HttpResponseBadRequest('Invalid parameter')
    response = render(request, 'common/redirect.html', {'hostname': parsed.hostname, 'url': url})
    response['X-Robots-Tag'] = 'noindex'
    return response


def safelink(url: str) -> str:
    """Route off-site URLs through the interstitial; local URLs pass through unchanged."""
    if url_has_allowed_host_and_scheme(url, allowed_hosts=None):
        return url
    return reverse('redirect') + '?url=' + urllib.parse.quote(SIGNER.sign(url))


def safe_next(url: str | None) -> str | None:
    """Validate a ``next``-style redirect parameter.

    Local URLs are returned as-is, off-site http(s) URLs are routed through the interstitial,
    anything else (``//host``, ``javascript:``, empty) returns ``None`` so callers use their default.
    """
    if url and (
        url_has_allowed_host_and_scheme(url, allowed_hosts=None)
        or urllib.parse.urlparse(url).scheme in ('http', 'https')
    ):
        return safelink(url)
    return None
