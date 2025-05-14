from cms.models.pluginmodel import CMSPlugin
from django.db import models
from django.utils.translation import gettext_lazy as _

class RemoteContent(CMSPlugin):
    """
    Remote Content Model
    ===
    Defines at what path to load remote content
    """
    path = models.CharField(
        verbose_name=_('Path'),
        help_text=_('Path to remote content (e.g. "news/latest-news/tag/lccf/")'),
        max_length=255,
    )

    def __str__(self):
        return self.path
