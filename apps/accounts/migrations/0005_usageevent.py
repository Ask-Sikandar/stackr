from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0004_organization_custom_instructions"),
    ]

    operations = [
        migrations.CreateModel(
            name="UsageEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_type", models.CharField(db_index=True, max_length=64)),
                ("quantity", models.IntegerField(default=1)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "organization",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="usage_events", to="accounts.organization"),
                ),
                (
                    "project",
                    models.ForeignKey(blank=True, null=True, on_delete=models.deletion.SET_NULL, related_name="usage_events", to="accounts.project"),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="usageevent",
            index=models.Index(fields=["organization", "event_type"], name="accounts_usa_organiz_d1e8d0_idx"),
        ),
        migrations.AddIndex(
            model_name="usageevent",
            index=models.Index(fields=["project", "event_type"], name="accounts_usa_project_f0132b_idx"),
        ),
        migrations.AddIndex(
            model_name="usageevent",
            index=models.Index(fields=["created_at"], name="accounts_usa_created_6d04d6_idx"),
        ),
    ]
