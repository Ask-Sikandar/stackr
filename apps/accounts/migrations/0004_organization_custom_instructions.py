from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_alter_organizationllmkey_api_key"),
    ]

    operations = [
        migrations.AddField(
            model_name="organization",
            name="custom_instructions",
            field=models.TextField(blank=True, default=""),
        ),
    ]
