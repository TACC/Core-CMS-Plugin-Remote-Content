from django import forms
from django.utils.translation import gettext_lazy as _

class RemoteContentForm(forms.ModelForm):
    remote_path = forms.CharField(
        label=_('Remote Path'),
        help_text=_('Path to remote content (e.g. "news/latest-news/tag/lccf/")'),
        required=True
    )

fieldsets = [
    (_('Content Source'), {
        'description': _('Specify the path to the remote content you want to display.'),
        'fields': (
            'remote_path',
        )
    }),
]
