import pandas as pd
import json
from openai import OpenAI
import os
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
XLSX_PATH = BASE_DIR / "datasets" / "Для_тестов_ЛЛМ1__3__Асель__1_.xlsx"

API_KEY = "sk-QwR2Iapnq6ph70c6jM9rpfQsxdzGMhZG"

client = OpenAI(
    api_key=API_KEY,
    base_url="https://api.proxyapi.ru/openai/v1",
)

# =============================================================================
# СИСТЕМНЫЕ ПРОМТЫ
# =============================================================================
SYSTEM_TYPE = """Ты — опытный врач с большим опытом диагностики болезней.
Тебе показывают двух наблюдения у ОДНОГО и того же пациента.
Твоя задача — решить, как эти два наблюдения связаны между собой.

ТИПЫ СВЯЗИ — выбери один:

ПОЛОЖИТЕЛЬНАЯ — оба наблюдения могут быть у пациента одновременно.
  Врач просто записывает оба, не выбирает между ними.
  Пример: у пациента есть кашель И температура — оба наблюдения сосуществуют.

ОТРИЦАТЕЛЬНАЯ — одно наблюдение мешает другому быть главной причиной.
  Если первое подтвердилось — второе скорее всего не является причиной болезни.
  Пример: анализ показал вирус гриппа. Тогда туберкулёз как причина — маловероятен.
  Врач выбирает одно из двух как объяснение состояния пациента.

НЕСОВМЕСТНЫ — оба наблюдения физически не могут быть у пациента одновременно.
НЕ СВЯЗАНЫ — между наблюдениями вообще нет никакой связи.

КАК ОТЛИЧИТЬ ПОЛОЖИТЕЛЬНАЯ от ОТРИЦАТЕЛЬНАЯ:

Задай себе простой вопрос:
"Если первое наблюдение — это ответ на вопрос ПОЧЕМУ пациенту плохо,
то второе наблюдение — это ДРУГОЙ ответ на тот же вопрос?"

Если да — врач должен выбрать один ответ, второй становится лишним → ОТРИЦАТЕЛЬНАЯ.
Если нет — оба наблюдения просто существуют рядом → ПОЛОЖИТЕЛЬНАЯ.

ПРИМЕРЫ:

ОТРИЦАТЕЛЬНАЯ:
- Бактериальная пневмония + Обнаружены туберкулёзные бактерии в мокроте
  → Это два разных объяснения болезни лёгких. Врач выбирает одно.
- КТ показывает COVID-19 + Туберкулёз
  → Два разных диагноза для одного лёгочного процесса. Врач выбирает.
- Вирусная пневмония + Положительный тест на туберкулёз (Диаскинтест)
  → Вирус и туберкулёз — разные причины. Врач выбирает одну.

ПОЛОЖИТЕЛЬНАЯ:
- Кашель с ржавой мокротой + Кровь при кашле
  → Одно вытекает из другого, не конкурируют.
- Воздушные ловушки на снимке + Признаки гриппозной пневмонии
  → Разные находки, мирно сосуществуют у одного пациента.

ВАЖНО: если одно наблюдение является видом, подвидом или частным случаем 
другого — это всегда ПОЛОЖИТЕЛЬНАЯ, даже если оба про одну болезнь.
Пример: штампованная полость — это вид деструктивной полости.
Одно включает другое → ПОЛОЖИТЕЛЬНАЯ, не ОТРИЦАТЕЛЬНАЯ.

РАССУЖДАЙ ТАК — шаг за шагом:
1. Что говорит Наблюдение 1 — на какую причину болезни оно указывает?
2. Что говорит Наблюдение 2 — на какую причину болезни оно указывает?
3. Это разные причины одной и той же болезни? Врач должен выбрать одну?
   Если да → ОТРИЦАТЕЛЬНАЯ.
4. Или они просто оба есть у пациента, и врач спокойно записывает оба?
   Если да → ПОЛОЖИТЕЛЬНАЯ.
5. Назови тип связи.

Не используй кавычки внутри поля reasoning.

Отвечай СТРОГО в формате JSON:
{"reasoning": "пошаговое рассуждение", "link_type": "ПОЛОЖИТЕЛЬНАЯ"}

Только JSON, без лишнего текста.
"""

