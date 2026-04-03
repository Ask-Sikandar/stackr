from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_provider_settings"),
    ]

    operations = [
        migrations.AlterField(
            model_name="organizationllmkey",
            name="api_key",
            field=models.CharField(max_length=1024),
        ),
    ]
