from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from cms.models.pluginmodel import CMSPlugin

from .constants import DEFAULT_SOURCE_ROOT

class RemoteContent(CMSPlugin):
    remote_path = models.CharField(max_length=255)

    def get_source_root(self):
        """Get the source root URL from settings or default"""
        return getattr(settings, 'PORTAL_REMOTE_CONTENT_SOURCE_ROOT', DEFAULT_SOURCE_ROOT)

    def __str__(self):
        """Return the full URL of the remote content"""
        return self.get_source_root().rstrip('/') + '/' + self.remote_path.lstrip('/')
