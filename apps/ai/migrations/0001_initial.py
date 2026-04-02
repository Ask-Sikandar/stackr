import uuid
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("leads", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Conversation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("lead", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="conversations",
                    to="leads.lead",
                )),
                ("started_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["-started_at"]},
        ),
        migrations.CreateModel(
            name="Message",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("conversation", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="messages",
                    to="ai.conversation",
                )),
                ("role", models.CharField(
                    choices=[("user", "User"), ("assistant", "Assistant")],
                    max_length=10,
                )),
                ("content", models.TextField()),
                ("intent", models.CharField(blank=True, default="", max_length=20)),
                ("sources", models.JSONField(default=list)),
                ("components", models.JSONField(default=list)),
                ("handoff_triggered", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["created_at"]},
        ),
    ]
