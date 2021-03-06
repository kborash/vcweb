from django.conf import settings


def common(request):
    return {
        'WEBSOCKET_SSL': settings.WEBSOCKET_SSL,
        'WEBSOCKET_PORT': settings.WEBSOCKET_PORT,
        'SITE_URL': settings.SITE_URL,
        'DEBUG': settings.DEBUG
    }
