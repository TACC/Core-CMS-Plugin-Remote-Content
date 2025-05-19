from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from cms.models.pluginmodel import CMSPlugin

from .constants import DEFAULT_ROOT_URL

class RemoteContent(CMSPlugin):
    remote_path = models.CharField(max_length=255)

    @property
    def full_url(self):
        """Return the full URL of the remote content"""
        source_root = getattr(settings, 'PORTAL_CONTENT_ROOT_URL', DEFAULT_ROOT_URL)
        return source_root.rstrip('/') + '/' + self.remote_path.lstrip('/')

    def __str__(self):
        return self.remote_path
