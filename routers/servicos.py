from flask import Blueprint, render_template, request, redirect, url_for, flash
from sqlalchemy.exc import IntegrityError
from core.models import db, Servico
from core.utils import validar_nome, validar_valor

servicos_bp = Blueprint('servicos', __name__, url_prefix='/servicos')

@servicos_bp.route('/')
def listar_servicos():
    categoria = request.args.get('categoria', '').strip()
    busca = request.args.get('busca', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 20

    query = Servico.query
    if categoria:
        query = query.filter(Servico.categoria == categoria)
    if busca:
        query = query.filter(Servico.nome.ilike(f'%{busca}%'))

    servicos = query.order_by(Servico.nome.asc()).paginate(page=page, per_page=per_page, error_out=False)

    # Categorias para filtro
    categorias = [c[0] for c in db.session.query(Servico.categoria).distinct().order_by(Servico.categoria).all() if c[0]]

    return render_template('servicos.html', servicos=servicos, categorias=categorias,
                           categoria=categoria, busca=busca)

@servicos_bp.route('/novo', methods=['GET', 'POST'])
def novo_servico():
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        categoria = request.form.get('categoria', '').strip()
        descricao = request.form.get('descricao', '').strip()
        valor_str = request.form.get('valor', '0').strip()

        if not validar_nome(nome):
            flash('Informe o nome do serviço.', 'danger')
            return redirect(url_for('servicos.novo_servico'))
        if not validar_nome(categoria):
            flash('Informe a categoria.', 'danger')
            return redirect(url_for('servicos.novo_servico'))

        valor = validar_valor(valor_str)
        if valor is None:
            flash('Valor inválido ou negativo.', 'danger')
            return redirect(url_for('servicos.novo_servico'))

        servico = Servico(
            nome=nome,
            categoria=categoria,
            descricao=descricao,
            valor=valor,
            ativo=True
        )
        db.session.add(servico)
        db.session.commit()
        flash(f'Serviço "{nome}" cadastrado com sucesso!', 'success')
        return redirect(url_for('servicos.listar_servicos'))

    return render_template('servico_form.html', servico=None, titulo='Novo Serviço')

@servicos_bp.route('/<int:sid>/editar', methods=['GET', 'POST'])
def editar_servico(sid):
    servico = Servico.query.get_or_404(sid)

    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        categoria = request.form.get('categoria', '').strip()
        descricao = request.form.get('descricao', '').strip()
        valor_str = request.form.get('valor', '0').strip()

        if not validar_nome(nome):
            flash('Informe o nome do serviço.', 'danger')
            return redirect(url_for('servicos.editar_servico', sid=sid))
        if not validar_nome(categoria):
            flash('Informe a categoria.', 'danger')
            return redirect(url_for('servicos.editar_servico', sid=sid))

        valor = validar_valor(valor_str)
        if valor is None:
            flash('Valor inválido ou negativo.', 'danger')
            return redirect(url_for('servicos.editar_servico', sid=sid))

        servico.nome = nome
        servico.categoria = categoria
        servico.descricao = descricao
        servico.valor = valor
        db.session.commit()
        flash('Serviço atualizado com sucesso!', 'success')
        return redirect(url_for('servicos.listar_servicos'))

    return render_template('servico_form.html', servico=servico, titulo='Editar Serviço')

@servicos_bp.route('/<int:sid>/alternar', methods=['POST'])
def alternar_servico(sid):
    servico = Servico.query.get_or_404(sid)
    servico.ativo = not servico.ativo
    db.session.commit()
    estado = 'ativado' if servico.ativo else 'desativado'
    flash(f'Serviço "{servico.nome}" {estado}.', 'success')
    return redirect(url_for('servicos.listar_servicos'))

@servicos_bp.route('/<int:sid>/excluir', methods=['POST'])
def excluir_servico(sid):
    servico = Servico.query.get_or_404(sid)
    db.session.delete(servico)
    db.session.commit()
    flash('Serviço excluído com sucesso.', 'success')
    return redirect(url_for('servicos.listar_servicos'))