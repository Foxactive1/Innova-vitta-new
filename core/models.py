from datetime import datetime, timezone, date
from flask_sqlalchemy import SQLAlchemy
import json

# Helper para timestamps UTC
def _now():
    return datetime.now(timezone.utc)

db = SQLAlchemy()

# Mixin para timestamps
class TimestampMixin:
    criado_em = db.Column(db.DateTime(timezone=True), default=_now)
    atualizado_em = db.Column(db.DateTime(timezone=True), default=_now, onupdate=_now)

class Paciente(db.Model, TimestampMixin):
    __tablename__ = 'paciente'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False, index=True)
    data_nascimento = db.Column(db.Date, nullable=True)  # Novo campo
    sexo = db.Column(db.String(10))
    telefone = db.Column(db.String(20))
    cpf = db.Column(db.String(14), unique=True, nullable=True, index=True)
    rg = db.Column(db.String(20), nullable=True)
    endereco = db.Column(db.Text)
    doencas_previas = db.Column(db.Text)  # JSON array

    # Relacionamentos (já existentes)
    atendimentos = db.relationship('Atendimento', backref='paciente', lazy='select', order_by='Atendimento.data.desc()')
    consultas = db.relationship('Consulta', backref='paciente_consulta', lazy='select', order_by='Consulta.data_hora.desc()')
    exames = db.relationship('Exame', backref='paciente_exame', lazy='select', order_by='Exame.data.desc()')
    pagamentos = db.relationship('Pagamento', backref='paciente_pagamento', lazy='select', order_by='Pagamento.data_vencimento.desc()')
    receitas = db.relationship('Receita', backref='paciente_receita', lazy='select', order_by='Receita.data_emissao.desc()')

    @property
    def idade(self):
        if self.data_nascimento:
            today = date.today()
            return today.year - self.data_nascimento.year - ((today.month, today.day) < (self.data_nascimento.month, self.data_nascimento.day))
        return None

    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'data_nascimento': self.data_nascimento.isoformat() if self.data_nascimento else None,
            'idade': self.idade,
            'sexo': self.sexo,
            'telefone': self.telefone,
            'cpf': self.cpf,
            'rg': self.rg,
            'endereco': self.endereco,
            'doencas_previas': json.loads(self.doencas_previas) if self.doencas_previas else [],
            'criado_em': self.criado_em.isoformat() if self.criado_em else None,
            'atualizado_em': self.atualizado_em.isoformat() if self.atualizado_em else None,
        }

    def to_dict_completo(self):
        d = self.to_dict()
        d['atendimentos'] = [a.to_dict() for a in self.atendimentos]
        d['consultas'] = [c.to_dict() for c in self.consultas]
        d['exames'] = [e.to_dict() for e in self.exames]
        d['pagamentos'] = [p.to_dict() for p in self.pagamentos]
        d['receitas'] = [r.to_dict() for r in self.receitas]
        return d

class Medico(db.Model, TimestampMixin):
    __tablename__ = 'medico'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False, index=True)
    especialidade = db.Column(db.String(100))
    crm = db.Column(db.String(50), unique=True, index=True)
    telefone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    horarios_disponiveis = db.Column(db.Text)  # JSON
    ativo = db.Column(db.Boolean, default=True, index=True)

    consultas = db.relationship('Consulta', backref='medico_consulta', lazy='select', order_by='Consulta.data_hora.desc()')
    atendimentos = db.relationship('Atendimento', backref='medico_atendimento', lazy='select', order_by='Atendimento.data.desc()')
    receitas = db.relationship('Receita', backref='medico_receita', lazy='select', order_by='Receita.data_emissao.desc()')

    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'especialidade': self.especialidade,
            'crm': self.crm,
            'telefone': self.telefone,
            'email': self.email,
            'horarios_disponiveis': json.loads(self.horarios_disponiveis) if self.horarios_disponiveis else {},
            'ativo': self.ativo,
            'criado_em': self.criado_em.isoformat() if self.criado_em else None,
            'atualizado_em': self.atualizado_em.isoformat() if self.atualizado_em else None,
        }

    def horarios_ocupados(self, data):
        """Retorna intervalos ocupados para uma data (considerando duração de 1 hora)"""
        from datetime import datetime, time, timedelta
        inicio = datetime.combine(data, time.min)
        fim = datetime.combine(data, time.max)
        consultas = Consulta.query.filter(
            Consulta.medico_id == self.id,
            Consulta.data_hora >= inicio,
            Consulta.data_hora <= fim,
            Consulta.status != 'cancelada'
        ).all()
        # Retorna tuplas (inicio, fim) para cada consulta
        ocupados = []
        for c in consultas:
            inicio_c = c.data_hora
            fim_c = inicio_c + timedelta(hours=1)  # duração padrão 1h
            ocupados.append((inicio_c.strftime('%H:%M'), fim_c.strftime('%H:%M')))
        return ocupados

