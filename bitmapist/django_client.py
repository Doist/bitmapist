from django.conf import settings

from bitmapist import (
    mark_event as _mark_event,
    mark_attribute as _mark_attribute,
    get_all_attribute_names as _get_all_attribute_names,
    get_all_event_names as _get_all_event_names,
    setup_redis,
    set_divider,
    set_key_prefix,
)

setup_redis(
    name=settings.BITMAP_REDIS_NAME,
    host=settings.BITMAP_REDIS_HOST,
    port=settings.BITMAP_REDIS_PORT
)

set_key_prefix(settings.BITMAP_PREFIX)
set_divider(settings.BITMAP_DIVIDER)


def mark_event(*args, **kwargs):
    kwargs['system'] = settings.BITMAP_REDIS_NAME
    return _mark_event(*args, **kwargs)


def mark_attribute(*args, **kwargs):
    kwargs['system'] = settings.BITMAP_REDIS_NAME
    return _mark_attribute(*args, **kwargs)


def get_all_attribute_names(*args, **kwargs):
    kwargs['system'] = settings.BITMAP_REDIS_NAME
    return _get_all_attribute_names(*args, **kwargs)


def get_all_event_names(*args, **kwargs):
    kwargs['system'] = settings.BITMAP_REDIS_NAME
    return _get_all_event_names(*args, **kwargs)