SYSTEM_REFINE_POS = """Ты — опытный врач и клинический диагност.
Между двумя признаками у ОДНОГО пациента установлена ПОЛОЖИТЕЛЬНАЯ связь.
Уточни степень этой связи.

ВСЕГДА НАБЛЮДАЕТСЯ — при наблюдении События A у пациента Событие B
присутствует без исключений.
Выбирай если выполняется хотя бы одно из:
- Событие B является частью определения или обязательным следствием События A
- Событие A является разновидностью, подвидом или частным случаем Событие B
  (частный случай всегда входит в общую категорию → ВСЕГДА по определению)
- Без Событие B невозможно поставить диагноз Событие A

Примеры ВСЕГДА НАБЛЮДАЕТСЯ:
- Ржавая мокрота → Кровь при кашле = ВСЕГДА
  (ржавая мокрота по определению содержит примесь крови, исключений нет)
- Штампованные полости → Деструктивная полость туберкулёза = ВСЕГДА
  (штампованная полость — частный вид деструктивной полости туберкулёза,
  частный случай всегда входит в общую категорию)

МОЖЕТ НАБЛЮДАТЬСЯ — Событие B часто сопутствует но не является обязательным.
Бывают случаи когда Событие A есть а Событие B нет.

ВАЖНО: вопрос не в том могут ли быть другие причины События A.
Вопрос только: если Событие A уже наблюдается у пациента —
всегда ли при этом есть Событие B?

Рассуждай пошагово:
1. Является ли Событие A частным случаем или подвидом Событие B?
2. Является ли Событие B частью определения или обязательным следствием События A?
3. Является ли Событие B условием существования События A?
4. Бывают ли случаи когда Событие A есть а Событие B нет? 
5. Содержит ли Событие A явное ограничение на пол, возраст или другую группу пациентов?
   Если да — принадлежность к этой группе обязательна.
6. Выбери вариант.

ВАЖНО: в поле reasoning не используй кавычки внутри текста.
Вместо написания слова в кавычках просто пиши его без кавычек.

Отвечай СТРОГО в формате JSON:
{"reasoning": "пошаговое рассуждение", "refinement": "ВСЕГДА НАБЛЮДАЕТСЯ"}

Только JSON, без лишнего текста.
"""

SYSTEM_REFINE_NEG = """Ты — опытный врач и клинический диагност.
Между двумя признаками у ОДНОГО пациента установлена ОТРИЦАТЕЛЬНАЯ связь.
Уточни степень этой связи.

ОПРЕДЕЛЕНИЯ:

ВСЕГДА ОТСУТСТВУЕТ — при наблюдении События A Событие B отсутствует без исключений.
Выбирай только если исключений не существует.
Пример: "Бактериальная пневмония" → "Наличие МБТ" = ВСЕГДА ОТСУТСТВУЕТ
(разные этиологии, одна полностью исключает другую)

МОЖЕТ ОТСУТСТВОВАТЬ — Событие B обычно отсутствует, но редкие исключения клинически возможны.
Например сочетанная патология — рак лёгких и инфекция у одного пациента теоретически бывает.

КРИТИЧЕСКИ ВАЖНО:
Если в своём рассуждении ты написал хотя бы одно из:
"исключения возможны", "теоретически возможно", "крайне редко но бывает",
"сочетанная патология допустима", "не исключено" —
это ОДНОЗНАЧНО МОЖЕТ ОТСУТСТВОВАТЬ, никогда не ВСЕГДА ОТСУТСТВУЕТ.

ВСЕГДА ОТСУТСТВУЕТ только если ты уверен что исключений не существует в принципе.

Рассуждай пошагово:
1. Полностью ли Событие A исключает Событие B по определению?
2. Возможна ли сочетанная патология хотя бы теоретически?
3. Есть ли хоть одно исключение из правила?
4. Если есть хоть одно исключение — выбирай МОЖЕТ ОТСУТСТВОВАТЬ.

ВАЖНО: в поле reasoning не используй кавычки внутри текста.
Вместо написания слова в кавычках просто пиши его без кавычек.

Отвечай СТРОГО в формате JSON:
{"reasoning": "пошаговое рассуждение", "refinement": "ВСЕГДА ОТСУТСТВУЕТ"}

Только JSON, без лишнего текста.
"""
# =============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =============================================================================

def ask_llm(system_prompt: str, user_prompt: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.1,
    )
    return response.choices[0].message.content.strip()


