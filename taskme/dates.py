"""Resolução DETERMINÍSTICA de datas relativas em PT-BR.

O agente NUNCA calcula datas. Ele passa a frase crua ("sexta", "dia 20",
"em 3 dias") + o `now`; aqui resolvemos para um `date` com regras fixas.
O resultado é sempre mostrado ao usuário para aprovação, então preferimos
determinismo previsível a adivinhação.

`resolve_due(phrase, now) -> date | None`  (None = não interpretável → due_required)
"""
from __future__ import annotations

import re
import unicodedata
from calendar import monthrange
from datetime import date, datetime, timedelta

_WEEKDAYS = {
    "segunda": 0, "segunda-feira": 0, "seg": 0,
    "terca": 1, "terca-feira": 1, "ter": 1,
    "quarta": 2, "quarta-feira": 2, "qua": 2,
    "quinta": 3, "quinta-feira": 3, "qui": 3,
    "sexta": 4, "sexta-feira": 4, "sex": 4,
    "sabado": 5, "sab": 5,
    "domingo": 6, "dom": 6,
}

_MONTHS = {
    "janeiro": 1, "fevereiro": 2, "marco": 3, "abril": 4, "maio": 5,
    "junho": 6, "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10,
    "novembro": 11, "dezembro": 12,
}


def _strip(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    no_accent = "".join(c for c in nfkd if not unicodedata.combining(c))
    return no_accent.lower().strip()


def _clamp_day(year: int, month: int, day: int) -> date:
    last = monthrange(year, month)[1]
    return date(year, month, min(day, last))


def _add_months(d: date, months: int) -> date:
    m = d.month - 1 + months
    year = d.year + m // 12
    month = m % 12 + 1
    return _clamp_day(year, month, d.day)


def resolve_due(phrase: str, now: datetime) -> date | None:
    if not phrase or not phrase.strip():
        return None
    today = now.date()
    t = _strip(phrase)

    # 1) Datas explícitas: yyyy-mm-dd / yyyy/mm/dd
    m = re.search(r"\b(\d{4})[-/](\d{1,2})[-/](\d{1,2})\b", t)
    if m:
        y, mo, d = int(m[1]), int(m[2]), int(m[3])
        try:
            return date(y, mo, d)
        except ValueError:
            return None

    # 2) dd/mm[/yyyy] ou dd-mm[-yyyy]
    m = re.search(r"\b(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\b", t)
    if m:
        d, mo = int(m[1]), int(m[2])
        if m[3]:
            y = int(m[3])
            if y < 100:
                y += 2000
        else:
            y = today.year
        try:
            cand = date(y, mo, d)
        except ValueError:
            return None
        if not m[3] and cand < today:  # ano omisso e já passou → próximo ano
            try:
                cand = date(y + 1, mo, d)
            except ValueError:
                return None
        return cand

    # 3) Palavras-chave de dia relativo
    if re.search(r"\bhoje\b", t):
        return today
    if re.search(r"\bdepois de amanha\b", t):
        return today + timedelta(days=2)
    if re.search(r"\bamanha\b", t):
        return today + timedelta(days=1)

    # 4) "em N dias" / "daqui a N dias" / "daqui N dias"
    m = re.search(r"\b(?:em|daqui a|daqui|apos|depois de)\s+(\d{1,3})\s+dias?\b", t)
    if m:
        return today + timedelta(days=int(m[1]))

    # 5) "N de <mês>" ou "dia N de <mês>"
    m = re.search(r"\b(?:dia\s+)?(\d{1,2})\s+de\s+([a-z]+)\b", t)
    if m and _strip(m[2]) in _MONTHS:
        d, mo = int(m[1]), _MONTHS[_strip(m[2])]
        cand = _clamp_day(today.year, mo, d)
        if cand < today:
            cand = _clamp_day(today.year + 1, mo, d)
        return cand

    # 6) "fim do mes" / "final do mes"
    if re.search(r"\b(fim|final)\s+(do|de)\s+mes\b", t):
        last = monthrange(today.year, today.month)[1]
        return date(today.year, today.month, last)

    # 7) "semana que vem" / "proxima semana" → próxima segunda
    if re.search(r"\b(semana que vem|proxima semana|semana proxima)\b", t):
        days = (0 - today.weekday()) % 7
        days = days or 7
        return today + timedelta(days=days)

    # 8) "mes que vem" / "proximo mes" → mesmo dia, mês seguinte
    if re.search(r"\b(mes que vem|proximo mes|mes proximo)\b", t):
        return _add_months(today, 1)

    # 9) Dia da semana (com possível "proxima")
    proximo = bool(re.search(r"\bproxim", t))
    for name, wd in _WEEKDAYS.items():
        if re.search(rf"\b{name}\b", t):
            delta = (wd - today.weekday()) % 7
            cand = today + timedelta(days=delta)
            if proximo and cand == today:
                cand = cand + timedelta(days=7)
            return cand

    # 10) "dia N" (sem mês) → dia N deste mês, ou do próximo se já passou
    m = re.search(r"\bdia\s+(\d{1,2})\b", t)
    if m:
        d = int(m[1])
        cand = _clamp_day(today.year, today.month, d)
        if cand < today:
            cand = _add_months(date(today.year, today.month, 1), 1)
            cand = _clamp_day(cand.year, cand.month, d)
        return cand

    return None
