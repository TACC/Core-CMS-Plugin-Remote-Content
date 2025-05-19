from django import forms
from django.utils.translation import gettext_lazy as _

class RemoteContentForm(forms.ModelForm):
    remote_path = forms.CharField(
        label=_('Remote Path'),
        help_text=_('The path of the URL to the remote content to be displayed (e.g. "/news/latest-news/tag/lccf/")'),
        required=True
    )

    class Meta:
        help_texts = {
            'full_url': _('The complete URL that will be used to fetch content.')
        }
        labels = {
            'full_url': _('Full URL')
        }

fieldsets = [
    (None, {
        'fields': (
            'remote_path',
            'full_url',
        )
    }),
]
