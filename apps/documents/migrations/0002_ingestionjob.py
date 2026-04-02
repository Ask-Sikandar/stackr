import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="IngestionJob",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("job_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("queued", "Queued"),
                            ("running", "Running"),
                            ("succeeded", "Succeeded"),
                            ("failed", "Failed"),
                        ],
                        default="queued",
                        max_length=20,
                    ),
                ),
                ("task_id", models.CharField(blank=True, default="", max_length=255)),
                ("retries", models.PositiveSmallIntegerField(default=0)),
                ("error_message", models.TextField(blank=True, default="")),
                ("queued_at", models.DateTimeField(auto_now_add=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                (
                    "document",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ingestion_jobs",
                        to="documents.document",
                    ),
                ),
            ],
            options={"ordering": ["-queued_at"]},
        ),
        migrations.AddIndex(
            model_name="ingestionjob",
            index=models.Index(fields=["status"], name="documents_i_status_4650eb_idx"),
        ),
        migrations.AddIndex(
            model_name="ingestionjob",
            index=models.Index(fields=["document", "status"], name="documents_i_documen_85f5f7_idx"),
        ),
    ]
