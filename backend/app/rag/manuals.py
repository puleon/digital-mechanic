"""Реестр руководств: какие документы относятся к каким двигателям.

`manual_ref` — каноническое обозначение/название документа, оно уходит в заявку ТОиР
(поле `references.manual`) и в ответы агента.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Manual:
    doc_id: str
    file: str
    manual_ref: str
    title: str
    engines: tuple[str, ...]
    kind: str  # re = руководство по эксплуатации, rk = руководство по ремонту


MANUALS: tuple[Manual, ...] = (
    Manual(
        doc_id="yamz236_re",
        file="ЯМЗ_236_руководство по эксплуатации.pdf",
        manual_ref="236-3902150-Б РЭ",
        title="Руководство по эксплуатации двигателей ЯМЗ-236М2, ЯМЗ-238М2",
        engines=("ЯМЗ-236М2",),
        kind="re",
    ),
    Manual(
        doc_id="yamz236_rk",
        file="ЯМЗ_236_руководство по РЕМОНТУ.pdf",
        manual_ref="236.01.01 РК",
        title="Руководство по ремонту двигателей ЯМЗ-236М2, ЯМЗ-238М2",
        engines=("ЯМЗ-236М2",),
        kind="rk",
    ),
    Manual(
        doc_id="yamz536_re",
        file="yamz-536_re_2016.pdf",
        manual_ref="536.3902150 РЭ",
        title="Руководство по эксплуатации двигателей ЯМЗ-536, 5361, 5362, 5363, 5364",
        engines=("ЯМЗ-536",),
        kind="re",
    ),
    Manual(
        doc_id="yamz536_rk",
        file="yamz-536_rk_2013.pdf",
        manual_ref="536.01.02 РК",
        title="Руководство по ремонту двигателей ЯМЗ-536, 5361, 5363, 53602, 53622, 53642",
        engines=("ЯМЗ-536",),
        kind="rk",
    ),
    Manual(
        doc_id="zmz5234_rk",
        file="zmz-5234_rk_2025.pdf",
        manual_ref="Двигатели ЗМЗ-5234.10 со сцеплением. Руководство по ремонту",
        title="Двигатели ЗМЗ-5234.10 со сцеплением. Руководство по ремонту (5-е изд., 2025)",
        engines=("ЗМЗ-5234.10",),
        kind="rk",
    ),
    Manual(
        doc_id="zmz4090x_rk",
        file="zmz-40904-40905_rk_2025.pdf",
        manual_ref="Руководство по эксплуатации, ТО и ремонту двигателей ЗМЗ-40904.10 и ЗМЗ-40905.10",
        title="Руководство по эксплуатации, техническому обслуживанию и ремонту двигателей ЗМЗ-40904.10 и ЗМЗ-40905.10 (10-е изд., 2025)",
        engines=("ЗМЗ-40904.10", "ЗМЗ-40905.10"),
        kind="rk",
    ),
)

BY_ID = {m.doc_id: m for m in MANUALS}
