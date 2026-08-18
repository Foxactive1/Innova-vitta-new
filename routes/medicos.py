from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from sqlalchemy.exc import IntegrityError
from core.models import db, Medico, Consulta
from core.utils import validar_nome
import json

medicos_bp = Blueprint('medicos', __name__, url_prefix='/medicos')

@medicos_bp.route('/')
def listar_medicos():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    medicos = Medico.query.order_by(Medico.nome).paginate(page=page, per_page=per_page, error_out=False)
    return render_template('medicos.html', medicos=medicos)

@medicos_bp.route('/novo', methods=['GET', 'POST'])
def novo_medico():
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        especialidade = request.form.get('especialidade', '').strip()
        crm = request.form.get('crm', '').strip()
        telefone = request.form.get('telefone', '').strip()
        email = request.form.get('email', '').strip()

        if not validar_nome(nome) or not crm:
            flash('Nome e CRM são obrigatórios!', 'danger')
            return redirect(url_for('medicos.novo_medico'))

        medico = Medico(
            nome=nome,
            especialidade=especialidade,
            crm=crm,
            telefone=telefone,
            email=email
        )
        try:
            db.session.add(medico)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash('CRM já cadastrado!', 'danger')
            return redirect(url_for('medicos.novo_medico'))

        flash('Médico cadastrado com sucesso!', 'success')
        return redirect(url_for('medicos.listar_medicos'))

    return render_template('medico_form.html')  # Novo template para formulário

@medicos_bp.route('/<int:id>')
def medico_detalhes(id):
    medico = Medico.query.get_or_404(id)
    consultas = Consulta.query.filter(
        Consulta.medico_id == id,
        Consulta.status != 'cancelada'
    ).order_by(Consulta.data_hora.desc()).all()
    return render_template('medico_detalhes.html', medico=medico, consultas_medico=consultas)

@medicos_bp.route('/<int:mid>/json')
def medico_json(mid):
    m = Medico.query.get_or_404(mid)
    return jsonify(m.to_dict())

@medicos_bp.route('/<int:mid>/horarios', methods=['GET', 'POST'])
def gerenciar_horarios(mid):
    medico = Medico.query.get_or_404(mid)

    if request.method == 'POST':
        horarios = {}
        dias = ['seg', 'ter', 'qua', 'qui', 'sex', 'sab']
        for dia in dias:
            horas = request.form.getlist(f'horarios_{dia}')
            if horas:
                horarios[dia] = horas
        medico.horarios_disponiveis = json.dumps(horarios)
        db.session.commit()
        flash('Horários atualizados!', 'success')
        return redirect(url_for('medicos.gerenciar_horarios', mid=mid))

    horarios_atuais = json.loads(medico.horarios_disponiveis) if medico.horarios_disponiveis else {}
    return render_template('medico_horarios.html', medico=medico, horarios=horarios_atuais)