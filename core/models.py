from datetime import datetime, timezone, date, time, timedelta
from flask_sqlalchemy import SQLAlchemy
import json


# ============================================================
# BANCO DE DADOS
# ============================================================

db = SQLAlchemy()


# ============================================================
# HELPERS
# ============================================================

def _now():
    """
    Retorna datetime atual em UTC.

    Compatível com PostgreSQL:
        timestamp with time zone
    """
    return datetime.now(timezone.utc)


def _ensure_utc(value):
    """
    Garante que um datetime seja timezone-aware em UTC.

    Se o datetime já possuir timezone, converte para UTC.
    Se for naive, assume UTC.
    """
    if value is None:
        return None

    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


def _json_loads(value, default):
    """
    Converte JSON armazenado em TEXT para Python.

    Evita que um JSON inválido existente no banco
    provoque HTTP 500 nas APIs.
    """
    if value is None or value == "":
        return default

    try:
        return json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return default


# ============================================================
# MIXIN — TIMESTAMPS
# ============================================================

class TimestampMixin:
    """
    Campos padrão de auditoria.

    PostgreSQL/Neon:
        timestamp with time zone
    """

    criado_em = db.Column(
        db.DateTime(timezone=True),
        default=_now
    )

    atualizado_em = db.Column(
        db.DateTime(timezone=True),
        default=_now,
        onupdate=_now
    )


# ============================================================
# PACIENTE
# ============================================================

class Paciente(db.Model, TimestampMixin):

    __tablename__ = "paciente"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    nome = db.Column(
        db.String(120),
        nullable=False,
        index=True
    )

    data_nascimento = db.Column(
        db.Date,
        nullable=True
    )

    sexo = db.Column(
        db.String(10)
    )

    telefone = db.Column(
        db.String(20)
    )

    cpf = db.Column(
        db.String(14),
        unique=True,
        nullable=True,
        index=True
    )

    rg = db.Column(
        db.String(20),
        nullable=True
    )

    endereco = db.Column(
        db.Text
    )

    # JSON armazenado como TEXT
    doencas_previas = db.Column(
        db.Text
    )

    # --------------------------------------------------------
    # Relacionamentos
    # --------------------------------------------------------

    atendimentos = db.relationship(
        "Atendimento",
        backref="paciente",
        lazy="select",
        order_by="Atendimento.data.desc()"
    )

    consultas = db.relationship(
        "Consulta",
        backref="paciente_consulta",
        lazy="select",
        order_by="Consulta.data_hora.desc()"
    )

    exames = db.relationship(
        "Exame",
        backref="paciente_exame",
        lazy="select",
        order_by="Exame.data.desc()"
    )

    pagamentos = db.relationship(
        "Pagamento",
        backref="paciente_pagamento",
        lazy="select",
        order_by="Pagamento.data_vencimento.desc()"
    )

    receitas = db.relationship(
        "Receita",
        backref="paciente_receita",
        lazy="select",
        order_by="Receita.data_emissao.desc()"
    )

    # --------------------------------------------------------
    # Propriedades
    # --------------------------------------------------------

    @property
    def idade(self):

        if not self.data_nascimento:
            return None

        hoje = date.today()

        return (
            hoje.year
            - self.data_nascimento.year
            - (
                (hoje.month, hoje.day)
                <
                (
                    self.data_nascimento.month,
                    self.data_nascimento.day
                )
            )
        )

    # --------------------------------------------------------
    # Serialização
    # --------------------------------------------------------

    def to_dict(self):

        return {
            "id": self.id,
            "nome": self.nome,
            "data_nascimento": (
                self.data_nascimento.isoformat()
                if self.data_nascimento
                else None
            ),
            "idade": self.idade,
            "sexo": self.sexo,
            "telefone": self.telefone,
            "cpf": self.cpf,
            "rg": self.rg,
            "endereco": self.endereco,

            "doencas_previas": _json_loads(
                self.doencas_previas,
                []
            ),

            "criado_em": (
                self.criado_em.isoformat()
                if self.criado_em
                else None
            ),

            "atualizado_em": (
                self.atualizado_em.isoformat()
                if self.atualizado_em
                else None
            ),
        }

    def to_dict_completo(self):

        dados = self.to_dict()

        dados["atendimentos"] = [
            a.to_dict()
            for a in self.atendimentos
        ]

        dados["consultas"] = [
            c.to_dict()
            for c in self.consultas
        ]

        dados["exames"] = [
            e.to_dict()
            for e in self.exames
        ]

        dados["pagamentos"] = [
            p.to_dict()
            for p in self.pagamentos
        ]

        dados["receitas"] = [
            r.to_dict()
            for r in self.receitas
        ]

        return dados


