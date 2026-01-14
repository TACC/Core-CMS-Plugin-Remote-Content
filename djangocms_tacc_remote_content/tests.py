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
            remote_path="/about/about-tacc"
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
                ( "/about/about-tacc",   f"{defaults.NETLOC}about/about-tacc" ),
                ( "/about/about-tacc/",  f"{defaults.NETLOC}about/about-tacc/" ),
                ( "about/about-tacc",    f"{defaults.NETLOC}about/about-tacc" ),
                ( "about/about-tacc/",   f"{defaults.NETLOC}about/about-tacc/" ),
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
        instance = RemoteContent(remote_path="/about/about-tacc")
        full_url = self.plugin_instance.build_source_url(instance)

        # Should handle source roots with paths and trailing slashes correctly
        self.assertEqual(full_url, "https://example.com/path/about/about-tacc")

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

    def test_path_transformation(self):
        """Test that relative and absolute paths are transformed correctly"""
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
                    <img src="/images/photo2.jpg" srcset=" /images/photo2-576.jpg 576w, /images/photo2-768.jpg 768w, /images/photo2-992.jpg 992w ">
                    <img src="/images/photo3.jpg" srcset="https://example.com/absolute.jpg 1x">
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
            self.assertNotIn('srcset', other_img.attrs)

            # Image with relative srcset should transform both src and srcset
            imgs_with_srcset = [img for img in soup.find_all('img', srcset=True) if 'data-use-relative-url' not in img.attrs]
            img_with_srcset = [img for img in imgs_with_srcset if img['srcset'].startswith(defaults.NETLOC)][0]
            self.assertEqual(img_with_srcset['src'], defaults.NETLOC + '/images/photo2.jpg')
            expected_srcset = f"{defaults.NETLOC}/images/photo2-576.jpg 576w, {defaults.NETLOC}/images/photo2-768.jpg 768w, {defaults.NETLOC}/images/photo2-992.jpg 992w"
            self.assertEqual(img_with_srcset['srcset'], expected_srcset)

            # Image with absolute srcset should transform src but leave srcset unchanged
            img_absolute_srcset = [img for img in imgs_with_srcset if 'https://' in img['srcset']][0]
            self.assertEqual(img_absolute_srcset['src'], defaults.NETLOC + '/images/photo3.jpg')
            self.assertEqual(img_absolute_srcset['srcset'], 'https://example.com/absolute.jpg 1x')

    def test_query_parameter_handling(self):
        """Test handling of query parameters in URLs"""
        from django.test import RequestFactory

        instance = RemoteContent(remote_path="/news")
        test_cases = [
            # (request URL, expected params in result, unexpected params in result)
            ('/?page=2', ['page=2'], []), # basic content parameter
            ('/?page=2&toolbar_on', ['page=2'], ['toolbar_on']), # CMS param should be filtered
            ('/?structure&other_param=test', ['other_param=test'], ['structure']), # mixed params
            ('/?preview&page=3&toolbar_off', ['page=3'], ['preview', 'toolbar_off']), # multiple CMS params
            ('/?edit&tag=featured', ['tag=featured'], ['edit']), # edit param filtered
        ]

        for test_url, expected_params, unexpected_params in test_cases:
            with self.subTest(test_url=test_url):
                request = RequestFactory().get(test_url)
                url = self.plugin_instance.build_source_url(instance, request)
                
                # Check expected parameters are present
                for param in expected_params:
                    self.assertIn(param, url, f"Expected parameter '{param}' missing from URL: {url}")
                
                # Check CMS parameters are filtered out
                for param in unexpected_params:
                    self.assertNotIn(param, url, f"Unexpected parameter '{param}' found in URL: {url}")
