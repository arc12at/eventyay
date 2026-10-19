import pytest
from django.urls import reverse


DASHBOARD = '/common/'
SAFE_NEXT = '/common/organizers/'
URL_NAMES = ['eventyay_common:auth.forgot', 'eventyay_common:auth.forgot.recover']


@pytest.mark.django_db
@pytest.mark.parametrize('url_name', URL_NAMES)
def test_authenticated_external_next_goes_to_interstitial(authenticated_client, url_name):
    """A logged-in user with an off-site http(s) `next` is sent to the interstitial, never straight off-site."""
    response = authenticated_client.get(reverse(url_name), {'next': 'https://example.org/fake-login'})
    assert response.status_code == 302
    assert response['Location'].startswith(reverse('redirect') + '?url=')
    page = authenticated_client.get(response['Location'])
    assert page.status_code == 200
    assert 'https://example.org/fake-login' in page.content.decode()


@pytest.mark.django_db
@pytest.mark.parametrize('url_name', URL_NAMES)
@pytest.mark.parametrize('next_url', ['//example.org/x', 'javascript:alert(1)'])
def test_authenticated_unsafe_next_falls_back_to_dashboard(authenticated_client, url_name, next_url):
    """A logged-in user with a protocol-relative or non-http `next` is sent to the dashboard."""
    response = authenticated_client.get(reverse(url_name), {'next': next_url})
    assert response.status_code == 302
    assert response['Location'] == DASHBOARD


@pytest.mark.django_db
@pytest.mark.parametrize('url_name', URL_NAMES)
def test_authenticated_safe_next_is_honored(authenticated_client, url_name):
    """A logged-in user with a relative `next` is still sent there."""
    response = authenticated_client.get(reverse(url_name), {'next': SAFE_NEXT})
    assert response.status_code == 302
    assert response['Location'] == SAFE_NEXT


@pytest.mark.django_db
@pytest.mark.parametrize('url_name', URL_NAMES)
def test_authenticated_without_next_goes_to_dashboard(authenticated_client, url_name):
    """A logged-in user without `next` is sent to the dashboard."""
    response = authenticated_client.get(reverse(url_name))
    assert response.status_code == 302
    assert response['Location'] == DASHBOARD


@pytest.mark.django_db
def test_anonymous_forgot_renders_form(client):
    """Anonymous visitors still get the form, even with an off-site `next`."""
    response = client.get(reverse('eventyay_common:auth.forgot'), {'next': 'https://example.org/x'})
    assert response.status_code == 200
    assert 'email' in response.context['form'].fields


@pytest.mark.django_db
def test_authenticated_login_external_next_goes_to_interstitial(authenticated_client):
    """The login page routes an off-site `next` through the interstitial too."""
    response = authenticated_client.get(reverse('auth.login'), {'next': 'https://example.org/x'})
    assert response.status_code == 302
    assert response['Location'].startswith(reverse('redirect') + '?url=')


@pytest.mark.django_db
def test_authenticated_login_protocol_relative_next_goes_to_dashboard(authenticated_client):
    """The login page still ignores a protocol-relative `next`."""
    response = authenticated_client.get(reverse('auth.login'), {'next': '//example.org/x'})
    assert response.status_code == 302
    assert response['Location'] == DASHBOARD


@pytest.mark.django_db
def test_logout_external_back_goes_to_interstitial(authenticated_client):
    """An off-site `back` after logout goes through the interstitial."""
    response = authenticated_client.get(reverse('eventyay_common:auth.logout'), {'back': 'https://example.org/x'})
    assert response.status_code == 302
    assert response['Location'].startswith(reverse('redirect') + '?url=')