def parse_json_response(raw: str, key: str, valid_values: list):
    try:
        clean = raw.strip()
        if clean.startswith("```"):
            parts = clean.split("```")
            for part in parts:
                if part.startswith("json"):
                    clean = part[4:].strip()
                    break
                elif "{" in part:
                    clean = part.strip()
                    break
        data = json.loads(clean)
        reasoning = data.get("reasoning", "")
        value = data.get(key, "").strip().upper()
        if value in valid_values:
            return value, reasoning
        for v in valid_values:
            if v in raw.upper():
                return v, reasoning
        return valid_values[-1], reasoning
    except Exception as e:
        print(f"  [WARN] Не удалось распарсить JSON: {e}\n  Ответ: {raw}")
        reasoning = ""
        upper = raw.upper()
        for v in valid_values:
            if v in upper:
                return v, reasoning
        return valid_values[-1], reasoning


VALID_LINK_TYPES = ["ПОЛОЖИТЕЛЬНАЯ", "ОТРИЦАТЕЛЬНАЯ", "НЕСОВМЕСТНЫ", "НЕ СВЯЗАНЫ"]
VALID_REFINE_POS = ["ВСЕГДА НАБЛЮДАЕТСЯ", "МОЖЕТ НАБЛЮДАТЬСЯ", "НЕТ ИНФОРМАЦИИ"]
VALID_REFINE_NEG = ["ВСЕГДА ОТСУТСТВУЕТ", "МОЖЕТ ОТСУТСТВОВАТЬ", "НЕТ ИНФОРМАЦИИ"]


def get_expected_answers(label: str):
    mapping = {
        "всегда наблюдается":  ("ПОЛОЖИТЕЛЬНАЯ", "ВСЕГДА НАБЛЮДАЕТСЯ"),
        "может наблюдаться":   ("ПОЛОЖИТЕЛЬНАЯ", "МОЖЕТ НАБЛЮДАТЬСЯ"),
        "всегда отсутствует":  ("ОТРИЦАТЕЛЬНАЯ", "ВСЕГДА ОТСУТСТВУЕТ"),
        "может отсутствовать": ("ОТРИЦАТЕЛЬНАЯ", "МОЖЕТ ОТСУТСТВОВАТЬ"),
    }
    return mapping.get(label, (None, None))


def get_link_type(event1: str, event2: str):
    user_prompt = (
        f"Пациент. Оцени связь между двумя клиническими наблюдениями у одного пациента:\n\n"
        f"Событие 1: «{event1}»\n"
        f"Событие 2: «{event2}»\n\n"
        f"Определи тип связи."
    )
    raw = ask_llm(SYSTEM_TYPE, user_prompt)
    print(f"  [LLM шаг 1 - тип связи]: {raw}")
    value, reasoning = parse_json_response(raw, "link_type", VALID_LINK_TYPES)
    return value, reasoning


def get_refinement(event_a: str, event_b: str, link_type: str):
    if link_type == "ПОЛОЖИТЕЛЬНАЯ":
        system = SYSTEM_REFINE_POS
        valid = VALID_REFINE_POS
    else:
        system = SYSTEM_REFINE_NEG
        valid = VALID_REFINE_NEG

    user_prompt = (
        f"Пациент. Уточни степень связи:\n\n"
        f"Событие A (наблюдается у пациента): «{event_a}»\n"
        f"Событие B: «{event_b}»\n\n"
        f"Что можно сказать о Событии B, когда у пациента наблюдается Событие A?"
    )
    raw = ask_llm(system, user_prompt)
    print(f"  [LLM шаг 2 - уточнение]: {raw}")
    value, reasoning = parse_json_response(raw, "refinement", valid)
    return value, reasoning


# =============================================================================
# ОСНОВНОЙ АЛГОРИТМ
# =============================================================================

