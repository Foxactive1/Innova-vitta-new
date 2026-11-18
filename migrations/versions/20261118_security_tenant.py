"""Add clinic identity, memberships, audit and tenant ownership columns."""
from alembic import op
import sqlalchemy as sa

revision = "20261118_security_tenant"
down_revision = None
branch_labels = None
depends_on = None

CLINICAL_TABLES = (
    "paciente", "medico", "servico", "consulta", "exame",
    "atendimento", "pagamento", "receita", "medicamento",
)


def upgrade():
    op.create_table(
        "tenant",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nome", sa.String(160), nullable=False),
        sa.Column("slug", sa.String(80), nullable=False, unique=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("criado_em", sa.DateTime(timezone=True)),
        sa.Column("atualizado_em", sa.DateTime(timezone=True)),
    )
    op.bulk_insert(
        sa.table("tenant", sa.column("id", sa.Integer()), sa.column("nome", sa.String()),
                 sa.column("slug", sa.String()), sa.column("ativo", sa.Boolean())),
        [{"id": 1, "nome": "Clínica Vida+", "slug": "clinica-vida-plus", "ativo": True}],
    )

    op.create_table(
        "app_user",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(80), nullable=False, unique=True),
        sa.Column("email", sa.String(254), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(512), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("criado_em", sa.DateTime(timezone=True)),
        sa.Column("atualizado_em", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_app_user_username", "app_user", ["username"])
    op.create_index("ix_app_user_email", "app_user", ["email"])

    op.create_table(
        "clinic_membership",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("app_user.id"), nullable=False),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("role", sa.String(32), nullable=False, server_default="recepcao"),
        sa.Column("padrao", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("criado_em", sa.DateTime(timezone=True)),
        sa.Column("atualizado_em", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("user_id", "tenant_id", name="uq_membership_user_tenant"),
    )
    op.create_index("ix_clinic_membership_user_id", "clinic_membership", ["user_id"])
    op.create_index("ix_clinic_membership_tenant_id", "clinic_membership", ["tenant_id"])

    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("app_user.id")),
        sa.Column("action", sa.String(24), nullable=False),
        sa.Column("resource_type", sa.String(80), nullable=False),
        sa.Column("resource_id", sa.String(80)),
        sa.Column("endpoint", sa.String(160)),
        sa.Column("http_method", sa.String(10)),
        sa.Column("status_code", sa.Integer()),
        sa.Column("ip_address", sa.String(45)),
        sa.Column("user_agent", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_log_tenant_id", "audit_log", ["tenant_id"])
    op.create_index("ix_audit_log_user_id", "audit_log", ["user_id"])

    for table in CLINICAL_TABLES:
        with op.batch_alter_table(table) as batch_op:
            batch_op.add_column(sa.Column("tenant_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key(f"fk_{table}_tenant_id_tenant", "tenant", ["tenant_id"], ["id"])
        op.execute(sa.text(f"UPDATE {table} SET tenant_id = 1 WHERE tenant_id IS NULL"))
        op.create_index(f"ix_{table}_tenant_id", table, ["tenant_id"])


def downgrade():
    for table in reversed(CLINICAL_TABLES):
        op.drop_index(f"ix_{table}_tenant_id", table_name=table)
        with op.batch_alter_table(table) as batch_op:
            batch_op.drop_constraint(f"fk_{table}_tenant_id_tenant", type_="foreignkey")
            batch_op.drop_column("tenant_id")
    op.drop_index("ix_audit_log_user_id", table_name="audit_log")
    op.drop_index("ix_audit_log_tenant_id", table_name="audit_log")
    op.drop_table("audit_log")
    op.drop_index("ix_clinic_membership_tenant_id", table_name="clinic_membership")
    op.drop_index("ix_clinic_membership_user_id", table_name="clinic_membership")
    op.drop_table("clinic_membership")
    op.drop_index("ix_app_user_email", table_name="app_user")
    op.drop_index("ix_app_user_username", table_name="app_user")
    op.drop_table("app_user")
    op.drop_table("tenant")
