"""Tenant isolation hooks for SQLAlchemy ORM sessions."""
from flask import g, has_request_context
from sqlalchemy import event
from sqlalchemy.orm import Session, with_loader_criteria

from core.models import AuditLog, TenantMixin


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
    for obj in session.deleted:
        if isinstance(obj, AuditLog):
            raise PermissionError("A trilha de auditoria é somente de acréscimo.")
    for obj in session.dirty:
        if isinstance(obj, AuditLog):
            raise PermissionError("A trilha de auditoria é somente de acréscimo.")
