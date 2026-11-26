"""Агент «Цифровой механик»: цикл tool calling поверх OpenAI-совместимого API.

Агент сам выбирает инструмент по контексту (F5). Сценарий не зашит в if-else:
единственное, что фиксировано, — набор инструментов и правила безопасности.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
    RateLimitError,
)

from . import clients, store
from .config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
from .rag import tools as rag

log = logging.getLogger(__name__)

MAX_STEPS = 8

SYSTEM_PROMPT = """Ты — «Цифровой механик», AI-агент диагностики двигателей внутреннего сгорания
для механика автопарка. Твоя задача — превратить результат акустической проверки в понятное
решение и помочь оформить дефектовку.

ТЕКУЩИЙ КОНТЕКСТ
{context}

ПРАВИЛА
1. Отвечай по-русски, кратко и по делу. Механик должен понять вердикт за 10 секунд:
   сначала главное, потом детали.
2. Состояние двигателя (статус, тип отклонения, уверенность, качество записи) бери ТОЛЬКО
   из результата инструмента get_diagnosis. Не придумывай этих значений.
3. Любые нормативы, допуски, моменты затяжки, зазоры и порядок работ бери ТОЛЬКО из
   search_manuals. В каждом техническом утверждении указывай документ и страницу PDF,
   например: «236.01.01 РК, стр. 41». Не ссылайся на страницу, которой нет в результатах поиска.
4. Если в найденных фрагментах нет ответа — прямо скажи: «В базе знаний нет данных по этому
   вопросу» и предложи дефектовку. Запрещено подставлять нормативы от другого двигателя.
5. Если status = check_failed: не делай никаких выводов о двигателе. Скажи, что запись
   непригодна (укажи причину из description), и попроси повторить запись.
6. Если status = normal: значимых отклонений нет, эксплуатация допустима. Заявку в этом
   случае не создавай.
7. Заявку в ТОиР создавай ТОЛЬКО при явной просьбе — слова «оформи заявку», «создай
   заявку», «передай в ТОиР», «нужна дефектовка». Вопрос о нормативе, «что проверить»,
   «почему это опасно», просьба объяснить — это НЕ просьба о заявке: отвечай текстом,
   ничего не создавай. Если непонятно, нужна ли заявка, — спроси одной фразой.
   Сама заявка возможна только при status = anomaly. Перед вызовом create_ticket собери
   работы, запчасти и ссылки на руководство через search_manuals. В references — только
   документы руководств этого двигателя и только страницы из выдачи поиска.
8. На вопросы вне базы знаний (стоимость, сроки, юридические последствия) честно отвечай,
   что данных нет.
9. Не вызывай инструменты без необходимости. На приветствие или уточняющий вопрос
   отвечай текстом.
10. Не показывай механику сырой JSON, если он не просил.

