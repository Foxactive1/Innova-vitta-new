"""Central endpoint RBAC policy. Unknown endpoints are denied by default."""
READ_METHODS = {"GET", "HEAD", "OPTIONS"}

READ_ROLES = {
    "index": {"admin", "medico", "recepcao", "financeiro", "auditor"},
    "pacientes": {"admin", "medico", "recepcao", "auditor"},
    "consultas": {"admin", "medico", "recepcao", "auditor"},
    "medicos": {"admin", "medico", "recepcao", "auditor"},
    "servicos": {"admin", "medico", "recepcao", "financeiro", "auditor"},
    "atendimentos": {"admin", "medico", "auditor"},
    "exames": {"admin", "medico", "recepcao", "auditor"},
    "receitas": {"admin", "medico", "auditor"},
    "relatorios": {"admin", "financeiro", "auditor"},
    "api_estatisticas": {"admin", "medico", "recepcao", "financeiro", "auditor"},
    "api_busca_paciente": {"admin", "medico", "recepcao"},
    "api_horarios_disponiveis": {"admin", "medico", "recepcao"},
}

WRITE_ROLES = {
    "pacientes": {"admin", "recepcao", "medico"},
    "consultas": {"admin", "medico", "recepcao"},
    "medicos": {"admin"},
    "servicos": {"admin"},
    "atendimentos": {"admin", "medico"},
    "exames": {"admin", "medico"},
    "receitas": {"admin", "medico"},
    "relatorios": {"admin"},
}


def role_allowed(endpoint, method, role):
    if role == "admin":
        return True
    if not endpoint:
        return False
    prefix = endpoint.split(".", 1)[0]
    if method in READ_METHODS:
        allowed = READ_ROLES.get(endpoint, READ_ROLES.get(prefix, set()))
    else:
        allowed = WRITE_ROLES.get(prefix, set())
    return role in allowed
