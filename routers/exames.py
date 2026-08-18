from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from sqlalchemy.orm import joinedload
from datetime import datetime, timezone
from core.models import db, Exame, Paciente, Medico, Servico
from core.utils import parse_data_hora, validar_valor

exames_bp = Blueprint('exames', __name__, url_prefix='/exames')

@exames_bp.route('/')
def listar_exames():
    status = request.args.get('status', '')
    page = request.args.get('page', 1, type=int)
    per_page = 20

    query = Exame.query.options(
        joinedload(Exame.paciente_exame),
        joinedload(Exame.medico_solicitante),
        joinedload(Exame.servico)
    )
    if status:
        query = query.filter(Exame.status == status)
    exames = query.order_by(Exame.data.desc()).paginate(page=page, per_page=per_page, error_out=False)

    return render_template('exames.html', exames=exames, status=status)

@exames_bp.route('/novo', methods=['GET', 'POST'])
def novo_exame():
    pacientes = Paciente.query.order_by(Paciente.nome).all()
    medicos = Medico.query.filter_by(ativo=True).order_by(Medico.nome).all()
    servicos = Servico.query.filter_by(ativo=True).order_by(Servico.nome).all()  # serviços para exame

    if request.method == 'POST':
        paciente_id = request.form.get('paciente_id', type=int)
        medico_id = request.form.get('medico_id', type=int)
        servico_id = request.form.get('servico_id', type=int)
        tipo = request.form.get('tipo', '').strip()
        descricao = request.form.get('descricao', '').strip()
        data_str = request.form.get('data', '')
        hora_str = request.form.get('hora', '')

        if not paciente_id:
            flash('Paciente obrigatório.', 'danger')
            return redirect(url_for('exames.novo_exame'))
        if not tipo:
            flash('Tipo de exame obrigatório.', 'danger')
            return redirect(url_for('exames.novo_exame'))
        if not data_str or not hora_str:
            flash('Data e hora obrigatórias.', 'danger')
            return redirect(url_for('exames.novo_exame'))

        data_hora = parse_data_hora(data_str, hora_str)
        if not data_hora:
            flash('Data/hora inválida.', 'danger')
            return redirect(url_for('exames.novo_exame'))

        # Valor do serviço (se selecionado)
        valor = None
        servico = None
        if servico_id:
            servico = Servico.query.get(servico_id)
            if servico:
                valor = servico.valor

        exame = Exame(
            paciente_id=paciente_id,
            medico_solicitante_id=medico_id,
            servico_id=servico_id,
            tipo=tipo,
            descricao=descricao,
            data=data_hora,
            valor=valor,
            status='agendado'
        )

        db.session.add(exame)
        db.session.commit()
        flash('Exame agendado com sucesso!', 'success')
        return redirect(url_for('exames.listar_exames'))

    return render_template('exames_form.html', pacientes=pacientes, medicos=medicos, servicos=servicos)

@exames_bp.route('/<int:eid>/resultado', methods=['POST'])
def registrar_resultado(eid):
    exame = Exame.query.get_or_404(eid)
    exame.resultado = request.form.get('resultado', '')
    exame.status = 'realizado'
    db.session.commit()
    flash('Resultado registrado!', 'success')
    return redirect(url_for('exames.listar_exames'))

@exames_bp.route('/<int:eid>/cancelar', methods=['POST'])
def cancelar_exame(eid):
    exame = Exame.query.get_or_404(eid)
    exame.status = 'cancelado'
    db.session.commit()
    flash('Exame cancelado!', 'success')
    return redirect(url_for('exames.listar_exames'))