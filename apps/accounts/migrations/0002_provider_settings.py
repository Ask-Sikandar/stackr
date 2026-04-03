import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="organization",
            name="allow_platform_fallback",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="organization",
            name="use_private_llm_credentials",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="project",
            name="custom_instructions",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="project",
            name="llm_backup_provider",
            field=models.CharField(
                blank=True,
                choices=[("ollama", "Ollama"), ("openai", "OpenAI"), ("gemini", "Gemini")],
                default="",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="project",
            name="llm_primary_provider",
            field=models.CharField(
                choices=[("ollama", "Ollama"), ("openai", "OpenAI"), ("gemini", "Gemini")],
                default="ollama",
                max_length=20,
            ),
        ),
        migrations.CreateModel(
            name="OrganizationLLMKey",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "provider",
                    models.CharField(
                        choices=[("ollama", "Ollama"), ("openai", "OpenAI"), ("gemini", "Gemini")],
                        max_length=20,
                    ),
                ),
                ("api_key", models.CharField(max_length=255)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="llm_keys",
                        to="accounts.organization",
                    ),
                ),
            ],
            options={"ordering": ["organization", "provider"]},
        ),
        migrations.AlterUniqueTogether(
            name="organizationllmkey",
            unique_together={("organization", "provider")},
        ),
    ]
