from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, make_response
from sqlalchemy.orm import joinedload
from core.models import db, Receita, Paciente, Medico, Atendimento

# Medicamento é opcional — importe apenas se o modelo existir em core/models.py
try:
    from core.models import Medicamento
    _medicamento_disponivel = True
except ImportError:
    _medicamento_disponivel = False

import json

receitas_bp = Blueprint('receitas', __name__, url_prefix='/receitas')

@receitas_bp.route('/')
def listar_receitas():
    # PAGINAÇÃO CORRIGIDA
    page = request.args.get('page', 1, type=int)
    per_page = 20
    receitas = (Receita.query
                .options(joinedload(Receita.paciente_receita),
                         joinedload(Receita.medico_receita))
                .order_by(Receita.data_emissao.desc())
                .paginate(page=page, per_page=per_page, error_out=False))
    return render_template('receitas.html', receitas=receitas)

@receitas_bp.route('/nova', methods=['GET', 'POST'])
def nova_receita():
    pacientes = Paciente.query.order_by(Paciente.nome).all()
    medicos = Medico.query.filter_by(ativo=True).order_by(Medico.nome).all()
    atendimentos = Atendimento.query.order_by(Atendimento.data.desc()).all()
    
    if request.method == 'POST':
        paciente_id = int(request.form.get('paciente_id'))
        medico_id = int(request.form.get('medico_id'))
        atendimento_id = request.form.get('atendimento_id')
        atendimento_id = int(atendimento_id) if atendimento_id else None
        observacoes = request.form.get('observacoes', '')
        
        medicamentos = []
        nomes = request.form.getlist('med_nome[]')
        dosagens = request.form.getlist('med_dosagem[]')
        frequencias = request.form.getlist('med_frequencia[]')
        
        for i in range(len(nomes)):
            if nomes[i].strip():
                medicamentos.append({
                    'nome': nomes[i].strip(),
                    'dosagem': dosagens[i] if i < len(dosagens) else '',
                    'frequencia': frequencias[i] if i < len(frequencias) else ''
                })
        
        receita = Receita(
            medicamentos=json.dumps(medicamentos),
            observacoes=observacoes,
            paciente_id=paciente_id,
            medico_id=medico_id,
            atendimento_id=atendimento_id
        )
        db.session.add(receita)
        db.session.commit()
        flash('Receita emitida com sucesso!', 'success')
        return redirect(url_for('receitas.listar_receitas'))
    
    return render_template('receitas_form.html', 
                           pacientes=pacientes, 
                           medicos=medicos, 
                           atendimentos=atendimentos)

@receitas_bp.route('/<int:rid>')
def detalhes_receita(rid):
    receita = Receita.query.options(
        joinedload(Receita.paciente_receita),
        joinedload(Receita.medico_receita)
    ).get_or_404(rid)
    return render_template('receita_detalhes.html', receita=receita)

@receitas_bp.route('/<int:rid>/imprimir')
def imprimir_receita(rid):
    receita = Receita.query.get_or_404(rid)
    html = render_template('receita_imprimir.html', receita=receita)
    response = make_response(html)
    response.headers['Content-Type'] = 'text/html'
    return response

# ✅ ROTA DE AUTOCOMPLETE – busca medicamentos por nome
@receitas_bp.route('/api/medicamentos')
def api_medicamentos():
    """Autocomplete de medicamentos. Requer modelo Medicamento em core/models.py."""
    if not _medicamento_disponivel:
        return jsonify({'erro': 'Modelo Medicamento não disponível'}), 501

    q = request.args.get('q', '').strip()
    if len(q) < 2:
        return jsonify([])

    medicamentos = Medicamento.query.filter(
        Medicamento.nome.ilike(f'%{q}%')
    ).limit(20).all()

    return jsonify([{'id': m.id, 'nome': m.nome} for m in medicamentos])