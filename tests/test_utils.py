"""
Testes unitários para funções utilitárias.
"""

from datetime import date, datetime, timezone

from core.utils import (
    validar_nome,
    validar_valor,
    normalizar_cpf,
    parse_data_hora,
    parse_data,
    inicio_mes,
    inicio_proximo_mes,
    verificar_controle_acesso,
    tabela_verdade_consulta_normal,
    tabela_verdade_emergencia,
)


# ============================================================
# VALIDAÇÃO DE NOME
# ============================================================

class TestValidarNome:

    def test_nome_valido(self):
        assert validar_nome("João Silva") is True

    def test_nome_vazio(self):
        assert validar_nome("") is False

    def test_nome_none(self):
        assert validar_nome(None) is False

    def test_nome_so_espacos(self):
        assert validar_nome("   ") is False


# ============================================================
# VALIDAÇÃO DE VALOR
# ============================================================

class TestValidarValor:

    def test_valor_inteiro(self):
        assert validar_valor("100") == 100.0

    def test_valor_decimal_ponto(self):
        assert validar_valor("100.50") == 100.50

    def test_valor_decimal_virgula(self):
        assert validar_valor("100,50") == 100.50

    def test_valor_milhar_brasileiro(self):
        assert validar_valor("1.000,50") == 1000.50

    def test_valor_zero(self):
        assert validar_valor("0") == 0.0

    def test_valor_negativo(self):
        assert validar_valor("-50") is None

    def test_valor_vazio(self):
        assert validar_valor("") is None

    def test_valor_none(self):
        assert validar_valor(None) is None

    def test_valor_invalido(self):
        assert validar_valor("abc") is None


# ============================================================
# NORMALIZAR CPF
# ============================================================

class TestNormalizarCPF:

    def test_cpf_formatado(self):
        assert normalizar_cpf("123.456.789-00") == "12345678900"

    def test_cpf_so_numeros(self):
        assert normalizar_cpf("12345678900") == "12345678900"

    def test_cpf_none(self):
        assert normalizar_cpf(None) is None

    def test_cpf_vazio(self):
        assert normalizar_cpf("") is None


# ============================================================
# PARSE DATA HORA
# ============================================================

class TestParseDataHora:

    def test_data_hora_valida(self, app):
        with app.app_context():
            result = parse_data_hora("2026-10-15", "14:30")
            assert result is not None
            assert result.tzinfo is not None  # timezone-aware
            # 14:30 em São Paulo (UTC-3) = 17:30 UTC
            assert result.hour == 17
            assert result.minute == 30

    def test_data_hora_vazia(self, app):
        with app.app_context():
            assert parse_data_hora("", "14:00") is None
            assert parse_data_hora("2026-10-15", "") is None
            assert parse_data_hora(None, None) is None

    def test_data_hora_invalida(self, app):
        with app.app_context():
            assert parse_data_hora("15/10/2026", "14:00") is None
            assert parse_data_hora("2026-10-15", "25:00") is None


# ============================================================
# PARSE DATA
# ============================================================

class TestParseData:

    def test_data_valida(self):
        result = parse_data("2026-10-15")
        assert result == date(2026, 10, 15)

    def test_data_vazia(self):
        assert parse_data("") is None
        assert parse_data(None) is None

    def test_data_invalida(self):
        assert parse_data("15/10/2026") is None
        assert parse_data("2026-13-01") is None


# ============================================================
# INÍCIO DE MÊS
# ============================================================

class TestInicioMes:

    def test_inicio_mes(self):
        result = inicio_mes(2026, 10)
        assert result.year == 2026
        assert result.month == 10
        assert result.day == 1
        assert result.tzinfo == timezone.utc

    def test_inicio_proximo_mes(self):
        result = inicio_proximo_mes(2026, 10)
        assert result.year == 2026
        assert result.month == 11

    def test_inicio_proximo_mes_dezembro(self):
        result = inicio_proximo_mes(2026, 12)
        assert result.year == 2027
        assert result.month == 1


# ============================================================
# CONTROLE DE ACESSO — TABELA VERDADE
# ============================================================

class TestControleAcesso:

    def test_consulta_normal_basica(self):
        # A=1, B=1, C=1 → atendido
        assert verificar_controle_acesso(True, True, True, False) is True

    def test_consulta_normal_sem_agendamento(self):
        # A=0, B=1, C=1, D=1 → atendido (via B∧C∧D)
        assert verificar_controle_acesso(False, True, True, True) is True

    def test_consulta_normal_sem_medico(self):
        # C=0 → nunca atendido
        assert verificar_controle_acesso(True, True, False, True) is False

    def test_emergencia_com_medico_e_docs(self):
        # Emergência: C ∧ (B ∨ D)
        assert verificar_controle_acesso(
            False, True, True, False, emergencia=True
        ) is True

    def test_emergencia_sem_medico(self):
        # Emergência sem médico → não atendido
        assert verificar_controle_acesso(
            True, True, False, True, emergencia=True
        ) is False

    def test_tabela_verdade_consulta_normal(self):
        tabela = tabela_verdade_consulta_normal()
        assert len(tabela) == 16  # 2^4 combinações

        # Verifica uma linha específica: A=1,B=1,C=1,D=0
        linha = next(
            r for r in tabela
            if r["A"] and r["B"] and r["C"] and not r["D"]
        )
        assert linha["Atendido"] is True

    def test_tabela_verdade_emergencia(self):
        tabela = tabela_verdade_emergencia()
        assert len(tabela) == 16

        # Emergência: C=1, B=0, D=1 → atendido
        linha = next(
            r for r in tabela
            if not r["B"] and r["C"] and r["D"]
        )
        assert linha["Atendido"] is True