# ============================================================
# MÉDICO
# ============================================================

class Medico(db.Model, TimestampMixin):

    __tablename__ = "medico"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    nome = db.Column(
        db.String(120),
        nullable=False,
        index=True
    )

    especialidade = db.Column(
        db.String(100)
    )

    crm = db.Column(
        db.String(50),
        unique=True,
        index=True
    )

    telefone = db.Column(
        db.String(20)
    )

    email = db.Column(
        db.String(120)
    )

    horarios_disponiveis = db.Column(
        db.Text
    )

    # Neon possui NOT NULL
    ativo = db.Column(
        db.Boolean,
        default=True,
        nullable=False,
        index=True
    )

    # --------------------------------------------------------
    # Relacionamentos
    # --------------------------------------------------------

    consultas = db.relationship(
        "Consulta",
        backref="medico_consulta",
        lazy="select",
        order_by="Consulta.data_hora.desc()"
    )

    atendimentos = db.relationship(
        "Atendimento",
        backref="medico_atendimento",
        lazy="select",
        order_by="Atendimento.data.desc()"
    )

    receitas = db.relationship(
        "Receita",
        backref="medico_receita",
        lazy="select",
        order_by="Receita.data_emissao.desc()"
    )

    # --------------------------------------------------------
    # Serialização
    # --------------------------------------------------------

    def to_dict(self):

        return {
            "id": self.id,
            "nome": self.nome,
            "especialidade": self.especialidade,
            "crm": self.crm,
            "telefone": self.telefone,
            "email": self.email,

            "horarios_disponiveis": _json_loads(
                self.horarios_disponiveis,
                {}
            ),

            "ativo": self.ativo,

            "criado_em": (
                self.criado_em.isoformat()
                if self.criado_em
                else None
            ),

            "atualizado_em": (
                self.atualizado_em.isoformat()
                if self.atualizado_em
                else None
            ),
        }

    # --------------------------------------------------------
    # Horários ocupados
    # --------------------------------------------------------

    def horarios_ocupados(self, data):
        """
        Retorna os horários ocupados de um médico em uma data.

        PostgreSQL/Neon utiliza:
            timestamp with time zone

        Portanto os limites são explicitamente UTC-aware.
        """

        inicio = datetime.combine(
            data,
            time.min,
            tzinfo=timezone.utc
        )

        fim = datetime.combine(
            data,
            time.max,
            tzinfo=timezone.utc
        )

        consultas = Consulta.query.filter(
            Consulta.medico_id == self.id,
            Consulta.data_hora >= inicio,
            Consulta.data_hora <= fim,
            Consulta.status != "cancelada"
        ).all()

        ocupados = []

        for consulta in consultas:

            inicio_consulta = _ensure_utc(
                consulta.data_hora
            )

            fim_consulta = (
                inicio_consulta
                + timedelta(hours=1)
            )

            ocupados.append(
                (
                    inicio_consulta.strftime("%H:%M"),
                    fim_consulta.strftime("%H:%M")
                )
            )

        return ocupados


# ============================================================
# SERVIÇO
# ============================================================

