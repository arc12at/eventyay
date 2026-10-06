import io
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils.timezone import now
from django_scopes import scopes_disabled
from PIL import Image

from eventyay.base.header_presets import get_active_presets, invalidate_preset_cache
from eventyay.base.models import Event, EventHeaderPreset, EventHeaderPresetCategory, Organizer, User


def _create_test_image(width=1920, height=640):
    out = io.BytesIO()
    im = Image.new('RGB', (width, height), color=(100, 150, 200))
    im.save(out, format='JPEG')
    out.seek(0)
    return SimpleUploadedFile('sample_preset.jpg', out.read(), content_type='image/jpeg')


@pytest.fixture
def admin_user(client):
    user = User.objects.create_superuser('admin_preset@test.org', 'adminpass123')
    client.force_login(user)
    user.staffsession_set.create(date_start=now(), session_key=client.session.session_key)
    return user


@pytest.fixture
def test_category():
    cat, _ = EventHeaderPresetCategory.objects.get_or_create(
        name='Abstract Test',
    )
    return cat


@pytest.mark.django_db
def test_admin_preset_list_view(client, admin_user, test_category):
    preset = EventHeaderPreset.objects.create(
        name='Test Preset Alpha',
        category=test_category,
        image=_create_test_image(),
        thumbnail=_create_test_image(),
        is_active=True,
    )
    invalidate_preset_cache()

    url = reverse('eventyay_admin:admin.header_presets')
    response = client.get(url)
    assert response.status_code == 200
    assert 'presets' in response.context
    assert 'categories' in response.context
    assert 'total_presets_count' in response.context
    assert preset in response.context['presets']


@pytest.mark.django_db
def test_admin_preset_create_view(client, admin_user, test_category):
    url = reverse('eventyay_admin:admin.header_presets.add')
    test_image = _create_test_image(1200, 400)

    data = {
        'name_0': 'Admin Uploaded Sunset',
        'category': test_category.pk,
        'image': test_image,
        'is_active': 'on',
    }
    response = client.post(url, data)
    assert response.status_code == 302

    preset = EventHeaderPreset.objects.filter(name__icontains='Admin Uploaded Sunset').first()
    assert preset is not None
    assert preset.image is not None
    assert preset.thumbnail is not None
    assert preset.is_active is True
    assert preset in get_active_presets()

    with Image.open(preset.image) as img:
        assert img.size == (1920, 640)
        assert img.format == 'JPEG'

    with Image.open(preset.thumbnail) as thumb:
        assert thumb.size == (400, 133)
        assert thumb.format == 'JPEG'


@pytest.mark.django_db
def test_admin_preset_create_invalid_image_fails(client, admin_user, test_category):
    url = reverse('eventyay_admin:admin.header_presets.add')
    fake_file = SimpleUploadedFile('malicious.txt', b'this is not an image file', content_type='text/plain')

    data = {
        'name_0': 'Invalid Image Preset',
        'category': test_category.pk,
        'image': fake_file,
    }
    response = client.post(url, data)
    assert response.status_code == 200
    assert 'form' in response.context
    assert 'image' in response.context['form'].errors


@pytest.mark.django_db
def test_admin_preset_update_view(client, admin_user, test_category):
    preset = EventHeaderPreset.objects.create(
        name='Original Preset Name',
        category=test_category,
        image=_create_test_image(),
        thumbnail=_create_test_image(),
        is_active=True,
    )
    original_image_name = preset.image.name
    original_thumbnail_name = preset.thumbnail.name

    url = reverse('eventyay_admin:admin.header_presets.edit', kwargs={'pk': preset.pk})
    data = {
        'name_0': 'Updated Preset Name',
        'category': test_category.pk,
    }
    response = client.post(url, data)
    assert response.status_code == 302

    preset.refresh_from_db()
    assert 'Updated Preset Name' in str(preset.name)
    assert preset.image.name == original_image_name
    assert preset.thumbnail.name == original_thumbnail_name


@pytest.mark.django_db
def test_admin_preset_delete_view(client, admin_user, test_category):
    preset = EventHeaderPreset.objects.create(
        name='To Be Deleted Preset',
        category=test_category,
        image=_create_test_image(),
        thumbnail=_create_test_image(),
        is_active=True,
    )

    url = reverse('eventyay_admin:admin.header_presets.delete', kwargs={'pk': preset.pk})
    response = client.post(url)
    assert response.status_code == 302

    assert not EventHeaderPreset.objects.filter(pk=preset.pk).exists()


@pytest.mark.django_db
def test_admin_preset_category_crud(client, admin_user):
    # 1. Create category
    add_url = reverse('eventyay_admin:admin.header_presets.category.add')
    data = {
        'name_0': 'Sci-Fi Futuristic',
    }
    response = client.post(add_url, data)
    assert response.status_code == 302

    cat = EventHeaderPresetCategory.objects.filter(name__icontains='Sci-Fi Futuristic').first()
    assert cat is not None
    assert 'Sci-Fi Futuristic' in str(cat.name)

    # 2. Edit category
    edit_url = reverse('eventyay_admin:admin.header_presets.category.edit', kwargs={'pk': cat.pk})
    data = {
        'name_0': 'Sci-Fi Renamed',
    }
    response = client.post(edit_url, data)
    assert response.status_code == 302
    cat.refresh_from_db()
    assert 'Sci-Fi Renamed' in str(cat.name)

    # 3. Delete category
    delete_url = reverse('eventyay_admin:admin.header_presets.category.delete', kwargs={'pk': cat.pk})
    response = client.post(delete_url)
    assert response.status_code == 302
    assert not EventHeaderPresetCategory.objects.filter(pk=cat.pk).exists()


