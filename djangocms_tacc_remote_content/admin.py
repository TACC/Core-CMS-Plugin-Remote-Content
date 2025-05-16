from cms.admin.placeholderadmin import FrontendEditableAdminMixin
from django.contrib import admin

from .models import RemoteContent
from .forms import RemoteContentForm, fieldsets

class RemoteContentAdmin(FrontendEditableAdminMixin, admin.ModelAdmin):
    form = RemoteContentForm
    fieldsets = fieldsets
    list_display = ('id', 'remote_path')
    search_fields = ('remote_path',)

admin.site.register(RemoteContent, RemoteContentAdmin)
