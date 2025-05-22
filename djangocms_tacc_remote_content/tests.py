from django.test import TestCase, override_settings
from django.conf import settings
from unittest.mock import patch, MagicMock
from bs4 import BeautifulSoup

from cms.api import add_plugin
from cms.models import Placeholder
from cms.plugin_rendering import ContentRenderer

from .models import RemoteContent
from .cms_plugins import RemoteContentPlugin
from . import settings as defaults

class RemoteContentPluginTests(TestCase):
    def setUp(self):
        # Ensure we're using default settings
        if hasattr(settings, 'PORTAL_PLUGIN_CONTENT_NETLOC'):
            delattr(settings, 'PORTAL_PLUGIN_CONTENT_NETLOC')

        self.placeholder = Placeholder.objects.create(slot="test")
        self.plugin = add_plugin(
            self.placeholder,
            RemoteContentPlugin,
            "en",
            remote_path="/about/staff"
        )
        self.plugin_instance = self.plugin.get_plugin_class_instance()
        self.renderer = ContentRenderer(request=None)

    def test_plugin_context(self):
        """Test plugin generates correct context"""
        context = self.plugin_instance.render({}, self.plugin, None)
        self.assertIn("instance", context)
        self.assertEqual(context["instance"], self.plugin)

    def test_custom_source_root(self):
        """Test that plugin respects custom PORTAL_PLUGIN_CONTENT_NETLOC setting"""
        with self.settings(PORTAL_PLUGIN_CONTENT_NETLOC="https://example.com/"):
            source_root = self.plugin_instance.get_source_root()
            self.assertEqual(source_root, "https://example.com/")

    def test_default_source_root(self):
        """Test plugin uses default netloc when setting is not provided"""
        with self.settings(PORTAL_PLUGIN_CONTENT_NETLOC=None):
            delattr(settings, 'PORTAL_PLUGIN_CONTENT_NETLOC')  # Force setting to be truly unset
            source_root = self.plugin_instance.get_source_root()
            self.assertEqual(source_root, defaults.NETLOC)

    @patch("requests.get")
    def test_content_fetching_success(self, mock_get):
        """Test successful content fetching"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<div>Test Content</div>"
        mock_get.return_value = mock_response

        url = "https://example.com/about"
        content = self.plugin_instance.get_source_markup(url)

        self.assertEqual(content, "<div>Test Content</div>")
        mock_get.assert_called_once_with(url)

    @patch("requests.get")
    def test_content_fetching_failure(self, mock_get):
        """Test failed content fetching"""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        url = "https://example.com/nonexistent"
        content = self.plugin_instance.get_source_markup(url)

        self.assertIsNone(content)
        mock_get.assert_called_once_with(url)

    def test_url_building_path_formats(self):
        """Test URL building with various path formats"""
        with self.settings(PORTAL_PLUGIN_CONTENT_NETLOC=None):
            test_cases = [
                # ( input path,     expected url )
                ( "/about/staff",   f"{defaults.NETLOC}about/staff" ),
                ( "/about/staff/",  f"{defaults.NETLOC}about/staff/" ),
                ( "about/staff",    f"{defaults.NETLOC}about/staff" ),
                ( "about/staff/",   f"{defaults.NETLOC}about/staff/" ),
            ]

        for input_path, expected_url in test_cases:
            with self.subTest(input_path=input_path):
                instance = RemoteContent(remote_path=input_path)
                actual_url = self.plugin_instance.build_source_url(instance)
                self.assertEqual(
                    actual_url,
                    expected_url,
                    f"For path '{input_path}', expected URL '{expected_url}' but got '{actual_url}'"
                )

    @override_settings(PORTAL_PLUGIN_CONTENT_NETLOC="https://example.com/path/")
    def test_url_building_with_complex_root(self):
        """Test URL building with different source root configurations"""
        instance = RemoteContent(remote_path="/about/staff")
        full_url = self.plugin_instance.build_source_url(instance)

        # Should handle source roots with paths and trailing slashes correctly
        self.assertEqual(full_url, "https://example.com/path/about/staff")

        # Test with a different instance to ensure path joining works
        instance2 = RemoteContent(remote_path="no/leading/slash")
        full_url2 = self.plugin_instance.build_source_url(instance2)
        self.assertEqual(full_url2, "https://example.com/path/no/leading/slash")

    @patch("requests.get")
    def test_content_rendering(self, mock_get):
        """Test that plugin correctly renders fetched content"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<div>Test Content</div>"
        mock_get.return_value = mock_response

        context = self.plugin_instance.render({}, self.plugin, None)
        html = self.renderer.render_plugin(self.plugin, context)
        self.assertIn("Test Content", html)

    def test_keep_relative_paths(self):
        """Test that elements matching CSS selectors from settings keep relative paths"""
        test_selectors = ['.pagination a', '[data-use-relative-url]']
        test_markup = '''
            <div>
                <nav class="pagination">
                    <span class="current">Page 1 of 37</span>
                    <a href="?page=2">Next &gt;</a>
                </nav>
                <div class="content">
                    <a href="/path/to/resource" data-use-relative-url>Resource</a>
                    <a href="/docs/guide.html">Guide</a>
                    <img src="/path/to/image.jpg" data-use-relative-url>
                    <img src="/images/photo.jpg">
                </div>
            </div>
        '''

        with self.settings(PORTAL_PLUGIN_CONTENT_USE_RELATIVE_PATHS=test_selectors):
            result = self.plugin_instance.build_client_markup(test_markup, defaults.NETLOC)
            soup = BeautifulSoup(result, 'html.parser')

            # Pagination links should remain relative
            pagination_link = soup.select_one('.pagination a')
            self.assertEqual(pagination_link['href'], '?page=2')
            self.assertNotIn('target', pagination_link.attrs)
            self.assertNotIn('crossorigin', pagination_link.attrs)

            # [data-use-relative-url] links should remain relative
            custom_link = soup.find('a', attrs={'data-use-relative-url': True})
            self.assertEqual(custom_link['href'], '/path/to/resource')
            self.assertNotIn('target', custom_link.attrs)
            self.assertNotIn('crossorigin', custom_link.attrs)

            # Other links should be absolute
            docs_link = soup.find('a', href=defaults.NETLOC + '/docs/guide.html')
            self.assertEqual(docs_link['href'], defaults.NETLOC + '/docs/guide.html')
            self.assertEqual(docs_link['target'], '_blank')

            # [data-use-relative-url] images should remain relative
            custom_img = soup.find('img', attrs={'data-use-relative-url': True})
            self.assertEqual(custom_img['src'], '/path/to/image.jpg')
            self.assertNotIn('crossorigin', custom_img.attrs)

            # Other images should be absolute
            other_img = soup.find('img', src=defaults.NETLOC + '/images/photo.jpg')
            self.assertEqual(other_img['src'], defaults.NETLOC + '/images/photo.jpg')
            self.assertEqual(other_img['crossorigin'], 'anonymous')