class Servico(db.Model, TimestampMixin):

    __tablename__ = "servico"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    nome = db.Column(
        db.String(150),
        nullable=False,
        index=True
    )

    categoria = db.Column(
        db.String(50),
        nullable=False,
        index=True
    )

    descricao = db.Column(
        db.Text
    )

    valor = db.Column(
        db.Numeric(10, 2),
        nullable=False,
        default=0
    )

    ativo = db.Column(
        db.Boolean,
        default=True,
        nullable=False,
        index=True
    )

    def to_dict(self):

        return {
            "id": self.id,
            "nome": self.nome,
            "categoria": self.categoria,
            "descricao": self.descricao,

            "valor": (
                float(self.valor)
                if self.valor is not None
                else 0.0
            ),

            "ativo": self.ativo,

            "criado_em": (
                self.criado_em.isoformat()
                if self.criado_em
                else None
            ),

            "atualizado_em": (
                self.atualizado_em.isoformat()
                if self.atualizado_em
                else None
            ),
        }


# ============================================================
# CONSULTA
# ============================================================

class Consulta(db.Model, TimestampMixin):

    __tablename__ = "consulta"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    tipo = db.Column(
        db.String(50),
        default="normal"
    )

    data_hora = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        index=True
    )

    status = db.Column(
        db.String(20),
        default="agendada",
        index=True
    )

    observacoes = db.Column(
        db.Text
    )

    motivo = db.Column(
        db.Text
    )

    valor = db.Column(
        db.Numeric(10, 2),
        nullable=True
    )

    paciente_id = db.Column(
        db.Integer,
        db.ForeignKey("paciente.id"),
        index=True
    )

    medico_id = db.Column(
        db.Integer,
        db.ForeignKey("medico.id"),
        index=True
    )

    servico_id = db.Column(
        db.Integer,
        db.ForeignKey("servico.id"),
        nullable=True,
        index=True
    )

    servico = db.relationship(
        "Servico",
        backref="consultas"
    )

    def to_dict(self):

        return {
            "id": self.id,
            "tipo": self.tipo,

            "data_hora": (
                self.data_hora.isoformat()
                if self.data_hora
                else None
            ),

            "status": self.status,
            "observacoes": self.observacoes,
            "motivo": self.motivo,

            "valor": (
                float(self.valor)
                if self.valor is not None
                else 0.0
            ),

            "servico": (
                self.servico.to_dict()
                if self.servico
                else None
            ),

            "paciente": (
                self.paciente_consulta.to_dict()
                if self.paciente_consulta
                else None
            ),

            "medico": (
                self.medico_consulta.to_dict()
                if self.medico_consulta
                else None
            ),

            "criado_em": (
                self.criado_em.isoformat()
                if self.criado_em
                else None
            ),

            "atualizado_em": (
                self.atualizado_em.isoformat()
                if self.atualizado_em
                else None
            ),
        }


# ============================================================
# EXAME
# ============================================================

class Exame(db.Model, TimestampMixin):

    __tablename__ = "exame"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    tipo = db.Column(
        db.String(100),
        nullable=False,
        index=True
    )

    descricao = db.Column(
        db.Text
    )

    data = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        index=True
    )

    resultado = db.Column(
        db.Text
    )

    status = db.Column(
        db.String(20),
        default="agendado",
        index=True
    )

    valor = db.Column(
        db.Numeric(10, 2),
        nullable=True
    )

    paciente_id = db.Column(
        db.Integer,
        db.ForeignKey("paciente.id"),
        index=True
    )

    medico_solicitante_id = db.Column(
        db.Integer,
        db.ForeignKey("medico.id"),
        index=True
    )

    servico_id = db.Column(
        db.Integer,
        db.ForeignKey("servico.id"),
        nullable=True,
        index=True
    )

    medico_solicitante = db.relationship(
        "Medico",
        foreign_keys=[medico_solicitante_id]
    )

    servico = db.relationship(
        "Servico",
        backref="exames"
    )

    def to_dict(self):

        return {
            "id": self.id,
            "tipo": self.tipo,
            "descricao": self.descricao,

            "data": (
                self.data.isoformat()
                if self.data
                else None
            ),

            "resultado": self.resultado,
            "status": self.status,

            "valor": (
                float(self.valor)
                if self.valor is not None
                else 0.0
            ),

            "servico": (
                self.servico.to_dict()
                if self.servico
                else None
            ),

            "paciente": (
                self.paciente_exame.to_dict()
                if self.paciente_exame
                else None
            ),

            "medico_solicitante": (
                self.medico_solicitante.to_dict()
                if self.medico_solicitante
                else None
            ),

            "criado_em": (
                self.criado_em.isoformat()
                if self.criado_em
                else None
            ),

            "atualizado_em": (
                self.atualizado_em.isoformat()
                if self.atualizado_em
                else None
            ),
        }


