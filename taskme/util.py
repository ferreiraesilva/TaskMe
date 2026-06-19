"""Utilidades pequenas e puras."""
from __future__ import annotations


def normalize_phone(phone: str) -> str:
    """Mantém só dígitos (formato de armazenamento/comparação)."""
    return "".join(ch for ch in (phone or "") if ch.isdigit())


def summarize(text: str | None, max_len: int = 280) -> str | None:
    """Garante tamanho máximo. A sumarização semântica é feita pelo agente;
    aqui só limitamos o tamanho do que vai pro histórico."""
    if text is None:
        return None
    t = " ".join(text.split())
    if len(t) <= max_len:
        return t
    return t[: max_len - 1].rstrip() + "…"
