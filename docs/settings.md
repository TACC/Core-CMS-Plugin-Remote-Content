# Remote Content: Settings

- [PORTAL_PLUGIN_CONTENT_NETLOC](#portal_plugin_content_netloc)
- [PORTAL_PLUGIN_CONTENT_USE_RELATIVE_PATHS](#portal_plugin_content_use_relative_paths)

## `PORTAL_PLUGIN_CONTENT_NETLOC`

The base URL form whence to fetch remote content.

## `PORTAL_PLUGIN_CONTENT_USE_RELATIVE_PATHS`

Whether and when to use relative paths instead of absolute URLs.

| Value | Behavior |
| - | - |
| `False` | Converts all relative URLs to absolute URLs |
| `True` | Preserves all relative URLs in their original form |
| `[…]` | Preserves relative URLs of specific elements |

### Specify Elements

To keep relative paths for pagination links on a news list from [TACC]:

[TACC]: https://tacc.utexas.edu/

```python
PORTAL_PLUGIN_CONTENT_USE_RELATIVE_PATHS = [
    '.pagination a' # for "?page=2" links in news lists
]
```

To keep relative paths for elements the source content might specify:

```python
PORTAL_PLUGIN_CONTENT_USE_RELATIVE_PATHS = [
    '[data-use-relative-url]', # source website adds this attr for this plugin
]
```
