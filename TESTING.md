# How to Test on [Core CMS]

[Core CMS]: https://github.com/TACC/Core-CMS

## 0. Prepare a Local Server

1. Follow [TACC/Core-CMS "Getting Started" steps](https://github.com/TACC/Core-CMS#getting-started).
2. Add middleware from [TACC/Core-CMS#873](https://github.com/TACC/Core-CMS/pull/873).
    <sup>e.g. `git fetch origin && git diff origin/main..origin/feat/support-multisite | git apply`</sup>
3. Add the following to `settings_local.py`:

    ```python
    # To let user assign News article to specific Site
    BLOG_MULTISITE = True
    ```

4. Add the following to `custom_app_settings.py`'s `CUSTOM_MIDDLEWARE` list:

    ```python
        'taccsite_cms.middleware.settings.DynamicSiteIdMiddleware',
   ```

## 1. Set Up Sites in Django Admin

Visit: http://localhost:8000/admin/sites/site/

Configure two sites:

- Site 1:\
    domain = `localhost:8000`
- Site 2:\
    domain = `127.0.0.1:8000`

## 2. Configure Settings

1. (Optional) Verify you have a working Blog/News.

    > [!NOTE]
    > This is not required — you could test regular pages — but this allows you to test using Blog/News (the kind of remote content we build this feature for).

    **And** add the following to `settings_local.py`:

    ```python
    # To let user assign News article to specific Site
    BLOG_MULTISITE = True
    ```

2. (Optional) Allow your local server to load two Sites at unique URLs.

    > [!NOTE]
    > This is not required — you could test an actual remote production server — but this allows fully local testing.

    1. Add middleware from [TACC/Core-CMS#873](https://github.com/TACC/Core-CMS/pull/873):

        ```sh
        git fetch origin && git diff origin/main..origin/feat/support-multisite | git apply
        ```

    2. Add the following to `custom_app_settings.py`'s `CUSTOM_MIDDLEWARE` list:

        ```python
            'taccsite_cms.middleware.settings.DynamicSiteIdMiddleware',
        ```

3. Add these settings to `settings_local.py`:

    ```python
    # Configure remote content settings
    PORTAL_PLUGIN_CONTENT_NETLOC = 'http://localhost:8000/'
    ```

    > [!NOTE]
    > If you are testing actual remote content, then set `PORTAL_PLUGIN_CONTENT_NETLOC` appropriately.

## 3. Create Test Content

**If** you **will** test Blog/News, [create two **articles**](http://localhost:8000/admin/djangocms_blog/post/):

1. Via Blog/News (either site):

  - Title: **Site 1 Article 1**
  - Sites: _select only_ **`localhost:8000`**

2. Via Blog/News (either site):

  - Title: **Site 2 Article 1**
  - Sites: _select only_ **`127.0.0.1:8000`**

**If** you **won't** test Blog/News, [create two **pages**](http://localhost:8000/admin/cms/page/):

1. Via localhost:8000:

    1. Create "Site 1 Page".
    2. Add text "Site 1 Page" to the page.

2. Via 127.0.0.1:8000:

    1. Create "Site 2 Page".
    2. Add text "Site 2 Page" to the page.

## 4. Test Setup

1. View articles or pages on their respective sites:

  - articles:
    1. http://localhost:8000/news/2025/05/09/site-1-article-1/
    2. http://127.0.0.1:8000/news/2025/05/09/site-2-article-1/

  - pages:
    1. http://localhost:8000/site-1-page/
    2. http://127.0.0.1:8000/site-2-page/

## 5. Test Feature

Test "Remote Content" plugin on a page on "Site 2" to load content from "Site 1".

2. For testing news articles:
   - On "Site 2", configure plugin instance to fetch: `/news/2025/05/09/site-1-article-1/`

3. For testing regular pages:
   - On "Site 2", configure plugin instance to fetch: `/site-1-page/`

4. Verify "Site 2" correctly displays the content from "Site 1":
   - Styles are applied correctly.
   - Links within remote content function properly.
   - Images have CORS error, but the URL is correct.

5. Test error handling:
   - Configure a plugin with an invalid URL and verify appropriate error messages are shown
   - Temporarily stop the localhost:8000 server and verify the plugin on 127.0.0.1:8000 gracefully handles the connection failure
