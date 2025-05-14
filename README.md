## Texas Advanced Computing Center
# Django CMS Plugin: Remote Content

This plugin fetches and displays content from remote TACC URLs. It was converted from the Core-CMS remote_content app into a Django CMS plugin.

- __Distribution Name__: `djangocms-tacc-remote-content`
- __Package Name__: `djangocms_tacc_remote_content`
- __Class Name__: `RemoteContent`
- __Plugin Name__: "Remote Content"


> [!IMPORTANT]
> After using this repository template for your app:
>
> 1. Follow [(wiki) Development Quick Start](https://github.com/TACC/Django-App/wiki/Development-Quick-Start).
> 2. Remove this notice.


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
PORTAL_REMOTE_CONTENT_SOURCE_ROOT = 'https://tacc.utexas.edu/'  # default value
```

## Usage

1. In the Django CMS admin interface:
   - Edit a page
   - Add a "Remote Content" plugin to a placeholder
   - Enter the path to the remote content (e.g. "about/staff")

2. The plugin will:
   - Fetch content from the remote source
   - Transform URLs to work in the local context
   - Display the content or show "No content found" if unavailable

3. Advanced features:
   - Resource URLs (images, etc.) are automatically transformed
   - Relative URLs are properly handled
   - Cross-origin resources are marked appropriately

## Features

- Simple interface to input a path to remote content
- Automatic fetching and rendering of remote content
- URL transformation to handle relative paths and resource URLs
- Proper error handling for failed requests
- "No content found" display when content is unavailable

## Development

1. Clone the repository:
```bash
git clone https://github.com/TACC/Core-CMS-Plugin-Remote-Content.git
```

2. Install in development mode:
```bash
pip install -e .
```

## Testing

The plugin includes tests to verify proper:
- Content fetching and rendering
- URL transformation
- Error handling
- Settings integration

Run the tests with:
```bash
python manage.py test djangocms_tacc_remote_content
```

## License

BSD 3-Clause License. See LICENSE file for details.