@pytest.fixture
def organizer():
    return Organizer.objects.create(name='Test Org', slug='test-org-presets')


@pytest.mark.django_db
def test_preset_resolution_in_event_model(organizer, test_category):
    preset = EventHeaderPreset.objects.create(
        name='Ocean Breeze',
        category=test_category,
        image=_create_test_image(),
        thumbnail=_create_test_image(400, 133),
        is_active=True,
    )
    invalidate_preset_cache()

    with scopes_disabled():
        event = Event.objects.create(
            organizer=organizer,
            name='Direct Model Preset Test',
            slug='direct-model-preset-test',
            date_from=now(),
            date_to=now(),
        )
        event.settings.set('logo_image', f'preset:{preset.pk}')

        from django.core.files.storage import default_storage

        assert event._visible_header_image_path == f'preset:{preset.pk}'
        assert event.visible_header_image_url == default_storage.url(preset.image.name)
        assert event.visible_header_image_file.name.endswith(preset.image.name)
        assert event.preview_image_url_with_fallback == default_storage.url(preset.image.name)
        assert event.preview_image_url_small == default_storage.url(preset.thumbnail.name)


@pytest.mark.django_db
def test_resolve_preset_known_and_unknown_slugs():
    from eventyay.base.header_presets import resolve_preset_to_url, resolve_preset_thumbnail_url

    # Known defaults return static URLs
    assert resolve_preset_to_url('abstract-spheres') is not None
    assert resolve_preset_to_url('preset:abstract-spheres.jpg') is not None
    assert resolve_preset_thumbnail_url('gradient-sunset') is not None

    # Unknown legacy slugs return None so event settings can fall back
    assert resolve_preset_to_url('unknown-custom-slug') is None
    assert resolve_preset_to_url('preset:random-nonexistent') is None
    assert resolve_preset_thumbnail_url('unknown-custom-slug') is None


@pytest.mark.django_db
def test_get_preset_by_identifier(test_category):
    from eventyay.base.header_presets import get_preset_by_identifier

    # Inactive preset lookup succeeds (e.g. for events that already reference it)
    inactive_preset = EventHeaderPreset.objects.create(
        name='Retired Preset',
        category=test_category,
        image=_create_test_image(),
        is_active=False,
    )
    invalidate_preset_cache()

    found = get_preset_by_identifier(str(inactive_preset.pk))
    assert found is not None
    assert found.pk == inactive_preset.pk

    # Lookup with prefix
    found_with_prefix = get_preset_by_identifier(f'preset:{inactive_preset.pk}')
    assert found_with_prefix is not None
    assert found_with_prefix.pk == inactive_preset.pk

    # Unknown ID returns None and caches miss
    assert get_preset_by_identifier('9999999') is None
    # Second call uses cache without error
    assert get_preset_by_identifier('9999999') is None


@pytest.mark.django_db
def test_storage_error_handling_returns_none(organizer, test_category, monkeypatch):
    from django.core.files.storage import default_storage

    preset = EventHeaderPreset.objects.create(
        name='Storage Error Test',
        category=test_category,
        image=_create_test_image(),
        thumbnail=_create_test_image(400, 133),
        is_active=True,
    )
    invalidate_preset_cache()

    with scopes_disabled():
        event = Event.objects.create(
            organizer=organizer,
            name='Storage Error Event',
            slug='storage-error-event',
            date_from=now(),
            date_to=now(),
        )
        event.settings.set('logo_image', f'preset:{preset.pk}')

        def broken_url(name):
            raise Exception('Remote storage connection dropped')

        def broken_open(name, mode='rb'):
            raise Exception('Remote storage permission denied')

        monkeypatch.setattr(default_storage, 'url', broken_url)
        monkeypatch.setattr(default_storage, 'open', broken_open)

        assert event.visible_header_image_url is None
        assert event.visible_header_image_file is None


@pytest.mark.django_db
def test_form_save_failure_cleans_up_uploaded_files(test_category, monkeypatch):
    from django.core.files.storage import default_storage
    from eventyay.control.forms.header_presets import EventHeaderPresetForm

    deleted_paths = []
    original_delete = default_storage.delete

    def tracking_delete(name):
        deleted_paths.append(name)
        return original_delete(name)

    monkeypatch.setattr(default_storage, 'delete', tracking_delete)

    form = EventHeaderPresetForm(
        data={
            'name_0': 'Fail Save Preset',
            'category': test_category.pk,
            'is_active': True,
        },
        files={
            'image': _create_test_image(1200, 400),
        },
    )
    assert form.is_valid()

    def fail_save(*args, **kwargs):
        raise RuntimeError('Simulated database failure during save')

    monkeypatch.setattr(EventHeaderPreset, 'save', fail_save)

    with pytest.raises(RuntimeError):
        form.save(commit=True)

    assert len(deleted_paths) == 2
    for path in deleted_paths:
        assert not default_storage.exists(path)

