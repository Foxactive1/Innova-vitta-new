from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
from core.models import db, Paciente, Atendimento, Consulta, Exame, Receita
from core.utils import normalizar_cpf, validar_nome, estatisticas_gerais
import json
from datetime import datetime, timezone

pacientes_bp = Blueprint('pacientes', __name__, url_prefix='/pacientes')

@pacientes_bp.route('/')
def listar_pacientes():
    busca = request.args.get('busca', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 20

    query = Paciente.query
    if busca:
        query = query.filter(Paciente.nome.ilike(f'%{busca}%'))
    pacientes = query.order_by(Paciente.nome).paginate(page=page, per_page=per_page, error_out=False)

    # Estatísticas (apenas se não houver busca)
    stats = None
    if not busca:
        stats = estatisticas_gerais()

    return render_template('pacientes.html', pacientes=pacientes, busca=busca, stats=stats)

@pacientes_bp.route('/novo', methods=['GET', 'POST'])
def novo_paciente():
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        data_nascimento_str = request.form.get('data_nascimento', '').strip()
        sexo = request.form.get('sexo', '').strip()
        telefone = request.form.get('telefone', '').strip()
        cpf = normalizar_cpf(request.form.get('cpf', '').strip())
        rg = request.form.get('rg', '').strip() or None
        endereco = request.form.get('endereco', '').strip()
        doencas = request.form.get('doencas', '').strip()

        if not validar_nome(nome):
            flash('Nome é obrigatório!', 'danger')
            return redirect(url_for('pacientes.novo_paciente'))

        # Parse data nascimento
        data_nascimento = None
        if data_nascimento_str:
            try:
                data_nascimento = datetime.strptime(data_nascimento_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Data de nascimento inválida!', 'danger')
                return redirect(url_for('pacientes.novo_paciente'))

        # CPF duplicado
        if cpf:
            existente = Paciente.query.filter_by(cpf=cpf).first()
            if existente:
                flash(f'Já existe um paciente com este CPF: {existente.nome}', 'danger')
                return redirect(url_for('pacientes.novo_paciente'))

        doencas_list = [d.strip() for d in doencas.split(',') if d.strip()]

        paciente = Paciente(
            nome=nome,
            data_nascimento=data_nascimento,
            sexo=sexo or None,
            telefone=telefone or None,
            cpf=cpf,
            rg=rg,
            endereco=endereco or None,
            doencas_previas=json.dumps(doencas_list, ensure_ascii=False)
        )

        try:
            db.session.add(paciente)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash('Erro ao cadastrar paciente. CPF pode estar duplicado.', 'danger')
            return redirect(url_for('pacientes.novo_paciente'))

        flash('Paciente cadastrado com sucesso!', 'success')
        return redirect(url_for('pacientes.listar_pacientes'))

    return render_template('pacientes_form.html')

@pacientes_bp.route('/<int:id>')
def paciente_detalhes(id):
    paciente = Paciente.query.options(
        joinedload(Paciente.atendimentos),
        joinedload(Paciente.consultas),
        joinedload(Paciente.exames),
        joinedload(Paciente.receitas)
    ).get_or_404(id)
    return render_template('paciente_detalhes.html', paciente=paciente)

@pacientes_bp.route('/<int:pid>/json')
def paciente_json(pid):
    p = Paciente.query.get_or_404(pid)
    return jsonify(p.to_dict_completo())

@pacientes_bp.route('/<int:pid>/editar', methods=['GET', 'POST'])
def editar_paciente(pid):
    paciente = Paciente.query.get_or_404(pid)

    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        data_nascimento_str = request.form.get('data_nascimento', '').strip()
        sexo = request.form.get('sexo', '').strip()
        telefone = request.form.get('telefone', '').strip()
        cpf = normalizar_cpf(request.form.get('cpf', '').strip())
        rg = request.form.get('rg', '').strip() or None
        endereco = request.form.get('endereco', '').strip()
        doencas = request.form.get('doencas', '').strip()

        if not validar_nome(nome):
            flash('Nome é obrigatório!', 'danger')
            return redirect(url_for('pacientes.editar_paciente', pid=pid))

        data_nascimento = None
        if data_nascimento_str:
            try:
                data_nascimento = datetime.strptime(data_nascimento_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Data de nascimento inválida!', 'danger')
                return redirect(url_for('pacientes.editar_paciente', pid=pid))

        if cpf:
            existente = Paciente.query.filter(Paciente.cpf == cpf, Paciente.id != pid).first()
            if existente:
                flash(f'CPF já pertence a {existente.nome}', 'danger')
                return redirect(url_for('pacientes.editar_paciente', pid=pid))

        paciente.nome = nome
        paciente.data_nascimento = data_nascimento
        paciente.sexo = sexo or None
        paciente.telefone = telefone or None
        paciente.cpf = cpf
        paciente.rg = rg
        paciente.endereco = endereco or None
        paciente.doencas_previas = json.dumps([d.strip() for d in doencas.split(',') if d.strip()], ensure_ascii=False)

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash('Erro ao atualizar. CPF pode estar duplicado.', 'danger')
            return redirect(url_for('pacientes.editar_paciente', pid=pid))

        flash('Paciente atualizado com sucesso!', 'success')
        return redirect(url_for('pacientes.paciente_detalhes', id=pid))

    return render_template('pacientes_form.html', paciente=paciente, editar=True)

@pacientes_bp.route('/<int:pid>/remover', methods=['POST'])
def remover_paciente(pid):
    paciente = Paciente.query.get_or_404(pid)
    db.session.delete(paciente)
    db.session.commit()
    flash('Paciente removido com sucesso!', 'success')
    return redirect(url_for('pacientes.listar_pacientes'))

@pacientes_bp.route('/estatisticas')
def estatisticas_pacientes():
    stats = estatisticas_gerais()
    return render_template('pacientes_estatisticas.html', stats=stats)