import django.db.models.deletion
import pgvector.django
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.RunSQL(
            sql="CREATE EXTENSION IF NOT EXISTS vector;",
            reverse_sql="DROP EXTENSION IF EXISTS vector;",
        ),
        migrations.CreateModel(
            name="Document",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("content", models.TextField()),
                ("source_type", models.CharField(
                    choices=[("markdown", "Markdown"), ("pdf", "PDF"), ("text", "Text")],
                    default="markdown",
                    max_length=20,
                )),
                ("file_url", models.URLField(blank=True, default="")),
                ("uploaded_at", models.DateTimeField(auto_now_add=True)),
                ("processed", models.BooleanField(default=False)),
            ],
            options={"ordering": ["-uploaded_at"]},
        ),
        migrations.CreateModel(
            name="Chunk",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("document", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="chunks",
                    to="documents.document",
                )),
                ("content", models.TextField()),
                ("embedding", pgvector.django.VectorField(dimensions=384, null=True)),
                ("chunk_index", models.IntegerField()),
                ("metadata", models.JSONField(default=dict)),
            ],
            options={
                "ordering": ["document", "chunk_index"],
                "unique_together": {("document", "chunk_index")},
            },
        ),
    ]