class Servico(db.Model, TimestampMixin):
    __tablename__ = 'servico'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False, index=True)
    categoria = db.Column(db.String(50), nullable=False, index=True)
    descricao = db.Column(db.Text)
    valor = db.Column(db.Numeric(10,2), nullable=False, default=0)
    ativo = db.Column(db.Boolean, default=True, nullable=False, index=True)

    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'categoria': self.categoria,
            'descricao': self.descricao,
            'valor': float(self.valor) if self.valor is not None else 0.0,
            'ativo': self.ativo,
            'criado_em': self.criado_em.isoformat() if self.criado_em else None,
            'atualizado_em': self.atualizado_em.isoformat() if self.atualizado_em else None,
        }

class Consulta(db.Model, TimestampMixin):
    __tablename__ = 'consulta'
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(50), default='normal')
    data_hora = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    status = db.Column(db.String(20), default='agendada', index=True)
    observacoes = db.Column(db.Text)
    motivo = db.Column(db.Text)
    valor = db.Column(db.Numeric(10,2), nullable=True)  # snapshot do valor

    paciente_id = db.Column(db.Integer, db.ForeignKey('paciente.id'), index=True)
    medico_id = db.Column(db.Integer, db.ForeignKey('medico.id'), index=True)
    servico_id = db.Column(db.Integer, db.ForeignKey('servico.id'), nullable=True, index=True)

    servico = db.relationship('Servico', backref='consultas')

    def to_dict(self):
        return {
            'id': self.id,
            'tipo': self.tipo,
            'data_hora': self.data_hora.isoformat() if self.data_hora else None,
            'status': self.status,
            'observacoes': self.observacoes,
            'motivo': self.motivo,
            'valor': float(self.valor) if self.valor is not None else 0.0,
            'servico': self.servico.to_dict() if self.servico else None,
            'paciente': self.paciente_consulta.to_dict() if self.paciente_consulta else None,
            'medico': self.medico_consulta.to_dict() if self.medico_consulta else None,
            'criado_em': self.criado_em.isoformat() if self.criado_em else None,
            'atualizado_em': self.atualizado_em.isoformat() if self.atualizado_em else None,
        }

class Exame(db.Model, TimestampMixin):
    __tablename__ = 'exame'
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(100), nullable=False, index=True)
    descricao = db.Column(db.Text)
    data = db.Column(db.DateTime(timezone=True), nullable=False, index=True)  # agora obrigatório
    resultado = db.Column(db.Text)
    status = db.Column(db.String(20), default='agendado', index=True)
    valor = db.Column(db.Numeric(10,2), nullable=True)

    paciente_id = db.Column(db.Integer, db.ForeignKey('paciente.id'), index=True)
    medico_solicitante_id = db.Column(db.Integer, db.ForeignKey('medico.id'), index=True)
    servico_id = db.Column(db.Integer, db.ForeignKey('servico.id'), nullable=True, index=True)

    medico_solicitante = db.relationship('Medico', foreign_keys=[medico_solicitante_id])
    servico = db.relationship('Servico', backref='exames')

    def to_dict(self):
        return {
            'id': self.id,
            'tipo': self.tipo,
            'descricao': self.descricao,
            'data': self.data.isoformat() if self.data else None,
            'resultado': self.resultado,
            'status': self.status,
            'valor': float(self.valor) if self.valor is not None else 0.0,
            'servico': self.servico.to_dict() if self.servico else None,
            'paciente': self.paciente_exame.to_dict() if self.paciente_exame else None,
            'medico_solicitante': self.medico_solicitante.to_dict() if self.medico_solicitante else None,
            'criado_em': self.criado_em.isoformat() if self.criado_em else None,
            'atualizado_em': self.atualizado_em.isoformat() if self.atualizado_em else None,
        }

class Atendimento(db.Model, TimestampMixin):
    __tablename__ = 'atendimento'
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(50), index=True)  # normal, urgência
    sintomas = db.Column(db.Text)  # JSON array
    diagnostico = db.Column(db.Text)
    evolucao = db.Column(db.Text)
    prescricao = db.Column(db.Text)
    data = db.Column(db.DateTime(timezone=True), default=_now, index=True)

    paciente_id = db.Column(db.Integer, db.ForeignKey('paciente.id'), index=True)
    medico_id = db.Column(db.Integer, db.ForeignKey('medico.id'), index=True)
    consulta_id = db.Column(db.Integer, db.ForeignKey('consulta.id'), nullable=True, index=True)

    consulta = db.relationship('Consulta', backref='atendimento_consulta')

    def to_dict(self):
        return {
            'id': self.id,
            'tipo': self.tipo,
            'sintomas': json.loads(self.sintomas) if self.sintomas else [],
            'diagnostico': self.diagnostico,
            'evolucao': self.evolucao,
            'prescricao': self.prescricao,
            'data': self.data.isoformat() if self.data else None,
            'paciente': self.paciente.to_dict() if self.paciente else None,
            'medico': self.medico_atendimento.to_dict() if self.medico_atendimento else None,
            'consulta_id': self.consulta_id,
            'criado_em': self.criado_em.isoformat() if self.criado_em else None,
            'atualizado_em': self.atualizado_em.isoformat() if self.atualizado_em else None,
        }

