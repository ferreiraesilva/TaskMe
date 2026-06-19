from datetime import date, datetime

import pytest

from taskme.dates import resolve_due

# Quarta-feira de referência.
NOW = datetime(2026, 6, 17, 10, 0, 0)


def r(phrase):
    return resolve_due(phrase, NOW)


def test_hoje():
    assert r("hoje") == date(2026, 6, 17)


@pytest.mark.parametrize("phrase", ["amanha", "amanhã", "entregar amanhã"])
def test_amanha(phrase):
    assert r(phrase) == date(2026, 6, 18)


def test_depois_de_amanha():
    assert r("depois de amanhã") == date(2026, 6, 19)


@pytest.mark.parametrize("phrase,delta", [("em 3 dias", 3), ("daqui a 10 dias", 10), ("daqui 5 dias", 5)])
def test_em_n_dias(phrase, delta):
    assert r(phrase) == date(2026, 6, 17) + __import__("datetime").timedelta(days=delta)


@pytest.mark.parametrize("phrase,expected", [
    ("25/12/2026", date(2026, 12, 25)),
    ("20/06/2026", date(2026, 6, 20)),
    ("2026-07-01", date(2026, 7, 1)),
])
def test_explicitas(phrase, expected):
    assert r(phrase) == expected


def test_dd_mm_ano_omisso_passado_vai_proximo_ano():
    # 05/01 sem ano, já passou em 17/06 → próximo ano.
    assert r("05/01") == date(2027, 1, 5)


def test_dia_n_mes_atual():
    assert r("dia 20") == date(2026, 6, 20)


def test_dia_n_passado_vai_proximo_mes():
    assert r("dia 10") == date(2026, 7, 10)


def test_n_de_mes():
    assert r("25 de dezembro") == date(2026, 12, 25)
    assert r("dia 1 de julho") == date(2026, 7, 1)


def test_fim_do_mes():
    assert r("fim do mês") == date(2026, 6, 30)


def test_semana_que_vem_eh_segunda():
    d = r("semana que vem")
    assert d.weekday() == 0 and 1 <= (d - date(2026, 6, 17)).days <= 7


@pytest.mark.parametrize("phrase,wd", [
    ("sexta", 4), ("sexta-feira", 4), ("segunda", 0), ("terça", 1), ("domingo", 6),
])
def test_dia_da_semana(phrase, wd):
    d = r(phrase)
    assert d.weekday() == wd
    assert 0 <= (d - date(2026, 6, 17)).days <= 6


def test_proxima_semana_dia_da_semana_empurra():
    # 17/06/2026 é quarta (wd=2). "quarta" = hoje; "próxima quarta" = +7.
    hoje = r("quarta")
    prox = r("próxima quarta")
    assert hoje == date(2026, 6, 17)
    assert prox == date(2026, 6, 24)


@pytest.mark.parametrize("phrase", ["", "   ", "qualquer coisa sem data", "talvez"])
def test_nao_interpretavel(phrase):
    assert r(phrase) is None
