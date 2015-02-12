from django.apps import AppConfig
from django.conf import settings

import logging
import mimetypes

logger = logging.getLogger(__name__)


class VcwebCoreConfig(AppConfig):
    name = 'vcweb.core'
    verbose_name = 'vcweb core services'

    def ready(self):
        logger.debug("vcweb core initialized in %s mode, initializing mimetypes", settings.ENVIRONMENT)
        mimetypes.init()