# ============================================================
# ATENDIMENTO
# ============================================================

class Atendimento(db.Model, TimestampMixin):

    __tablename__ = "atendimento"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    tipo = db.Column(
        db.String(50),
        index=True
    )

    sintomas = db.Column(
        db.Text
    )

    diagnostico = db.Column(
        db.Text
    )

    evolucao = db.Column(
        db.Text
    )

    prescricao = db.Column(
        db.Text
    )

    data = db.Column(
        db.DateTime(timezone=True),
        default=_now,
        index=True
    )

    paciente_id = db.Column(
        db.Integer,
        db.ForeignKey("paciente.id"),
        index=True
    )

    medico_id = db.Column(
        db.Integer,
        db.ForeignKey("medico.id"),
        index=True
    )

    consulta_id = db.Column(
        db.Integer,
        db.ForeignKey("consulta.id"),
        nullable=True,
        index=True
    )

    consulta = db.relationship(
        "Consulta",
        backref="atendimento_consulta"
    )

    def to_dict(self):

        return {
            "id": self.id,
            "tipo": self.tipo,

            "sintomas": _json_loads(
                self.sintomas,
                []
            ),

            "diagnostico": self.diagnostico,
            "evolucao": self.evolucao,
            "prescricao": self.prescricao,

            "data": (
                self.data.isoformat()
                if self.data
                else None
            ),

            "paciente": (
                self.paciente.to_dict()
                if self.paciente
                else None
            ),

            "medico": (
                self.medico_atendimento.to_dict()
                if self.medico_atendimento
                else None
            ),

            "consulta_id": self.consulta_id,

            "criado_em": (
                self.criado_em.isoformat()
                if self.criado_em
                else None
            ),

            "atualizado_em": (
                self.atualizado_em.isoformat()
                if self.atualizado_em
                else None
            ),
        }


# ============================================================
# PAGAMENTO
# ============================================================

class Pagamento(db.Model, TimestampMixin):

    __tablename__ = "pagamento"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    descricao = db.Column(
        db.String(200)
    )

    valor = db.Column(
        db.Numeric(10, 2),
        nullable=False,
        default=0
    )

    data_vencimento = db.Column(
        db.Date,
        index=True
    )

    data_pagamento = db.Column(
        db.Date,
        nullable=True
    )

    status = db.Column(
        db.String(20),
        default="pendente",
        index=True
    )

    metodo = db.Column(
        db.String(50)
    )

    paciente_id = db.Column(
        db.Integer,
        db.ForeignKey("paciente.id"),
        index=True
    )

    servico_id = db.Column(
        db.Integer,
        db.ForeignKey("servico.id"),
        nullable=True,
        index=True
    )

    servico = db.relationship(
        "Servico",
        backref="pagamentos"
    )

    def to_dict(self):

        return {
            "id": self.id,
            "descricao": self.descricao,

            "valor": (
                float(self.valor)
                if self.valor is not None
                else 0.0
            ),

            "data_vencimento": (
                self.data_vencimento.isoformat()
                if self.data_vencimento
                else None
            ),

            "data_pagamento": (
                self.data_pagamento.isoformat()
                if self.data_pagamento
                else None
            ),

            "status": self.status,
            "metodo": self.metodo,

            "servico": (
                self.servico.to_dict()
                if self.servico
                else None
            ),

            "paciente": (
                self.paciente_pagamento.to_dict()
                if self.paciente_pagamento
                else None
            ),

            "criado_em": (
                self.criado_em.isoformat()
                if self.criado_em
                else None
            ),

            "atualizado_em": (
                self.atualizado_em.isoformat()
                if self.atualizado_em
                else None
            ),
        }