def establish_link(event1: str, event2: str, max_retries: int = 3) -> dict:
    result = {
        "event1": event1,
        "event2": event2,
        "link_type": None,
        "type_reasoning": None,
        "direction_1_to_2": None,
        "refine_reasoning_1_to_2": None,
        "direction_2_to_1": None,
        "refine_reasoning_2_to_1": None,
    }

    print(f"\n{'='*60}")
    print(f"Событие 1: «{event1}»")
    print(f"Событие 2: «{event2}»")

    link_type, type_reasoning = get_link_type(event1, event2)
    result["link_type"] = link_type
    result["type_reasoning"] = type_reasoning
    print(f"  Тип связи: {link_type}")

    if link_type in ("НЕ СВЯЗАНЫ", "НЕСОВМЕСТНЫ"):
        result["direction_1_to_2"] = "НЕПРИМЕНИМО"
        result["direction_2_to_1"] = "НЕПРИМЕНИМО"
        print(f"  Симметричная связь: {link_type} в обе стороны")
        return result

    # Прямое направление
    print(f"\n  [Прямое: {event1} -> {event2}]")
    current_type = link_type
    for attempt in range(max_retries):
        ref, ref_reasoning = get_refinement(event1, event2, current_type)
        if ref != "НЕТ ИНФОРМАЦИИ":
            result["direction_1_to_2"] = ref
            result["refine_reasoning_1_to_2"] = ref_reasoning
            break
        print(f"  НЕТ ИНФОРМАЦИИ — повторный запрос типа (попытка {attempt+1})")
        current_type, _ = get_link_type(event1, event2)
        if current_type in ("НЕ СВЯЗАНЫ", "НЕСОВМЕСТНЫ"):
            result["direction_1_to_2"] = "НЕПРИМЕНИМО"
            break
    else:
        result["direction_1_to_2"] = "НЕИЗВЕСТНО"

    result["link_type"] = current_type

    # Обратное направление
    print(f"\n  [Обратное: {event2} -> {event1}]")
    current_type_rev = link_type
    for attempt in range(max_retries):
        ref2, ref_reasoning2 = get_refinement(event2, event1, current_type_rev)
        if ref2 != "НЕТ ИНФОРМАЦИИ":
            result["direction_2_to_1"] = ref2
            result["refine_reasoning_2_to_1"] = ref_reasoning2
            break
        print(f"  НЕТ ИНФОРМАЦИИ — повторный запрос типа (попытка {attempt+1})")
        current_type_rev, _ = get_link_type(event2, event1)
        if current_type_rev in ("НЕ СВЯЗАНЫ", "НЕСОВМЕСТНЫ"):
            result["direction_2_to_1"] = "НЕПРИМЕНИМО"
            break
    else:
        result["direction_2_to_1"] = "НЕИЗВЕСТНО"

    return result


# =============================================================================
# РАБОТА С ДАТАСЕТОМ
# =============================================================================

def load_and_split_dataset(path: str):
    df = pd.read_excel(path)

    datasets = {
        "всегда наблюдается":  [],
        "может наблюдаться":   [],
        "всегда отсутствует":  [],
        "может отсутствовать": [],
    }

    for _, row in df.iterrows():
        e1 = str(row["Событие 1"]).strip()
        e2 = str(row["Событие 2"]).strip()
        label = str(row["Взаимосвязь"]).strip().lower()
        reverse_raw = str(row.get("Обратная связь", "")).strip().lower()
        reverse_label = reverse_raw if reverse_raw not in ("nan", "") else None

        pair = {
            "event1": e1,
            "event2": e2,
            "label": label,
            "reverse_label": reverse_label,
        }

        if label in datasets:
            datasets[label].append(pair)

    print("Размер датасетов по категориям:")
    for cat, items in datasets.items():
        print(f"  {cat}: {len(items)}")

    return datasets

all_pairs = []

