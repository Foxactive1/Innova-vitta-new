"""Tenant isolation hooks for SQLAlchemy ORM sessions."""
from flask import g, has_request_context
from sqlalchemy import event, select
from sqlalchemy.orm import Session, with_loader_criteria

from core.models import (
    Atendimento, AuditLog, Consulta, Exame, Medico, Pagamento,
    Paciente, Receita, Servico, TenantMixin,
)

FOREIGN_TENANT_REFERENCES = {
    Consulta: {"paciente_id": Paciente, "medico_id": Medico, "servico_id": Servico},
    Exame: {"paciente_id": Paciente, "medico_solicitante_id": Medico, "servico_id": Servico},
    Atendimento: {"paciente_id": Paciente, "medico_id": Medico, "consulta_id": Consulta},
    Pagamento: {"paciente_id": Paciente, "servico_id": Servico},
    Receita: {"paciente_id": Paciente, "medico_id": Medico, "atendimento_id": Atendimento},
}


@event.listens_for(Session, "do_orm_execute")
def _scope_queries_to_active_tenant(execute_state):
    if not execute_state.is_select or execute_state.execution_options.get("skip_tenant_scope"):
        return
    if not has_request_context():
        return
    tenant_id = getattr(g, "active_tenant_id", None)
    if tenant_id is None:
        return
    execute_state.statement = execute_state.statement.options(
        with_loader_criteria(
            TenantMixin,
            lambda model: model.tenant_id == tenant_id,
            include_aliases=True,
        )
    )


@event.listens_for(Session, "before_flush")
def _assign_and_validate_tenant(session, flush_context, instances):
    if not has_request_context():
        return
    tenant_id = getattr(g, "active_tenant_id", None)
    if tenant_id is None:
        return
    for obj in session.new:
        if isinstance(obj, TenantMixin):
            if obj.tenant_id is None:
                obj.tenant_id = tenant_id
            elif obj.tenant_id != tenant_id:
                raise PermissionError("Não é permitido gravar dados em outra clínica.")
    for obj in session.dirty:
        if isinstance(obj, TenantMixin) and obj.tenant_id != tenant_id:
            raise PermissionError("Não é permitido alterar dados de outra clínica.")
    # ORM scoping alone is insufficient when a form submits a raw foreign-key ID.
    # Validate every clinical relation against the same tenant using Core SQL.
    for obj in session.new.union(session.dirty):
        if not isinstance(obj, TenantMixin):
            continue
        for field, target_model in FOREIGN_TENANT_REFERENCES.get(type(obj), {}).items():
            target_id = getattr(obj, field, None)
            if target_id is None:
                continue
            stmt = select(target_model.id).where(
                target_model.id == target_id,
                target_model.tenant_id == tenant_id,
            )
            if session.connection().execute(stmt).first() is None:
                raise PermissionError("Referência clínica inválida ou pertencente a outra clínica.")
    for obj in session.deleted:
        if isinstance(obj, AuditLog):
            raise PermissionError("A trilha de auditoria é somente de acréscimo.")
        if isinstance(obj, TenantMixin) and obj.tenant_id != tenant_id:
            raise PermissionError("Não é permitido excluir dados de outra clínica.")
    for obj in session.dirty:
        if isinstance(obj, AuditLog):
            raise PermissionError("A trilha de auditoria é somente de acréscimo.")
