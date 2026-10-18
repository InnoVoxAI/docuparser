import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ImportBatch",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("source", models.CharField(max_length=32)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("running", "Em andamento"),
                            ("ready", "Aguardando decisão"),
                            ("error", "Erro"),
                        ],
                        default="running",
                        max_length=16,
                    ),
                ),
                (
                    "error_message",
                    models.CharField(blank=True, default="", max_length=500),
                ),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                (
                    "started_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="import_batches",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ImportProposal",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "entity_type",
                    models.CharField(
                        choices=[
                            ("condominium", "Condomínio"),
                            ("chart", "Plano de contas"),
                            ("account", "Conta"),
                        ],
                        max_length=16,
                    ),
                ),
                ("external_id", models.CharField(max_length=128)),
                (
                    "action",
                    models.CharField(
                        choices=[
                            ("new", "Novo"),
                            ("update", "Atualizar"),
                            ("deactivate", "Desativar"),
                            ("conflict", "Conflito"),
                        ],
                        max_length=16,
                    ),
                ),
                ("data", models.JSONField(default=dict)),
                ("diff", models.JSONField(blank=True, default=dict)),
                ("warnings", models.JSONField(blank=True, default=list)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pendente"),
                            ("approved", "Aprovada"),
                            ("resolved", "Conflito resolvido"),
                            ("rejected", "Rejeitada"),
                            ("applied", "Aplicada"),
                            ("superseded", "Substituída"),
                        ],
                        default="pending",
                        max_length=16,
                    ),
                ),
                ("resolution", models.JSONField(blank=True, default=dict)),
                ("decided_at", models.DateTimeField(blank=True, null=True)),
                (
                    "batch",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="proposals",
                        to="erp_import.importbatch",
                    ),
                ),
                (
                    "decided_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="import_decisions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(
                        fields=["entity_type", "external_id", "status"],
                        name="erp_import_proposal_entity_idx",
                    )
                ],
            },
        ),
    ]