def test_dataset(dataset: list, category_name: str):
    print(f"\n{'='*60}")
    print(f"ТЕСТИРУЕМ: {category_name} ({len(dataset)} пар)")
    print('='*60)

    # счётчики для прямого направления
    step1_correct = 0
    step1_wrong = 0
    step2_correct = 0
    step2_wrong = 0
    step2_skipped = 0

    # счётчики для обратного направления
    rev_step1_correct = 0
    rev_step1_wrong = 0
    rev_step2_correct = 0
    rev_step2_wrong = 0
    rev_step2_skipped = 0
    rev_skipped_no_label = 0

    errors = 0

    for i, row in enumerate(dataset, 1):
        e1 = row["event1"]
        e2 = row["event2"]
        label = row["label"]
        reverse_label = row["reverse_label"]

        expected_type, expected_refine = get_expected_answers(label)

        print(f"\n[{i}/{len(dataset)}] {e1} -> {e2}")
        print(f"  Ожидается: тип={expected_type}, уточнение={expected_refine}")

        try:
            result = establish_link(e1, e2)

            predicted_type = result["link_type"]
            predicted_refine = result["direction_1_to_2"]

            # --- Оценка шага 1 (прямое) ---
            if predicted_type == expected_type:
                step1_correct += 1
                print(f"  Шаг 1 ✓ тип: {predicted_type}")
            else:
                step1_wrong += 1
                print(f"  Шаг 1 ✗ тип: ожидалось={expected_type}, получено={predicted_type}")

            # --- Оценка шага 2 (прямое) ---
            if predicted_type == expected_type:
                if predicted_refine == expected_refine:
                    step2_correct += 1
                    print(f"  Шаг 2 ✓ уточнение: {predicted_refine}")
                else:
                    step2_wrong += 1
                    print(f"  Шаг 2 ✗ уточнение: ожидалось={expected_refine}, получено={predicted_refine}")
            else:
                step2_skipped += 1
                print(f"  Шаг 2 — пропущен (шаг 1 неверный)")

            # --- Обратное направление ---
            if reverse_label is not None and reverse_label in {
                "всегда наблюдается", "может наблюдаться",
                "всегда отсутствует", "может отсутствовать"
            }:
                rev_expected_type, rev_expected_refine = get_expected_answers(reverse_label)
                print(f"\n  [Обратное: {e2} -> {e1}]")
                print(f"  Ожидается: тип={rev_expected_type}, уточнение={rev_expected_refine}")

                rev_predicted_type = result["link_type"]  # тип симметричен
                rev_predicted_refine = result["direction_2_to_1"]

                if rev_predicted_type == rev_expected_type:
                    rev_step1_correct += 1
                    print(f"  Шаг 1 ✓ тип: {rev_predicted_type}")
                else:
                    rev_step1_wrong += 1
                    print(f"  Шаг 1 ✗ тип: ожидалось={rev_expected_type}, получено={rev_predicted_type}")

                if rev_predicted_type == rev_expected_type:
                    if rev_predicted_refine == rev_expected_refine:
                        rev_step2_correct += 1
                        print(f"  Шаг 2 ✓ уточнение: {rev_predicted_refine}")
                    else:
                        rev_step2_wrong += 1
                        print(f"  Шаг 2 ✗ уточнение: ожидалось={rev_expected_refine}, получено={rev_predicted_refine}")
                else:
                    rev_step2_skipped += 1
                    print(f"  Шаг 2 — пропущен (шаг 1 неверный)")
            else:
                rev_skipped_no_label += 1
                print(f"\n  [Обратное: пропущено — нет метки в датасете]")

            all_pairs.append({
                "event1": e1,
                "event2": e2,
                "expected_type": expected_type,
                "expected_refine": expected_refine,
                "predicted_type": predicted_type,
                "predicted_refine": predicted_refine,
                "step1_ok": predicted_type == expected_type,
                "step2_ok": predicted_refine == expected_refine if predicted_type == expected_type else None,
                "reverse_label": reverse_label,
                "predicted_refine_reverse": result["direction_2_to_1"],
            })

        except Exception as e:
            errors += 1
            print(f"  ! ОШИБКА: {e}")

    # --- Итог по категории ---
    total_step1 = step1_correct + step1_wrong
    total_step2 = step2_correct + step2_wrong
    acc_step1 = step1_correct / total_step1 * 100 if total_step1 > 0 else 0
    acc_step2 = step2_correct / total_step2 * 100 if total_step2 > 0 else 0

    rev_total_step1 = rev_step1_correct + rev_step1_wrong
    rev_total_step2 = rev_step2_correct + rev_step2_wrong
    rev_acc_step1 = rev_step1_correct / rev_total_step1 * 100 if rev_total_step1 > 0 else 0
    rev_acc_step2 = rev_step2_correct / rev_total_step2 * 100 if rev_total_step2 > 0 else 0

    print(f"\n--- Итог по '{category_name}' ---")
    print(f"  ПРЯМОЕ НАПРАВЛЕНИЕ:")
    print(f"    Шаг 1 (тип связи):  {step1_correct}/{total_step1} = {acc_step1:.1f}%")
    print(f"    Шаг 2 (уточнение):  {step2_correct}/{total_step2} = {acc_step2:.1f}%")
    print(f"    Шаг 2 пропущен (ошибка шага 1): {step2_skipped}")
    print(f"  ОБРАТНОЕ НАПРАВЛЕНИЕ:")
    print(f"    Шаг 1 (тип связи):  {rev_step1_correct}/{rev_total_step1} = {rev_acc_step1:.1f}%")
    print(f"    Шаг 2 (уточнение):  {rev_step2_correct}/{rev_total_step2} = {rev_acc_step2:.1f}%")
    print(f"    Шаг 2 пропущен (ошибка шага 1): {rev_step2_skipped}")
    print(f"    Пропущено (нет метки): {rev_skipped_no_label}")
    print(f"  Ошибок API: {errors}")

    stats = {
        "step1_correct": step1_correct, "step1_wrong": step1_wrong,
        "step2_correct": step2_correct, "step2_wrong": step2_wrong,
        "step2_skipped": step2_skipped,
        "rev_step1_correct": rev_step1_correct, "rev_step1_wrong": rev_step1_wrong,
        "rev_step2_correct": rev_step2_correct, "rev_step2_wrong": rev_step2_wrong,
        "rev_step2_skipped": rev_step2_skipped,
        "errors": errors,
        "pairs": all_pairs,
    }
    return stats


