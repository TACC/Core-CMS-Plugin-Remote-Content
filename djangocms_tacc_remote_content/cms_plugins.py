import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urlsplit, urlunparse, ParseResult

from django.conf import settings
from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool
from django.utils.translation import gettext_lazy as _

from .models import RemoteContent
from .forms import RemoteContentForm, fieldsets
from .constants import DEFAULT_ROOT_URL

logger = logging.getLogger(f"portal.{__name__}")

@plugin_pool.register_plugin
class RemoteContentPlugin(CMSPluginBase):
    """
    TACC Site > "Remote Content" Plugin
    Plugin for fetching and displaying remote content from TACC sites
    """
    module = 'TACC Site'
    model = RemoteContent
    form = RemoteContentForm
    name = _('Remote Content')
    render_template = 'remote_content.html'
    cache = True
    fieldsets = fieldsets
    readonly_fields = ['full_url']

    def full_url(self, obj):
        """Admin UI display of the full URL"""
        return self.build_source_url(obj)
    full_url.short_description = _('Full URL')

    def get_source_root(self):
        """Get the source root URL from settings or default"""
        return getattr(settings, 'PORTAL_CONTENT_ROOT_URL', DEFAULT_ROOT_URL)

    def get_source_markup(self, url):
        """Fetch content from remote URL"""
        response = requests.get(url)
        if response.status_code == 200:
            return response.text
        else:
            logger.error(f"Failed to fetch content from {url}")
            return None

    def build_source_url(self, instance):
        """Build the source URL from settings and instance path"""
        source_root = self.get_source_root()
        page = instance.remote_path

        root_parts = urlsplit(source_root)
        page_parts = urlsplit(page)

        root_path = root_parts.path.rstrip('/')
        page_path = page_parts.path.lstrip('/')

        url_parts = ParseResult(
            scheme=root_parts.scheme,
            netloc=root_parts.netloc,
            path=f"{root_path}/{page_path}",
            params=None,
            query=page_parts.query,
            fragment=page_parts.fragment
        )

        source_url = urlunparse(url_parts)
        logger.debug(f"Attempting to fetch: {source_url}")
        return source_url

    def build_client_markup(self, source_markup, source_site):
        """Transform remote content for local display"""
        if not source_markup:
            return None

        soup = BeautifulSoup(source_markup, 'html.parser')

        # Transform resource URLs
        for tag in soup.find_all(src=True):
            if tag['src'].startswith('/'):
                tag['crossorigin'] = 'anonymous'
                tag['src'] = source_site + tag['src']

        # Transform reference URLs
        for tag in soup.find_all(href=True):
            href = tag['href']
            if ':' in href or href.startswith('#'):
                continue

            if tag.name == 'link':
                tag['crossorigin'] = 'anonymous'
                tag['href'] = source_site + href

        return str(soup)

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)

        source_url = self.build_source_url(instance)
        source_markup = self.get_source_markup(source_url)

        if source_markup is None and settings.DEBUG:
            context['error_string'] = f'Unable to fetch content from {source_url}'
            return context

        source = urlparse(settings.PORTAL_CONTENT_ROOT_URL)
        source_site = source.scheme + '://' + source.netloc
        context['markup'] = self.build_client_markup(source_markup, source_site)

        if context['markup'] is None and settings.DEBUG:
            context['error_string'] = 'Error processing remote content'
            return context

        return context
