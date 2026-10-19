"""
Tests for common pages and utilities (redirects, CSP reporting, etc).
"""
import pytest
import json

from django.urls import reverse

from eventyay.common.views.redirect import safe_next, safelink


@pytest.mark.django_db
class TestCommonPages:
    """Test common utility endpoints."""

    def test_redirect_renders_interstitial(self, client):
        """A signed off-site URL renders the interstitial, even with a same-site referer."""
        url = 'https://example.org/a?b=1'
        response = client.get(safelink(url), HTTP_REFERER='http://testserver/')
        assert response.status_code == 200
        content = response.content.decode()
        assert 'example.org' in content
        assert 'https://example.org/a?b=1' in content
        assert 'You are leaving Eventyay and being redirected to an external website.' in content
        assert 'You are being redirected to' in content
        assert 'Continue to External Site' in content
        assert 'Cancel / Return to Dashboard' in content
        assert reverse('eventyay_common:dashboard') in content

    def test_redirect_escapes_hostname(self, client):
        """A crafted hostname is shown escaped, never as markup."""
        response = client.get(safelink('https://<b>x/'))
        assert response.status_code == 200
        assert '<b>x' not in response.content.decode()

    @pytest.mark.parametrize('url', ['javascript:alert(1)', 'data:text/html,x', 'ftp://example.org', 'http://[bad'])
    def test_redirect_rejects_bad_scheme(self, client, url):
        """Non-http(s) targets are rejected, so they never become a clickable link."""
        assert client.get(safelink(url)).status_code == 400

    def test_redirect_rejects_unsigned(self, client):
        """An unsigned target is rejected."""
        assert client.get(reverse('redirect'), {'url': 'https://example.org'}).status_code == 400

    def test_safelink_passes_local_urls(self):
        """Local URLs are not wrapped."""
        assert safelink('/common/') == '/common/'

    @pytest.mark.parametrize('url', [None, '', '//example.org/x', 'javascript:alert(1)', 'http://[bad'])
    def test_safe_next_rejects_unsafe(self, url):
        """Unsafe redirect targets fall back to the caller's default."""
        assert safe_next(url) is None

    def test_safe_next_routes_offsite_through_interstitial(self):
        """Local targets pass through; off-site http(s) targets go through the interstitial."""
        assert safe_next('/common/organizers/') == '/common/organizers/'
        assert safe_next('https://example.org/x').startswith(reverse('redirect') + '?url=')

    def test_csp_report_endpoint(self, client):
        """Test CSP report endpoint accepts POST with valid JSON."""
        csp_report = {
            "csp-report": {
                "document-uri": "https://example.com/",
                "referrer": "",
                "blocked-uri": "https://evil.com/malicious.js",
                "violated-directive": "script-src",
                "original-policy": "script-src 'self'",
            }
        }
        response = client.post(
            reverse('csp.report'),
            data=json.dumps(csp_report),
            content_type='application/csp-report'
        )
        # Should accept CSP reports
        assert response.status_code in [200, 204]

    def test_csp_report_endpoint_empty_json(self, client):
        """Test CSP report endpoint with empty JSON body."""
        response = client.post(
            reverse('csp.report'),
            data='{}',
            content_type='application/json'
        )
        # Should handle empty JSON gracefully
        assert response.status_code in [200, 204, 400]

    def test_csp_report_endpoint_malformed_json(self, client):
        """Test CSP report endpoint with malformed JSON."""
        response = client.post(
            reverse('csp.report'),
            data='{bad json}',
            content_type='application/json'
        )
        # Should reject malformed JSON or handle gracefully
        assert response.status_code in [200, 204, 400]

    def test_csp_report_endpoint_missing_data(self, client):
        """Test CSP report endpoint with missing data."""
        response = client.post(
            reverse('csp.report'),
            data='',
            content_type='application/json'
        )
        # Should handle missing data gracefully
        assert response.status_code in [200, 204, 400]

    def test_metrics_endpoint(self, client):
        """Test metrics endpoint (may require auth)."""
        response = client.get(reverse('metrics'))
        # May require auth or return metrics
        assert response.status_code in [200, 401, 403]


@pytest.mark.django_db
class TestStaticPages:
    """Test static content and assets."""

    def test_static_url_pattern(self, client):
        """Test that static URL pattern is configured."""
        # Just verify the static URL doesn't 500
        response = client.get('/static/')
        # May 404 but shouldn't crash
        assert response.status_code in [200, 301, 302, 404]

    def test_media_url_pattern(self, client):
        """Test that media URL pattern is configured."""
        response = client.get('/media/')
        # May 404 but shouldn't crash
        assert response.status_code in [200, 301, 302, 404]


@pytest.mark.django_db
class TestJavaScriptHelpers:
    """Test JavaScript helper endpoints."""

    def test_js_catalog_endpoint(self, client):
        """Test JavaScript i18n catalog endpoint."""
        response = client.get('/jsi18n/en/')
        # Should return JavaScript catalog
        assert response.status_code == 200
        assert 'javascript' in response['Content-Type'].lower() or 'text' in response['Content-Type'].lower()

    def test_js_helpers_states(self, client):
        """Test states helper endpoint."""
        response = client.get('/js_helpers/states/')
        # Should return state data
        assert response.status_code in [200, 400]  # 400 if no country specified
