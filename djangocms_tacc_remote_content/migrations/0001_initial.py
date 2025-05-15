# Generated manually

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('cms', '0022_auto_20180620_1551'),
    ]

    operations = [
        migrations.CreateModel(
            name='RemoteContent',
            fields=[
                ('cmsplugin_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, related_name='djangocms_tacc_remote_content_remotecontent', serialize=False, to='cms.CMSPlugin')),
                ('remote_path', models.CharField(help_text='Path to remote content (e.g. "news/latest-news/tag/lccf/")', max_length=255, verbose_name='Remote Path')),
            ],
            options={
                'abstract': False,
            },
            bases=('cms.cmsplugin',),
        ),
    ]
