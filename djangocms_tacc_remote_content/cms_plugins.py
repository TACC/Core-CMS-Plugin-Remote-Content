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
from . import settings as defaults

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
        return getattr(settings, 'PORTAL_PLUGIN_CONTENT_NETLOC', defaults.NETLOC)

    def get_source_markup(self, url):
        """Fetch content from remote URL"""
        response = requests.get(url)
        if response.status_code == 200:
            return response.text
        else:
            logger.error(f"Failed to fetch content from {url}")
            return None

    def build_source_url(self, instance, request=None):
        """Build the source URL from settings and instance path"""
        source_root = self.get_source_root()
        page = instance.remote_path

        root_parts = urlsplit(source_root)
        page_parts = urlsplit(page)

        # CMS pages can load for editors with these query parameters
        cms_params = {'edit', 'toolbar_on', 'toolbar_off', 'structure', 'preview'}

        query_params = page_parts.query
        if request and request.GET:
            filtered_params = {
                key: value for key, value in request.GET.items()
                if key not in cms_params
            }
            if filtered_params:
                request_query = '&'.join(f"{key}={value}" for key, value in filtered_params.items())
                query_params = f"{query_params}&{request_query}" if query_params else request_query

        url_parts = ParseResult(
            scheme=root_parts.scheme,
            netloc=root_parts.netloc,
            path=f"{root_parts.path.rstrip('/')}/{page_parts.path.lstrip('/')}",
            params=None,
            query=query_params,
            fragment=page_parts.fragment
        )

        source_url = urlunparse(url_parts)
        logger.debug(f"Attempting to fetch: {source_url}")
        return source_url

    def should_keep_relative(self, element, config):
        """Determine if element should keep relative URLs based on setting"""
        if isinstance(config, bool):
            return config
        if isinstance(config, (list, tuple)):
            root = element
            while root.parent:
                root = root.parent
            for selector in config:
                if element in root.select(selector):
                    return True
        return False

    def transform_srcset(self, srcset, source_site):
        """
        Transform relative URLs in a srcset attribute to absolute URLs.

        Args:
            srcset: A srcset string that may contain multiple URLs separated by commas,
                    e.g., " /images/photo-576.jpg 576w, /images/photo-768.jpg 768w "
            source_site: The base URL to prepend to relative URLs (e.g., "https://example.com")

        Returns:
            A transformed srcset string with relative URLs converted to absolute URLs,
            or None if srcset is empty or contains no valid parts.
        """
        if not srcset:
            return None

        # srcset can have multiple URLs: "url1 descriptor1, url2 descriptor2, ..."
        # Transform each URL individually
        parts = []
        for part in srcset.split(','):
            part = part.strip()
            if not part:
                continue
            # Extract URL (everything before the first space or end of string)
            space_idx = part.find(' ')
            if space_idx > 0:
                url = part[:space_idx]
                descriptor = part[space_idx:]
            else:
                url = part
                descriptor = ''

            # Transform relative URLs
            if url.startswith('/'):
                url = source_site + url

            parts.append(url + descriptor)

        if parts:
            return ', '.join(parts)
        return None

    def build_client_markup(self, source_markup, source_site):
        """Transform remote content for local display"""
        if not source_markup:
            return None

        soup = BeautifulSoup(source_markup, 'html.parser')

        use_relative = getattr(settings, 'PORTAL_PLUGIN_CONTENT_USE_RELATIVE_PATHS', defaults.USE_RELATIVE_PATHS)

        # To transform resource URLs
        for tag in soup.find_all(src=True):
            if tag['src'].startswith('/'):
                if not self.should_keep_relative(tag, use_relative):
                    tag['crossorigin'] = 'anonymous'
                    tag['src'] = source_site + tag['src']

                    srcset = tag.get('srcset')
                    if srcset:
                        transformed_srcset = self.transform_srcset(srcset, source_site)
                        if transformed_srcset:
                            tag['srcset'] = transformed_srcset

        # To transform reference URLs
        for tag in soup.find_all(href=True):
            href = tag['href']
            # To skip absolute URLs and anchors
            if '://' in href or href.startswith('#'):
                continue

            if not self.should_keep_relative(tag, use_relative):
                tag['crossorigin'] = 'anonymous'
                tag['href'] = source_site + href
                tag['target'] = '_blank'

        return str(soup)

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)

        source_root = self.get_source_root()
        source_url = self.build_source_url(instance, context.get('request'))
        source_markup = self.get_source_markup(source_url)

        if source_markup is None and settings.DEBUG:
            context['error_string'] = f'Unable to fetch content from {source_url}'
            return context

        source = urlparse(source_root)
        source_site = source.scheme + '://' + source.netloc
        context['markup'] = self.build_client_markup(source_markup, source_site)

        if context['markup'] is None and settings.DEBUG:
            context['error_string'] = 'Error processing remote content'
            return context

        return context
