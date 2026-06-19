from datetime import date

from taskme.services.queries import _parse_period
from taskme.util import normalize_phone, summarize
from taskme import templates

TODAY = date(2026, 6, 19)


def test_parse_period():
    assert _parse_period("last_week", TODAY) == (date(2026, 6, 12), TODAY)
    assert _parse_period("last_month", TODAY) == (date(2026, 5, 20), TODAY)
    assert _parse_period("since:2026-01-01", TODAY) == (date(2026, 1, 1), TODAY)
    assert _parse_period("range:2026-01-01..2026-02-01", TODAY) == (date(2026, 1, 1), date(2026, 2, 1))
    assert _parse_period(None, TODAY) is None
    assert _parse_period("lixo", TODAY) is None


def test_normalize_phone():
    assert normalize_phone("+55 (62) 99311-9454") == "5562993119454"
    assert normalize_phone("") == ""


def test_summarize():
    assert summarize(None) is None
    assert summarize("  a   b ") == "a b"
    long = "x" * 400
    s = summarize(long, max_len=50)
    assert len(s) == 50 and s.endswith("…")


def test_task_message_imperativo_e_codigo():
    m = templates.task_message("João", "Leo", "TM-1001", "Enviar relatório", "rel", date(2026, 6, 20))
    assert "TM-1001" in m and "Enviar relatório" in m and "20/06/2026" in m
    assert "João" in m


def test_intro_na_primeira():
    m = templates.task_message("João", "Leo", "TM-1", "T", None, date(2026, 6, 20), intro=True)
    assert "assistente de tarefas de Leo" in m


def test_assigner_daily_buckets():
    msg = templates.assigner_daily(
        "Leo",
        [{"code": "TM-1", "title": "A", "assignee_name": "João", "original_due_date": date(2026, 6, 16), "atraso_dias": 2}],
        [{"code": "TM-2", "title": "B", "assignee_name": "Ana", "original_due_date": date(2026, 6, 10), "new_due_date": date(2026, 6, 25), "justificativa": "x"}],
        [],
    )
    assert "Concluídas" in msg and "Reprogramadas" in msg and "+2 dia" in msg
