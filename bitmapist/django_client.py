from django.conf import settings

from bitmapist import *

setup_redis(
    name='default',
    host=settings.BITMAP_REDIS_HOST,
    port=settings.BITMAP_REDIS_PORT
)

set_key_prefix(settings.BITMAP_PREFIX)
set_divider(settings.BITMAP_DIVIDER)