# ============================================================
# RECEITA
# ============================================================

class Receita(db.Model, TimestampMixin):

    __tablename__ = "receita"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    medicamentos = db.Column(
        db.Text
    )

    observacoes = db.Column(
        db.Text
    )

    data_emissao = db.Column(
        db.DateTime(timezone=True),
        default=_now,
        index=True
    )

    paciente_id = db.Column(
        db.Integer,
        db.ForeignKey("paciente.id"),
        index=True
    )

    medico_id = db.Column(
        db.Integer,
        db.ForeignKey("medico.id"),
        index=True
    )

    atendimento_id = db.Column(
        db.Integer,
        db.ForeignKey("atendimento.id"),
        nullable=True,
        index=True
    )

    atendimento = db.relationship(
        "Atendimento",
        backref="receita_atendimento"
    )

    def to_dict(self):

        return {
            "id": self.id,

            "medicamentos": _json_loads(
                self.medicamentos,
                []
            ),

            "observacoes": self.observacoes,

            "data_emissao": (
                self.data_emissao.isoformat()
                if self.data_emissao
                else None
            ),

            "paciente": (
                self.paciente_receita.to_dict()
                if self.paciente_receita
                else None
            ),

            "medico": (
                self.medico_receita.to_dict()
                if self.medico_receita
                else None
            ),

            "atendimento_id": self.atendimento_id,

            "criado_em": (
                self.criado_em.isoformat()
                if self.criado_em
                else None
            ),

            "atualizado_em": (
                self.atualizado_em.isoformat()
                if self.atualizado_em
                else None
            ),
        }


# ============================================================
# MEDICAMENTO
# ============================================================

class Medicamento(db.Model, TimestampMixin):

    __tablename__ = "medicamento"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    nome = db.Column(
        db.String(200),
        nullable=False,
        index=True
    )

    principio_ativo = db.Column(
        db.String(500)
    )

    dosagem = db.Column(
        db.String(100)
    )

    forma_farmaceutica = db.Column(
        db.String(100)
    )

    tipo_produto = db.Column(
        db.String(50)
    )

    categoria_regulatoria = db.Column(
        db.String(100)
    )

    numero_registro_produto = db.Column(
        db.String(50),
        unique=True,
        index=True
    )

    data_finalizacao_processo = db.Column(
        db.String(20)
    )

    data_vencimento_registro = db.Column(
        db.String(20)
    )

    numero_processo = db.Column(
        db.String(50)
    )

    classe_terapeutica = db.Column(
        db.String(200)
    )

    fabricante = db.Column(
        db.String(200)
    )

    situacao_registro = db.Column(
        db.String(50)
    )

    descricao = db.Column(
        db.Text
    )

    def to_dict(self):

        return {
            "id": self.id,
            "nome": self.nome,
            "principio_ativo": self.principio_ativo,
            "dosagem": self.dosagem,
            "forma_farmaceutica": self.forma_farmaceutica,
            "tipo_produto": self.tipo_produto,
            "categoria_regulatoria": self.categoria_regulatoria,
            "numero_registro_produto": self.numero_registro_produto,
            "data_finalizacao_processo": self.data_finalizacao_processo,
            "data_vencimento_registro": self.data_vencimento_registro,
            "numero_processo": self.numero_processo,
            "classe_terapeutica": self.classe_terapeutica,
            "fabricante": self.fabricante,
            "situacao_registro": self.situacao_registro,
            "descricao": self.descricao,

            "criado_em": (
                self.criado_em.isoformat()
                if self.criado_em
                else None
            ),

            "atualizado_em": (
                self.atualizado_em.isoformat()
                if self.atualizado_em
                else None
            ),
        }