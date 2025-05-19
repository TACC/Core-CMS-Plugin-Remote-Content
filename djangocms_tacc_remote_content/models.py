from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from cms.models.pluginmodel import CMSPlugin

from .constants import DEFAULT_NETLOC

class RemoteContent(CMSPlugin):
    remote_path = models.CharField(max_length=255)

    def __str__(self):
        return self.remote_path
