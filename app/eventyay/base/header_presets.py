import random
from contextlib import suppress
from django.core.cache import cache
from django.db.utils import OperationalError, ProgrammingError
from django.templatetags.static import static
from django.utils.translation import gettext_lazy as _

PRESET_PREFIX = 'preset:'
CACHE_KEY_ACTIVE_PRESETS = 'eventyay_active_header_presets'
CACHE_TIMEOUT = 300  # 5 minutes


def invalidate_preset_cache():
    """Invalidate cached header presets after admin modifications."""
    cache.delete(CACHE_KEY_ACTIVE_PRESETS)


def get_active_presets():
    """Return all active presets from the database, cached for performance."""
    presets = cache.get(CACHE_KEY_ACTIVE_PRESETS)
    if presets is None:
        try:
            from eventyay.base.models.event_header_preset import EventHeaderPreset
            presets = list(
                EventHeaderPreset.objects.filter(is_active=True)
                .select_related('category')
                .order_by('category_id', 'id')
            )
            cache.set(CACHE_KEY_ACTIVE_PRESETS, presets, CACHE_TIMEOUT)
        except (OperationalError, ProgrammingError):
            presets = []
    return presets


def get_active_categories():
    """Return category tuples (category_id_str, localized_name) for categories with active presets."""
    presets = get_active_presets()
    seen = {}
    for p in presets:
        if p.category_id and p.category_id not in seen:
            seen[p.category_id] = p.category.name
    result = [('all', _('All'))]
    for cat_id, cat_name in seen.items():
        result.append((str(cat_id), str(cat_name)))
    return result


def get_preset_by_id():
    """Return a dictionary of {str(preset.id): preset} for all active presets."""
    return {str(preset.id): preset for preset in get_active_presets()}


def get_random_preset_id():
    """Return a random active preset ID as a string, or '' if no active presets exist."""
    presets = get_active_presets()
    if not presets:
        return ''
    return str(random.choice(presets).id)


KNOWN_DEFAULT_PRESET_SLUGS = {
    'abstract-spheres',
    'gradient-sunset',
    'social-gathering',
    'tech-mesh',
}
CACHE_KEY_PRESET_LOOKUP_PREFIX = 'eventyay_preset_lookup:'


def get_preset_by_identifier(preset_id: str):
    """
    Look up an EventHeaderPreset by numeric database ID or image slug.
    Checks the active presets cache first, falls back to direct database query
    (including inactive presets referenced by existing events), caches misses,
    and avoids repeat queries.
    """
    if not preset_id:
        return None
    raw_id = str(preset_id).strip()
    if raw_id.startswith(PRESET_PREFIX):
        raw_id = raw_id[len(PRESET_PREFIX):]
    if not raw_id:
        return None

    active_presets = get_preset_by_id()
    if raw_id in active_presets:
        return active_presets[raw_id]

    cache_key = f'{CACHE_KEY_PRESET_LOOKUP_PREFIX}{raw_id}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached if cached != '__none__' else None

    from django.db.utils import OperationalError, ProgrammingError
    from eventyay.base.models.event_header_preset import EventHeaderPreset

    preset = None
    try:
        if raw_id.isdigit():
            preset = EventHeaderPreset.objects.filter(pk=int(raw_id)).first()
        else:
            slug = raw_id[:-4] if raw_id.endswith('.jpg') else raw_id
            possible_images = [raw_id, f'{slug}.jpg', f'header_presets/{raw_id}', f'header_presets/{slug}.jpg']
            preset = EventHeaderPreset.objects.filter(image__in=possible_images).first()
    except (OperationalError, ProgrammingError):
        preset = None

    cache.set(cache_key, preset if preset is not None else '__none__', CACHE_TIMEOUT)
    return preset


def _resolve_preset_url(preset_id: str, use_thumbnail=False):
    """Internal helper to resolve a preset to its full or thumbnail URL."""
    if not preset_id:
        return None

    raw_id = str(preset_id).strip()
    if raw_id.startswith(PRESET_PREFIX):
        raw_id = raw_id[len(PRESET_PREFIX):]
    if not raw_id:
        return None

    from django.core.files.storage import default_storage

    preset = get_preset_by_identifier(raw_id)
    if preset:
        target_file = preset.thumbnail if use_thumbnail and preset.thumbnail else preset.image
        if target_file:
            with suppress(Exception):
                return default_storage.url(target_file.name)

    # For legacy slugs not found in the DB, only serve static assets for known defaults
    slug = raw_id[:-4] if raw_id.endswith('.jpg') else raw_id
    if slug in KNOWN_DEFAULT_PRESET_SLUGS:
        folder = 'thumbs/' if use_thumbnail else ''
        return static(f'eventyay-common/images/header_presets/{folder}{slug}.jpg')

    return None


def resolve_preset_to_url(preset_id: str):
    """Given a preset ID (integer database ID or legacy slug), return the image URL."""
    return _resolve_preset_url(preset_id, use_thumbnail=False)


def resolve_preset_thumbnail_url(preset_id: str):
    """Given a preset ID, return the storage URL for the thumbnail image."""
    return _resolve_preset_url(preset_id, use_thumbnail=True)


def is_preset_value(raw):
    """Check if a settings value or path is a preset reference."""
    return isinstance(raw, str) and raw.startswith(PRESET_PREFIX)


def extract_preset_id(raw):
    """Extract the preset ID from a 'preset:<id>' string."""
    if is_preset_value(raw):
        return raw[len(PRESET_PREFIX):]
    return None
