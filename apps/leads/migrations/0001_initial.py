import uuid
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Lead",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("lead_id", models.UUIDField(db_index=True, default=uuid.uuid4, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("last_seen_at", models.DateTimeField(auto_now=True)),
                ("score", models.IntegerField(default=0)),
                ("last_intent", models.CharField(blank=True, default="", max_length=20)),
            ],
            options={"ordering": ["-score", "-last_seen_at"]},
        ),
        migrations.CreateModel(
            name="IntentEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("lead", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="intent_events",
                    to="leads.lead",
                )),
                ("intent", models.CharField(max_length=20)),
                ("message_preview", models.CharField(max_length=120)),
                ("score_delta", models.IntegerField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["created_at"]},
        ),
    ]
