from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, date, timezone, timedelta
from core.models import db, Consulta, Paciente, Medico, Servico
from core.utils import validar_valor, parse_data_hora

consultas_bp = Blueprint('consultas', __name__, url_prefix='/consultas')

@consultas_bp.route('/')
def listar_consultas():
    status = request.args.get('status', '')
    data_inicio = request.args.get('data_inicio', '')
    data_fim = request.args.get('data_fim', '')
    page = request.args.get('page', 1, type=int)
    per_page = 20

    query = Consulta.query.options(
        joinedload(Consulta.paciente_consulta),
        joinedload(Consulta.medico_consulta),
        joinedload(Consulta.servico)
    )

    if status:
        query = query.filter(Consulta.status == status)
    if data_inicio:
        try:
            dt = datetime.strptime(data_inicio, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            query = query.filter(Consulta.data_hora >= dt)
        except ValueError:
            pass
    if data_fim:
        try:
            dt = datetime.strptime(data_fim, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            dt = dt.replace(hour=23, minute=59, second=59)
            query = query.filter(Consulta.data_hora <= dt)
        except ValueError:
            pass

    consultas = query.order_by(Consulta.data_hora.desc()).paginate(page=page, per_page=per_page, error_out=False)

    return render_template('consultas.html', consultas=consultas, status=status,
                           data_inicio=data_inicio, data_fim=data_fim)

@consultas_bp.route('/novo', methods=['GET', 'POST'])
def nova_consulta():
    pacientes = Paciente.query.order_by(Paciente.nome).all()
    medicos = Medico.query.filter_by(ativo=True).order_by(Medico.nome).all()
    servicos = Servico.query.filter(Servico.ativo.is_(True), Servico.categoria.ilike('consulta')).order_by(Servico.nome).all()

    if request.method == 'POST':
        paciente_id = request.form.get('paciente_id', type=int)
        medico_id = request.form.get('medico_id', type=int)
        servico_id = request.form.get('servico_id', type=int)
        data_str = request.form.get('data')
        hora_str = request.form.get('hora')
        tipo = request.form.get('tipo', 'normal')
        motivo = request.form.get('motivo', '').strip()

        if not paciente_id:
            flash('Selecione um paciente.', 'danger')
            return redirect(url_for('consultas.nova_consulta'))
        if not medico_id:
            flash('Selecione um médico.', 'danger')
            return redirect(url_for('consultas.nova_consulta'))
        if not servico_id:
            flash('Selecione o serviço.', 'danger')
            return redirect(url_for('consultas.nova_consulta'))
        if not data_str or not hora_str:
            flash('Informe data e hora.', 'danger')
            return redirect(url_for('consultas.nova_consulta'))

        paciente = Paciente.query.get(paciente_id)
        if not paciente:
            flash('Paciente não encontrado.', 'danger')
            return redirect(url_for('consultas.nova_consulta'))

        medico = Medico.query.filter_by(id=medico_id, ativo=True).first()
        if not medico:
            flash('Médico inválido ou inativo.', 'danger')
            return redirect(url_for('consultas.nova_consulta'))

        servico = Servico.query.filter(Servico.id == servico_id, Servico.ativo.is_(True)).first()
        if not servico:
            flash('Serviço inválido ou inativo.', 'danger')
            return redirect(url_for('consultas.nova_consulta'))

        data_hora = parse_data_hora(data_str, hora_str)
        if not data_hora:
            flash('Data ou hora inválida!', 'danger')
            return redirect(url_for('consultas.nova_consulta'))

        # Impede passado
        if data_hora < datetime.now(timezone.utc):
            flash('Não é possível agendar no passado.', 'danger')
            return redirect(url_for('consultas.nova_consulta'))

        # Verifica conflito (sobreposição de 1 hora)
        fim_consulta = data_hora + timedelta(hours=1)
        conflito = Consulta.query.filter(
            Consulta.medico_id == medico_id,
            Consulta.status != 'cancelada',
            Consulta.data_hora < fim_consulta,
            Consulta.data_hora + timedelta(hours=1) > data_hora
        ).first()
        if conflito:
            flash('Horário já ocupado (ou sobreposto).', 'danger')
            return redirect(url_for('consultas.nova_consulta'))

        # Cria consulta
        consulta = Consulta(
            paciente_id=paciente.id,
            medico_id=medico.id,
            servico_id=servico.id,
            valor=servico.valor,
            data_hora=data_hora,
            tipo=tipo,
            motivo=motivo,
            status='agendada'
        )

        try:
            db.session.add(consulta)
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f'Erro ao agendar: {str(e)}', 'danger')
            return redirect(url_for('consultas.nova_consulta'))

        flash(f'Consulta agendada! Serviço: {servico.nome} - R$ {float(servico.valor):.2f}', 'success')
        return redirect(url_for('consultas.listar_consultas'))

    return render_template('consultas_form.html', pacientes=pacientes, medicos=medicos,
                           servicos=servicos, hoje=date.today().isoformat())

@consultas_bp.route('/<int:cid>/confirmar', methods=['POST'])
def confirmar_consulta(cid):
    consulta = Consulta.query.get_or_404(cid)
    if consulta.status == 'agendada':
        consulta.status = 'confirmada'
        db.session.commit()
        flash('Consulta confirmada!', 'success')
    else:
        flash('Não foi possível confirmar.', 'warning')
    return redirect(url_for('consultas.listar_consultas'))

@consultas_bp.route('/<int:cid>/cancelar', methods=['POST'])
def cancelar_consulta(cid):
    consulta = Consulta.query.get_or_404(cid)
    if consulta.status == 'realizada':
        flash('Consulta já realizada não pode ser cancelada.', 'warning')
    else:
        consulta.status = 'cancelada'
        db.session.commit()
        flash('Consulta cancelada.', 'success')
    return redirect(url_for('consultas.listar_consultas'))

@consultas_bp.route('/<int:cid>/realizar', methods=['POST'])
def realizar_consulta(cid):
    consulta = Consulta.query.get_or_404(cid)
    if consulta.status == 'cancelada':
        flash('Consulta cancelada não pode ser realizada.', 'warning')
    else:
        consulta.status = 'realizada'
        db.session.commit()
        flash('Consulta realizada!', 'success')
    return redirect(url_for('consultas.listar_consultas'))

@consultas_bp.route('/<int:cid>')
def detalhes_consulta(cid):
    consulta = Consulta.query.options(
        joinedload(Consulta.paciente_consulta),
        joinedload(Consulta.medico_consulta),
        joinedload(Consulta.servico)
    ).get_or_404(cid)
    return render_template('consulta_detalhes.html', consulta=consulta)