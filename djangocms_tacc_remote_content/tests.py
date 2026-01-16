from django.test import TestCase, override_settings
from django.conf import settings
from unittest.mock import patch, MagicMock
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from cms.api import add_plugin
from cms.models import Placeholder
from cms.plugin_rendering import ContentRenderer

from .models import RemoteContent
from .cms_plugins import RemoteContentPlugin
from . import settings as defaults

class RemoteContentPluginTests(TestCase):
    def setUp(self):
        # To ensure we're using default settings
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
            # To force setting to be truly unset
            # ???: Redundant? I see `setUp()` does this already
            delattr(settings, 'PORTAL_PLUGIN_CONTENT_NETLOC')

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
        # Expect remote path has leading slash
        instance = RemoteContent(remote_path="/about/about-tacc")
        full_url = self.plugin_instance.build_source_url(instance)
        self.assertEqual(full_url, "https://example.com/path/about/about-tacc")

        # Consider remote path without leading slash
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
                    <img src="https://example.com/absolute-src.jpg" srcset="/images/relative-in-srcset.jpg 1x">
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
            expected_docs_url = urljoin(defaults.NETLOC, '/docs/guide.html')
            docs_link = soup.find('a', href=expected_docs_url)
            self.assertIsNotNone(docs_link, f"Link with href '{expected_docs_url}' not found")
            self.assertEqual(docs_link['href'], expected_docs_url)
            self.assertEqual(docs_link['target'], '_blank')

            # [data-use-relative-url] images should remain relative
            custom_img = soup.find('img', attrs={'data-use-relative-url': True})
            self.assertEqual(custom_img['src'], '/path/to/image.jpg')
            self.assertNotIn('crossorigin', custom_img.attrs)

            # Other images should be absolute
            expected_img_url = urljoin(defaults.NETLOC, '/images/photo.jpg')
            other_img = soup.find('img', src=expected_img_url)
            self.assertIsNotNone(other_img, f"Image with src '{expected_img_url}' not found")
            self.assertEqual(other_img['src'], expected_img_url)
            self.assertEqual(other_img['crossorigin'], 'anonymous')
            self.assertNotIn('srcset', other_img.attrs)

            # Image with relative srcset should transform both src and srcset
            imgs_with_srcset = [img for img in soup.find_all('img', srcset=True) if 'data-use-relative-url' not in img.attrs]
            img_with_srcset = [img for img in imgs_with_srcset if img['srcset'].startswith(defaults.NETLOC.rstrip('/'))][0]
            expected_img2_url = urljoin(defaults.NETLOC, '/images/photo2.jpg')
            self.assertEqual(img_with_srcset['src'], expected_img2_url)
            expected_srcset = f"{urljoin(defaults.NETLOC, '/images/photo2-576.jpg')} 576w, {urljoin(defaults.NETLOC, '/images/photo2-768.jpg')} 768w, {urljoin(defaults.NETLOC, '/images/photo2-992.jpg')} 992w"
            self.assertEqual(img_with_srcset['srcset'], expected_srcset)

            # Image with absolute srcset should transform src but leave srcset unchanged
            expected_img3_url = urljoin(defaults.NETLOC, '/images/photo3.jpg')
            img_absolute_srcset = soup.find('img', src=expected_img3_url)
            self.assertIsNotNone(img_absolute_srcset, "Image with absolute srcset not found")
            self.assertEqual(img_absolute_srcset['src'], expected_img3_url)
            self.assertEqual(img_absolute_srcset['srcset'], 'https://example.com/absolute.jpg 1x')

            # Image with absolute src but relative srcset should transform srcset independently
            img_independent = soup.find('img', src='https://example.com/absolute-src.jpg')
            self.assertIsNotNone(img_independent, "Image with absolute src and relative srcset not found")
            self.assertEqual(img_independent['src'], 'https://example.com/absolute-src.jpg')
            expected_srcset_url = urljoin(defaults.NETLOC, '/images/relative-in-srcset.jpg')
            self.assertEqual(img_independent['srcset'], f"{expected_srcset_url} 1x")

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

    def test_transform_srcset(self):
        """Test transform_srcset function with various srcset formats"""
        source_site = "https://example.com"
        source_url = f"{source_site}/"

        test_cases = [
            # (input srcset, expected output)
            (
                " /images/photo-576.jpg 576w, /images/photo-768.jpg 768w, /images/photo-992.jpg 992w ",
                f"{source_site}/images/photo-576.jpg 576w, {source_site}/images/photo-768.jpg 768w, {source_site}/images/photo-992.jpg 992w"
            ),
            (
                "/images/photo-576.jpg 576w, /images/photo-768.jpg 768w",
                f"{source_site}/images/photo-576.jpg 576w, {source_site}/images/photo-768.jpg 768w"
            ),
            (
                "/images/photo.jpg 1x, /images/photo-2x.jpg 2x",
                f"{source_site}/images/photo.jpg 1x, {source_site}/images/photo-2x.jpg 2x"
            ),
            (
                "/images/photo.jpg",
                f"{source_site}/images/photo.jpg"
            ),
            (
                "https://other.com/photo.jpg 1x, /images/local.jpg 2x",
                f"https://other.com/photo.jpg 1x, {source_site}/images/local.jpg 2x"
            ),
            (
                "/images/photo-576.jpg 576w",
                f"{source_site}/images/photo-576.jpg 576w"
            ),
        ]

        for input_srcset, expected_output in test_cases:
            with self.subTest(input_srcset=input_srcset):
                result = self.plugin_instance.transform_srcset(input_srcset, source_url)
                self.assertEqual(result, expected_output)

    def test_transform_srcset_edge_cases(self):
        """Test transform_srcset function with edge cases"""
        source_site = "https://example.com"
        source_url = f"{source_site}/"

        # Permit empty or whitespace-only srcset
        self.assertIsNone(self.plugin_instance.transform_srcset("", source_url))
        self.assertIsNone(self.plugin_instance.transform_srcset("   ", source_url))
        self.assertIsNone(self.plugin_instance.transform_srcset(" , , ", source_url))

        # Permit `None` input
        self.assertIsNone(self.plugin_instance.transform_srcset(None, source_url))

        # Do NOT change absolute URLs
        result = self.plugin_instance.transform_srcset(
            "https://other.com/photo.jpg 1x, https://other.com/photo-2x.jpg 2x",
            source_url
        )
        self.assertEqual(result, "https://other.com/photo.jpg 1x, https://other.com/photo-2x.jpg 2x")

        # Do NOT change protocol-relative URLs
        result = self.plugin_instance.transform_srcset(
            "//www.youtube.com/embed/6sl9Rbh5VhY 1x, //example.com/image.jpg 2x",
            source_url
        )
        self.assertEqual(result, "//www.youtube.com/embed/6sl9Rbh5VhY 1x, //example.com/image.jpg 2x")

    def test_protocol_relative_urls(self):
        """Test that protocol-relative URLs are not transformed in src, srcset, and href"""
        source_site = "https://example.com"
        source_url = f"{source_site}/"
        test_markup = '''
            <div>
                <img src="//www.youtube.com/embed/6sl9Rbh5VhY">
                <img src="/images/local.jpg" srcset="//cdn.example.com/image.jpg 1x, /images/local.jpg 2x">
                <a href="//external.com/page">External Link</a>
                <a href="/local/page">Local Link</a>
            </div>
        '''
        result = self.plugin_instance.build_client_markup(test_markup, source_url)
        soup = BeautifulSoup(result, 'html.parser')

        # Protocol-relative src should remain unchanged
        youtube_img = soup.find('img', src='//www.youtube.com/embed/6sl9Rbh5VhY')
        self.assertIsNotNone(youtube_img, "Protocol-relative src was transformed")
        self.assertEqual(youtube_img['src'], '//www.youtube.com/embed/6sl9Rbh5VhY')

        # Protocol-relative URLs in srcset should remain unchanged, but relative URLs should be transformed
        img_with_srcset = soup.find('img', srcset=True)
        self.assertIsNotNone(img_with_srcset)
        # Protocol-relative URL should remain unchanged
        self.assertIn('//cdn.example.com/image.jpg', img_with_srcset['srcset'])
        # Relative URL should be transformed
        self.assertIn(f'{source_site}/images/local.jpg', img_with_srcset['srcset'])

        # Protocol-relative href should remain unchanged
        external_link = soup.find('a', href='//external.com/page')
        self.assertIsNotNone(external_link, "Protocol-relative href was transformed")
        self.assertEqual(external_link['href'], '//external.com/page')
        self.assertNotIn('target', external_link.attrs)
        self.assertNotIn('crossorigin', external_link.attrs)

        # Relative href should be transformed
        local_link = soup.find('a', href=f'{source_site}/local/page')
        self.assertIsNotNone(local_link, "Relative href was not transformed")
        self.assertEqual(local_link['href'], f'{source_site}/local/page')
        self.assertEqual(local_link['target'], '_blank')

    def test_is_relative_path(self):
        """Test the is_relative_path helper method"""
        # Should return True for relative paths
        self.assertTrue(self.plugin_instance.is_relative_path('/images/photo.jpg'))
        self.assertTrue(self.plugin_instance.is_relative_path('./images/photo.jpg'))
        self.assertTrue(self.plugin_instance.is_relative_path('../images/photo.jpg'))
        self.assertTrue(self.plugin_instance.is_relative_path('?page=2'))
        self.assertTrue(self.plugin_instance.is_relative_path('images/photo.jpg'))

        # Should return False for absolute URLs
        self.assertFalse(self.plugin_instance.is_relative_path('https://example.com/image.jpg'))
        self.assertFalse(self.plugin_instance.is_relative_path('http://example.com/image.jpg'))

        # Should return False for protocol-relative URLs
        self.assertFalse(self.plugin_instance.is_relative_path('//www.youtube.com/embed/6sl9Rbh5VhY'))
        self.assertFalse(self.plugin_instance.is_relative_path('//example.com/image.jpg'))

        # Should return False for anchor links
        self.assertFalse(self.plugin_instance.is_relative_path('#anchor'))
        self.assertFalse(self.plugin_instance.is_relative_path('#section'))

        # Should return False for empty/None
        self.assertFalse(self.plugin_instance.is_relative_path(''))
        self.assertFalse(self.plugin_instance.is_relative_path(None))

    def test_path_relative_urls(self):
        """Test that path-relative URLs (./ and ../) are correctly resolved"""
        source_site = "https://example.com"
        
        test_cases = [
            # (source_url_path, expected_same_dir_base, expected_parent_dir_base)
            ("/", f"{source_site}/", f"{source_site}/"),  # Root level
            ("/page/", f"{source_site}/page/", f"{source_site}/"),  # Single-level path
            ("/news/article/", f"{source_site}/news/article/", f"{source_site}/news/"),  # Nested path
        ]
        
        for source_url_path, expected_same_dir_base, expected_parent_dir_base in test_cases:
            with self.subTest(source_url_path=source_url_path):
                source_url = f"{source_site}{source_url_path}"
                test_markup = '''
                    <div>
                        <img src="./images/photo.jpg">
                        <img src="../images/photo.jpg">
                        <img src="/images/photo.jpg" srcset="./images/photo-576.jpg 576w, ../images/photo-768.jpg 768w">
                        <a href="./page.html">Same Directory</a>
                        <a href="../page.html">Parent Directory</a>
                        <a href="/absolute/page.html">Absolute Path</a>
                    </div>
                '''
                result = self.plugin_instance.build_client_markup(test_markup, source_url)
                soup = BeautifulSoup(result, 'html.parser')
                
                # ./images/photo.jpg should resolve relative to source URL
                expected_same_dir = f"{expected_same_dir_base}images/photo.jpg"
                img_same_dir = soup.find('img', src=expected_same_dir)
                self.assertIsNotNone(img_same_dir, f"./images/photo.jpg from {source_url_path} was not correctly resolved")
                self.assertEqual(img_same_dir['src'], expected_same_dir)
                
                # ../images/photo.jpg should resolve to parent directory
                expected_parent_dir = f"{expected_parent_dir_base}images/photo.jpg"
                img_parent_dir = soup.find('img', src=expected_parent_dir)
                self.assertIsNotNone(img_parent_dir, f"../images/photo.jpg from {source_url_path} was not correctly resolved")
                self.assertEqual(img_parent_dir['src'], expected_parent_dir)
                
                # srcset with path-relative URLs
                img_with_srcset = soup.find('img', srcset=True)
                self.assertIsNotNone(img_with_srcset)
                self.assertIn(f'{expected_same_dir_base}images/photo-576.jpg 576w', img_with_srcset['srcset'])
                self.assertIn(f'{expected_parent_dir_base}images/photo-768.jpg 768w', img_with_srcset['srcset'])
                
                # ./page.html should resolve relative to source URL
                expected_same_dir_page = f"{expected_same_dir_base}page.html"
                link_same_dir = soup.find('a', href=expected_same_dir_page)
                self.assertIsNotNone(link_same_dir, f"./page.html from {source_url_path} was not correctly resolved")
                self.assertEqual(link_same_dir['href'], expected_same_dir_page)
                
                # ../page.html should resolve to parent directory
                expected_parent_dir_page = f"{expected_parent_dir_base}page.html"
                link_parent_dir = soup.find('a', href=expected_parent_dir_page)
                self.assertIsNotNone(link_parent_dir, f"../page.html from {source_url_path} was not correctly resolved")
                self.assertEqual(link_parent_dir['href'], expected_parent_dir_page)
                
                # /absolute/page.html should resolve the same for all
                link_absolute = soup.find('a', href=f'{source_site}/absolute/page.html')
                self.assertIsNotNone(link_absolute, "/absolute/page.html was not correctly resolved")
                self.assertEqual(link_absolute['href'], f'{source_site}/absolute/page.html')
