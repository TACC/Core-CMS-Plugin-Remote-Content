# Generated manually

from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('djangocms_tacc_remote_content', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='remotecontent',
            old_name='path',
            new_name='remote_path',
        ),
    ]
