import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urlencode, parse_qsl
import urllib.parse

from django.conf import settings
from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool
from django.utils.translation import gettext_lazy as _

from .models import RemoteContent

logger = logging.getLogger(f"portal.{__name__}")

@plugin_pool.register_plugin
class RemoteContentPlugin(CMSPluginBase):
    """
    TACC Site > "Remote Content" Plugin
    Plugin for fetching and displaying remote content from TACC sites
    """
    module = 'TACC Site'
    model = RemoteContent
    name = _('Remote Content')
    render_template = 'remote_content.html'
    cache = True

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
        source_root = getattr(settings, 'PORTAL_REMOTE_CONTENT_SOURCE_ROOT', 'https://tacc.utexas.edu/')
        page = instance.remote_path

        root_parts = urllib.parse.urlsplit(source_root)
        page_parts = urllib.parse.urlsplit(page)

        url_parts = urllib.parse.ParseResult(
            scheme=root_parts.scheme,
            netloc=root_parts.netloc,
            path=root_parts.path + page_parts.path,
            params=None,
            query=page_parts.query,
            fragment=page_parts.fragment
        )

        source_url = urllib.parse.urlunparse(url_parts)
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

        source = urlparse(settings.PORTAL_REMOTE_CONTENT_SOURCE_ROOT)
        source_site = source.scheme + '://' + source.netloc
        
        context['markup'] = self.build_client_markup(source_markup, source_site)
        return context