ФОРМАТ ОТВЕТА ПРИ ОТКЛОНЕНИИ
Наблюдения → Вероятные причины → Что проверить → Возможный ремонт → Источник → Ограничения.
В конце — что сделать прямо сейчас, одним действием.
"""

TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_diagnosis",
            "description": (
                "Получить результат акустической проверки выбранного ТС и проверки из ML-сервиса. "
                "Вызывай, когда механик просит результат диагностики, статус двигателя или когда "
                "для ответа нужны данные текущей проверки."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_manuals",
            "description": (
                "Найти в руководствах по двигателю ЭТОГО ТС процедуры, нормативы, допуски, "
                "моменты затяжки, порядок проверки и ремонта. Возвращает фрагменты с названием "
                "документа и номером страницы PDF. Всегда используй перед техническими советами."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Поисковый запрос на русском, техническими терминами",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_vehicle_history",
            "description": (
                "История проверок и созданных заявок по текущему ТС. Вызывай, когда механик "
                "спрашивает про динамику, прошлые проверки или ранее созданные заявки."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_fleet_overview",
            "description": (
                "Сводка по парку: сколько ТС в норме, требуют внимания, в карантине, и "
                "приоритетный список. Вызывай на вопросы главного механика о состоянии парка."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_ticket",
            "description": (
                "Создать заявку на дефектовку в системе ТОиР. Только по явной просьбе механика "
                "и только при status = anomaly. Нужны работы, запчасти и ссылки на руководство."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "anomaly_type": {"type": "string", "description": "Код из результата диагностики, например F08"},
                    "conclusion": {"type": "string", "description": "Диагноз для заявки, одна-две фразы"},
                    "urgency": {"type": "string", "enum": ["low", "medium", "high"]},
                    "operations": {
                        "type": "array", "items": {"type": "string"},
                        "description": "Работы по дефектовке, непустой список",
                    },
                    "spare_parts": {
                        "type": "array", "items": {"type": "string"},
                        "description": "Запчасти; может быть пустым списком",
                    },
                    "references": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "manual": {"type": "string", "description": "Обозначение или название документа"},
                                "pdf_page": {"type": "integer", "minimum": 1},
                            },
                            "required": ["manual", "pdf_page"],
                        },
                        "description": "Источники из руководства, непустой список",
                    },
                },
                "required": [
                    "anomaly_type", "conclusion", "urgency",
                    "operations", "spare_parts", "references",
                ],
            },
        },
    },
]


class ToolError(RuntimeError):
    pass


# Просьба о заявке — проверяется на сервере, чтобы модель не создавала её «на всякий случай»
TICKET_INTENT = re.compile(r"заявк|дефектов|тоир|оформ|созда", re.I)


def _asks_for_ticket(message: str) -> bool:
    return bool(TICKET_INTENT.search(message or ""))


class AgentContext:
    def __init__(self, vehicle: dict, session_id: str, user_message: str = ""):
        self.vehicle = vehicle
        self.session_id = session_id
        self.user_message = user_message
        self.engine_model: str = vehicle["engine_model"]
        self.vehicle_id: str = vehicle["vehicle_id"]
        # Страницы, реально показанные агенту поиском в рамках этого запроса.
        # Заявка может ссылаться только на них — защита от выдуманных ссылок.
        self.seen_pages: set[tuple[str, int]] = set()

    def describe(self) -> str:
        v = self.vehicle
        model = f" {v['model']}" if v.get("model") else ""
        return (
            f"ТС: {v['vehicle_id']} (гаражный {v['garage_no']}), "
            f"{v['make']}{model}, двигатель {v['engine_model']}, топливо {v['fuel']}. "
            f"Выбранная проверка: {self.session_id}."
        )


async def _exec(name: str, args: dict, ctx: AgentContext) -> dict:
    if name == "get_diagnosis":
        result = await clients.diagnose(ctx.vehicle_id, ctx.session_id)
        return {"diagnosis": result, "engine_model": ctx.engine_model}

    if name == "search_manuals":
        query = (args.get("query") or "").strip()
        if not query:
            raise ToolError("Пустой поисковый запрос")
        hits = rag.search(query, ctx.engine_model, top_k=6)
        if not hits:
            return {"results": [], "note": f"В руководствах для {ctx.engine_model} ничего не найдено"}
        ctx.seen_pages.update((hit["manual"], hit["pdf_page"]) for hit in hits)
        return {
            "engine_model": ctx.engine_model,
            "results": hits,
            "note": "Ссылайся только на эти документы и страницы",
        }

    if name == "get_vehicle_history":
        return {
            "vehicle_id": ctx.vehicle_id,
            "sessions": store.get_sessions(ctx.vehicle_id),
            "tickets": store.list_tickets(ctx.vehicle_id),
        }

    if name == "get_fleet_overview":
        return store.fleet_overview()

    if name == "create_ticket":
        return await _create_ticket(args, ctx)

    raise ToolError(f"Неизвестный инструмент: {name}")


async def _create_ticket(args: dict, ctx: AgentContext) -> dict:
    if not _asks_for_ticket(ctx.user_message):
        raise ToolError(
            "Механик не просил оформлять заявку. Ответь на вопрос текстом; создавай "
            "заявку только по прямой просьбе («оформи заявку», «передай в ТОиР»)."
        )
    diag = store.get_session(ctx.vehicle_id, ctx.session_id)
    if not diag:
        raise ToolError("Нет данных проверки для этой заявки")
    if diag["status"] != "anomaly":
        raise ToolError(
            f"Заявка создаётся только при отклонении. Статус проверки: {diag['status']}"
        )
    anomaly_type = args.get("anomaly_type")
    if anomaly_type != diag["anomaly_type"]:
        raise ToolError(
            f"anomaly_type не совпадает с результатом проверки ({diag['anomaly_type']})"
        )

    operations = [x for x in (args.get("operations") or []) if str(x).strip()]
    spare_parts = [str(x) for x in (args.get("spare_parts") or [])]
    references = args.get("references") or []
    if not str(args.get("conclusion") or "").strip():
        raise ToolError("conclusion не может быть пустым")
    if not operations:
        raise ToolError("operations не может быть пустым")
    if not references:
        raise ToolError("references не может быть пустым")

    allowed = rag.allowed_manuals(ctx.engine_model)
    clean_refs = []
    for ref in references:
        manual = str(ref.get("manual", "")).strip()
        page = int(ref.get("pdf_page") or 0)
        if manual not in allowed:
            raise ToolError(
                f"Документ «{manual}» не относится к двигателю {ctx.engine_model}. "
                f"Доступны: {', '.join(sorted(allowed))}"
            )
        pages = rag.manual_page_count(manual)
        if page < 1 or (pages and page > pages):
            raise ToolError(f"Страницы {page} нет в документе «{manual}»")
        if (manual, page) not in ctx.seen_pages:
            raise ToolError(
                f"Страница {page} документа «{manual}» не встречалась в результатах поиска "
                "в этом запросе. Сначала найди её через search_manuals и ссылайся только "
                "на страницы из выдачи."
            )
        clean_refs.append({"manual": manual, "pdf_page": page})

    payload = {
        "vehicle_id": ctx.vehicle_id,
        "session_id": ctx.session_id,
        "anomaly_type": anomaly_type,
        "conclusion": str(args["conclusion"]).strip(),
        "urgency": args.get("urgency", "medium"),
        "operations": operations,
        "spare_parts": spare_parts,
        "references": clean_refs,
    }
    if payload["urgency"] not in {"low", "medium", "high"}:
        raise ToolError("urgency должен быть low, medium или high")

    created = await clients.create_ticket(payload)
    store.save_ticket(created["ticket_id"], payload)
    return {"ticket_id": created["ticket_id"], "status": created.get("status"), "payload": payload}


def _client() -> AsyncOpenAI:
    return AsyncOpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL, timeout=90)


async def _chat(client: AsyncOpenAI, **kwargs):
    """Запрос к LLM с повторами на временных сбоях (лимиты, 5xx, сеть)."""
    delay = 1.5
    for attempt in range(3):
        try:
            return await client.chat.completions.create(**kwargs)
        except (RateLimitError, APITimeoutError, APIConnectionError) as exc:
            if attempt == 2:
                raise
            log.warning("LLM временно недоступна (%s), повтор через %.1f с", type(exc).__name__, delay)
        except APIStatusError as exc:
            if exc.status_code < 500 or attempt == 2:
                raise
            log.warning("LLM вернула %s, повтор через %.1f с", exc.status_code, delay)
        await asyncio.sleep(delay)
        delay *= 2


async def run_agent(
    vehicle: dict,
    session_id: str,
    message: str,
    conversation_id: str,
    model: str | None = None,
) -> dict:
    ctx = AgentContext(vehicle, session_id, user_message=message)
    store.add_message(conversation_id, vehicle["vehicle_id"], "user", message)

    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT.format(context=ctx.describe())},
        *store.get_messages(conversation_id, limit=10),
    ]

    trace: list[dict] = []
    client = _client()
    content = ""
    for _ in range(MAX_STEPS):
        response = await _chat(
            client,
            model=model or LLM_MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.1,
        )
        msg = response.choices[0].message
        if not msg.tool_calls:
            content = msg.content or ""
            break

        messages.append({
            "role": "assistant",
            "content": msg.content,
            "tool_calls": [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in msg.tool_calls
            ],
        })
        for tc in msg.tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            try:
                result = await _exec(name, args, ctx)
                is_error = False
            except (ToolError, clients.ServiceError) as exc:
                result = {"error": str(exc)}
                is_error = True
            trace.append({"tool": name, "arguments": args, "result": result, "error": is_error})
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result, ensure_ascii=False),
            })
    else:
        content = content or "Не удалось завершить обработку запроса. Попробуйте переформулировать."

    store.add_message(conversation_id, vehicle["vehicle_id"], "assistant", content)
    return {
        "reply": content,
        "tool_calls": trace,
        "vehicle_id": vehicle["vehicle_id"],
        "session_id": session_id,
    }
