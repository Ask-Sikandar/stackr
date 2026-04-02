"""
ASGI config — routes HTTP traffic to Django and WebSocket traffic to Channels.
"""
import os

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

django_asgi_app = get_asgi_application()

from apps.ai.routing import websocket_urlpatterns  # noqa: E402 — must be after django setup

ws_stack = URLRouter(websocket_urlpatterns)

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": ws_stack,
    }
)