class Pagamento(db.Model, TimestampMixin):
    __tablename__ = 'pagamento'
    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(200))
    valor = db.Column(db.Numeric(10,2), nullable=False, default=0)
    data_vencimento = db.Column(db.Date, index=True)
    data_pagamento = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), default='pendente', index=True)
    metodo = db.Column(db.String(50))

    paciente_id = db.Column(db.Integer, db.ForeignKey('paciente.id'), index=True)
    servico_id = db.Column(db.Integer, db.ForeignKey('servico.id'), nullable=True, index=True)

    servico = db.relationship('Servico', backref='pagamentos')

    def to_dict(self):
        return {
            'id': self.id,
            'descricao': self.descricao,
            'valor': float(self.valor) if self.valor is not None else 0.0,
            'data_vencimento': self.data_vencimento.isoformat() if self.data_vencimento else None,
            'data_pagamento': self.data_pagamento.isoformat() if self.data_pagamento else None,
            'status': self.status,
            'metodo': self.metodo,
            'servico': self.servico.to_dict() if self.servico else None,
            'paciente': self.paciente_pagamento.to_dict() if self.paciente_pagamento else None,
            'criado_em': self.criado_em.isoformat() if self.criado_em else None,
            'atualizado_em': self.atualizado_em.isoformat() if self.atualizado_em else None,
        }

class Receita(db.Model, TimestampMixin):
    __tablename__ = 'receita'
    id = db.Column(db.Integer, primary_key=True)
    medicamentos = db.Column(db.Text)  # JSON array
    observacoes = db.Column(db.Text)
    data_emissao = db.Column(db.DateTime(timezone=True), default=_now, index=True)

    paciente_id = db.Column(db.Integer, db.ForeignKey('paciente.id'), index=True)
    medico_id = db.Column(db.Integer, db.ForeignKey('medico.id'), index=True)
    atendimento_id = db.Column(db.Integer, db.ForeignKey('atendimento.id'), nullable=True, index=True)

    atendimento = db.relationship('Atendimento', backref='receita_atendimento')

    def to_dict(self):
        return {
            'id': self.id,
            'medicamentos': json.loads(self.medicamentos) if self.medicamentos else [],
            'observacoes': self.observacoes,
            'data_emissao': self.data_emissao.isoformat() if self.data_emissao else None,
            'paciente': self.paciente_receita.to_dict() if self.paciente_receita else None,
            'medico': self.medico_receita.to_dict() if self.medico_receita else None,
            'atendimento_id': self.atendimento_id,
            'criado_em': self.criado_em.isoformat() if self.criado_em else None,
            'atualizado_em': self.atualizado_em.isoformat() if self.atualizado_em else None,
        }

class Medicamento(db.Model, TimestampMixin):
    __tablename__ = 'medicamento'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), nullable=False, index=True)
    principio_ativo = db.Column(db.String(500))
    dosagem = db.Column(db.String(100))
    forma_farmaceutica = db.Column(db.String(100))
    tipo_produto = db.Column(db.String(50))
    categoria_regulatoria = db.Column(db.String(100))
    numero_registro_produto = db.Column(db.String(50), unique=True, index=True)
    data_finalizacao_processo = db.Column(db.String(20))
    data_vencimento_registro = db.Column(db.String(20))
    numero_processo = db.Column(db.String(50))
    classe_terapeutica = db.Column(db.String(200))
    fabricante = db.Column(db.String(200))
    situacao_registro = db.Column(db.String(50))
    descricao = db.Column(db.Text)

    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'principio_ativo': self.principio_ativo,
            'dosagem': self.dosagem,
            'forma_farmaceutica': self.forma_farmaceutica,
            'tipo_produto': self.tipo_produto,
            'categoria_regulatoria': self.categoria_regulatoria,
            'numero_registro_produto': self.numero_registro_produto,
            'data_finalizacao_processo': self.data_finalizacao_processo,
            'data_vencimento_registro': self.data_vencimento_registro,
            'numero_processo': self.numero_processo,
            'classe_terapeutica': self.classe_terapeutica,
            'fabricante': self.fabricante,
            'situacao_registro': self.situacao_registro,
            'descricao': self.descricao,
            'criado_em': self.criado_em.isoformat() if self.criado_em else None,
            'atualizado_em': self.atualizado_em.isoformat() if self.atualizado_em else None,
        }