# =============================================================================
# ЗАПУСК
# =============================================================================

if __name__ == "__main__":
    N_PER_CATEGORY = 5

    datasets = load_and_split_dataset(XLSX_PATH)

    totals = {
        "step1_correct": 0, "step1_wrong": 0,
        "step2_correct": 0, "step2_wrong": 0,
        "step2_skipped": 0,
        "rev_step1_correct": 0, "rev_step1_wrong": 0,
        "rev_step2_correct": 0, "rev_step2_wrong": 0,
        "rev_step2_skipped": 0,
        "errors": 0,
    }

    all_stats = []
    for cat_name, ds in datasets.items():
        subset = ds[:N_PER_CATEGORY]
        stats = test_dataset(subset, cat_name)
        all_stats.append(stats)
        for k in totals:
            if k != "pairs":
                totals[k] += stats[k]

    t1 = totals["step1_correct"] + totals["step1_wrong"]
    t2 = totals["step2_correct"] + totals["step2_wrong"]
    rt1 = totals["rev_step1_correct"] + totals["rev_step1_wrong"]
    rt2 = totals["rev_step2_correct"] + totals["rev_step2_wrong"]

    print("\n" + "="*60)
    print("ОБЩАЯ СТАТИСТИКА")
    print("="*60)
    print(f"ПРЯМОЕ НАПРАВЛЕНИЕ:")
    print(f"  Шаг 1 (тип связи):  {totals['step1_correct']}/{t1} = {totals['step1_correct']/t1*100:.1f}%" if t1 else "  Шаг 1: нет данных")
    print(f"  Шаг 2 (уточнение):  {totals['step2_correct']}/{t2} = {totals['step2_correct']/t2*100:.1f}%" if t2 else "  Шаг 2: нет данных")
    print(f"  Шаг 2 пропущен: {totals['step2_skipped']}")
    print(f"ОБРАТНОЕ НАПРАВЛЕНИЕ:")
    print(f"  Шаг 1 (тип связи):  {totals['rev_step1_correct']}/{rt1} = {totals['rev_step1_correct']/rt1*100:.1f}%" if rt1 else "  Шаг 1: нет данных")
    print(f"  Шаг 2 (уточнение):  {totals['rev_step2_correct']}/{rt2} = {totals['rev_step2_correct']/rt2*100:.1f}%" if rt2 else "  Шаг 2: нет данных")
    print(f"  Шаг 2 пропущен: {totals['rev_step2_skipped']}")
    print(f"Ошибок API: {totals['errors']}")

    # Сохраняем результаты
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    RESULTS_DIR = BASE_DIR / "results"
    RESULTS_DIR.mkdir(exist_ok=True)
    output_path = RESULTS_DIR / f"results_{timestamp}.json"

    save_data = {
        "timestamp": timestamp,
        "n_per_category": N_PER_CATEGORY,
        "totals": {
            "step1_correct": totals["step1_correct"],
            "step1_total": t1,
            "step1_acc": round(totals["step1_correct"] / t1 * 100, 1) if t1 else 0,
            "step2_correct": totals["step2_correct"],
            "step2_total": t2,
            "step2_acc": round(totals["step2_correct"] / t2 * 100, 1) if t2 else 0,
        },
        "by_category": {}
    }

    for cat_name, stats in zip(datasets.keys(), all_stats):
        t1_cat = stats["step1_correct"] + stats["step1_wrong"]
        t2_cat = stats["step2_correct"] + stats["step2_wrong"]
        save_data["by_category"][cat_name] = {
            "step1_acc": round(stats["step1_correct"] / t1_cat * 100, 1) if t1_cat else 0,
            "step2_acc": round(stats["step2_correct"] / t2_cat * 100, 1) if t2_cat else 0,
            "pairs": stats["pairs"],
        }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(save_data, f, ensure_ascii=False, indent=2)

    print(f"\nРезультаты сохранены в {output_path}")
