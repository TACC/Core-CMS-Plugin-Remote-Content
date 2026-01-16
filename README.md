## Texas Advanced Computing Center
# Django CMS Plugin: Remote Content

This plugin fetches and displays content from remote TACC URLs. It was converted from the Core-CMS remote_content app into a Django CMS plugin.

- __Distribution Name__: `djangocms-tacc-remote-content`
- __Package Name__: `djangocms_tacc_remote_content`
- __Class Name__: `RemoteContent`
- __Plugin Name__: "Remote Content"

## Quick Start

1. Install the package:

    ```bash
    pip install djangocms-tacc-remote-content
    ```

2. Add to INSTALLED_APPS in your Django project's settings:

    ```python
    INSTALLED_APPS = [
       ...
       'djangocms_tacc_remote_content',
       ...
    ]
    ```

3. Run migrations:

    ```bash
    python manage.py migrate djangocms_tacc_remote_content
    ```

4. Configure the base URL for remote content in your settings (optional):

    ```python
    PORTAL_PLUGIN_CONTENT_NETLOC = 'https://tacc.utexas.edu/'
    ```

    [Learn about settings.](./docs/settings.md#portal_plugin_content_netloc)

## Usage

1. In the Django CMS admin interface:
   1. Edit a page.
   2. Add a "Remote Content" plugin to a placeholder.
   3. Enter the path to the remote content (e.g. "/about/about-tacc").

2. The plugin will:
   1. Fetch content from the remote source.
   2. Transform URLs to work in the local context.
   3. Display the content or show "No content found" if unavailable.

> [!WARNING]
> It is client application responsibility to:
> - support [CORS](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/CORS) for assets from other domains 
> - load extra assets specific to client context

> [!TIP]
> [Loading news from TACC websites](./docs/news-from-a-core-cms-website.md) may require client application to add specific extra assets.

## Screenshots

| 1. Plugin chosen | 2. Path set | 3. Arranged in structure | 4. Content rendered |
| - | - | - | - |
| <img width="475" alt="plugin choice" src="https://github.com/user-attachments/assets/2a7ce112-2cda-4bf9-b9f4-a1f86163fa29" /> | <img width="720" alt="plugin form" src="https://github.com/user-attachments/assets/b6d4d85f-a1af-49da-a3bb-e64dd67bf7f6" /> | <img width="375" alt="plugin instance" src="https://github.com/user-attachments/assets/fbd00693-5e83-4d38-88c2-3db6a31454fe" /> | <img width="960" alt="plugin rendered" src="https://github.com/user-attachments/assets/6bf4d2a8-bec2-47a6-b14e-9b5740327407" /> |

> [!NOTE]
> This demo set `PORTAL_PLUGIN_CONTENT_NETLOC` to https://localhost:8000. Default is https://tacc.utexas.edu.

## Features

- Simple interface to input a path to remote content
- Automatic fetching and rendering of remote content
- URL transformation to handle:
  - relative paths
  - resource URLs
  - query parameters
- Error handling for failed requests

## Testing

Follow [TESTING.md](TESTING.md).
