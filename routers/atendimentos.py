from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from sqlalchemy.orm import joinedload
from datetime import datetime, timezone
from core.models import db, Atendimento, Paciente, Medico, Receita
import json

atendimentos_bp = Blueprint('atendimentos', __name__, url_prefix='/atendimentos')

@atendimentos_bp.route('/')
def listar_atendimentos():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    atendimentos = Atendimento.query.options(
        joinedload(Atendimento.paciente),
        joinedload(Atendimento.medico_atendimento)
    ).order_by(Atendimento.data.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return render_template('atendimentos.html', atendimentos=atendimentos)

@atendimentos_bp.route('/novo', methods=['GET', 'POST'])
def novo_atendimento():
    pacientes = Paciente.query.order_by(Paciente.nome).all()
    medicos = Medico.query.filter_by(ativo=True).order_by(Medico.nome).all()

    if request.method == 'POST':
        tipo = request.form.get('tipo', 'normal')
        sintomas_raw = request.form.get('sintomas', '')
        diagnostico = request.form.get('diagnostico', '')
        evolucao = request.form.get('evolucao', '')
        prescricao = request.form.get('prescricao', '')
        paciente_id = request.form.get('paciente_id', type=int)
        medico_id = request.form.get('medico_id', type=int)

        if not paciente_id:
            flash('Paciente obrigatório.', 'danger')
            return redirect(url_for('atendimentos.novo_atendimento'))

        # Sintomas como lista (separados por vírgula ou ponto e vírgula)
        sintomas_list = []
        if sintomas_raw:
            # Tenta split por ; ou ,
            for sep in [';', ',']:
                if sep in sintomas_raw:
                    sintomas_list = [s.strip() for s in sintomas_raw.split(sep) if s.strip()]
                    break
            if not sintomas_list:
                sintomas_list = [sintomas_raw.strip()]

        atendimento = Atendimento(
            tipo=tipo,
            sintomas=json.dumps(sintomas_list, ensure_ascii=False),
            diagnostico=diagnostico,
            evolucao=evolucao,
            prescricao=prescricao,
            paciente_id=paciente_id,
            medico_id=medico_id,
            data=datetime.now(timezone.utc)
        )
        db.session.add(atendimento)
        db.session.commit()

        # Gerar receita se houver prescrição (cada linha como medicamento)
        if prescricao:
            medicamentos = []
            for linha in prescricao.splitlines():
                if linha.strip():
                    medicamentos.append({'nome': linha.strip(), 'dosagem': '', 'frequencia': ''})
            if medicamentos:
                receita = Receita(
                    medicamentos=json.dumps(medicamentos, ensure_ascii=False),
                    observacoes=diagnostico,
                    paciente_id=paciente_id,
                    medico_id=medico_id,
                    atendimento_id=atendimento.id
                )
                db.session.add(receita)
                db.session.commit()
                flash('Atendimento registrado e receita gerada automaticamente!', 'success')
            else:
                flash('Atendimento registrado!', 'success')
        else:
            flash('Atendimento registrado!', 'success')

        return redirect(url_for('atendimentos.listar_atendimentos'))

    return render_template('atendimentos.html', pacientes=pacientes, medicos=medicos, novo=True)

@atendimentos_bp.route('/<int:aid>')
def detalhes_atendimento(aid):
    atendimento = Atendimento.query.options(
        joinedload(Atendimento.paciente),
        joinedload(Atendimento.medico_atendimento)
    ).get_or_404(aid)
    return render_template('atendimento_detalhes.html', atendimento=atendimento)

@atendimentos_bp.route('/<int:aid>/json')
def atendimento_json(aid):
    a = Atendimento.query.get_or_404(aid)
    return jsonify(a.to_dict())

@atendimentos_bp.route('/<int:aid>/evolucao', methods=['POST'])
def adicionar_evolucao(aid):
    atendimento = Atendimento.query.get_or_404(aid)
    nova_evolucao = request.form.get('evolucao', '')
    if not nova_evolucao:
        flash('Evolução vazia.', 'warning')
        return redirect(url_for('atendimentos.detalhes_atendimento', aid=aid))

    timestamp = datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')
    if atendimento.evolucao:
        atendimento.evolucao += f"\n\n[{timestamp}]: {nova_evolucao}"
    else:
        atendimento.evolucao = f"[{timestamp}]: {nova_evolucao}"

    db.session.commit()
    flash('Evolução registrada!', 'success')
    return redirect(url_for('atendimentos.detalhes_atendimento', aid=aid))