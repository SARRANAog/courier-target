import datetime
import math

NEG_RISK = 0.15  # фикс 15% "на всякий случай"
TARGET_PERCENTS = [90, 93, 95, 96, 97, 98, 99, 100]

# ==========================================================
# ГРАФИК КУРЬЕРОВ (дата -> количество курьеров)
# Формат ключей: "YYYY-MM-DD"
# ==========================================================
SCHEDULE_BY_DATE = {
    "2026-01-15": 5,
    "2026-01-16": 7,
    "2026-01-17": 6,
    "2026-01-18": 5,
    "2026-01-19": 6,
    "2026-01-20": 6,
    "2026-01-21": 6,
    "2026-01-22": 4,
    "2026-01-23": 8,
    "2026-01-24": 8,
    "2026-01-25": 6,
    "2026-01-26": 6,
    "2026-01-27": 6,
    "2026-01-28": 7,
    "2026-01-29": 6,
    "2026-01-30": 8,
    "2026-01-31": 6,
}

# Если для какой-то даты нет записи — берём это значение.
DEFAULT_COURIERS = 5


def last_day_of_month(d: datetime.date) -> datetime.date:
    if d.month == 12:
        return datetime.date(d.year + 1, 1, 1) - datetime.timedelta(days=1)
    return datetime.date(d.year, d.month + 1, 1) - datetime.timedelta(days=1)


def pick_target(current_percent: float) -> int:
    for t in TARGET_PERCENTS:
        if current_percent < t:
            return t
    return 100


def min_positive_needed_strict(total: int, positive: int, target_percent: int):
    """
    Минимальное x >= 0, чтобы:
        100*(positive + x) > target_percent*(total + x)
    Считаем строго ">" и целыми числами.
    """
    if target_percent >= 100:
        if positive == total:
            return 0
        return math.inf  # 100% недостижимо, если уже есть негатив

    A = 100 - target_percent
    B = target_percent * total - 100 * positive

    if B < 0:
        return 0

    # A*x > B  =>  x = floor(B/A) + 1
    return (B // A) + 1


def get_couriers_for_date(d: datetime.date) -> int:
    key = d.isoformat()
    val = SCHEDULE_BY_DATE.get(key, DEFAULT_COURIERS)
    if val is None:
        val = DEFAULT_COURIERS
    return int(val)


def build_day_plan(today: datetime.date):
    end = last_day_of_month(today)
    days = []
    cur = today
    while cur <= end:
        c = get_couriers_for_date(cur)
        days.append((cur, c))
        cur += datetime.timedelta(days=1)
    return days


def allocate_weighted_total(total_needed: int, day_plan: list):
    """
    Распределяем total_needed по дням пропорционально количеству курьеров.
    day_plan: [(date, couriers_count), ...]
    Возвращает dict: date -> allocated_total_for_day (int)
    """
    if total_needed <= 0:
        return {d: 0 for d, _ in day_plan}

    weights = []
    for d, c in day_plan:
        if c <= 0:
            # 0 курьеров => 0 веса
            weights.append((d, 0))
        else:
            weights.append((d, c))

    total_weight = sum(w for _, w in weights)
    if total_weight == 0:
        # некому работать — распределять некуда
        return {d: 0 for d, _ in day_plan}

    # Сначала берём "пол"
    alloc = {}
    remainders = []
    allocated_sum = 0

    for d, w in weights:
        if w == 0:
            alloc[d] = 0
            continue
        exact = total_needed * (w / total_weight)
        base = int(math.floor(exact))
        alloc[d] = base
        allocated_sum += base
        remainders.append((d, exact - base))

    # Докидываем остаток по наибольшим дробным частям
    remaining = total_needed - allocated_sum
    remainders.sort(key=lambda x: x[1], reverse=True)

    i = 0
    while remaining > 0 and i < len(remainders):
        d, _ = remainders[i]
        alloc[d] += 1
        remaining -= 1
        i += 1

    # Если всё ещё остался остаток (теоретически редко), докидываем по кругу
    i = 0
    while remaining > 0 and remainders:
        d, _ = remainders[i % len(remainders)]
        alloc[d] += 1
        remaining -= 1
        i += 1

    return alloc


def calculate():
    print("=" * 70)
    print("РАСЧЕТ ЦЕЛЕЙ ДЛЯ КУРЬЕРОВ (по дням, по количеству курьеров)")
    print("=" * 70)

    try:
        total = int(input("Сколько всего оценок сейчас: ").strip())
        positive = int(input("Сколько из них положительных: ").strip())

        if total < 0 or positive < 0 or positive > total:
            print("Ошибка: positive должно быть в диапазоне [0..total].")
            return

        current_percent = (positive / total * 100) if total > 0 else 0.0
        target = pick_target(current_percent)

        # Если цель 100% недостижима (есть негатив), не даём скрипту уходить в тупик
        if target == 100 and positive < total:
            target = 99  # разумная автозамена

        needed_positive = min_positive_needed_strict(total, positive, target)
        if needed_positive is math.inf:
            print("\nЦель 100% недостижима, пока уже есть негативные оценки.")
            return

        # С запасом 15% считаем, сколько ВСЕГО оценок надо собрать,
        # чтобы "ожидаемо" набрать needed_positive позитивных
        total_needed = 0 if needed_positive == 0 else math.ceil(needed_positive / (1.0 - NEG_RISK))

        today = datetime.date.today()
        day_plan = build_day_plan(today)  # [(date, couriers_count), ...]

        # Валидация: курьеров >= 1 в рабочих днях
        # Если где-то 0 — просто выдадим 0 задач на этот день
        allocated_by_day = allocate_weighted_total(total_needed, day_plan)

        print("\n" + "-" * 70)
        print(f"Текущий процент: {current_percent:.2f}%  ({positive}/{total})")
        print(f"Цель: > {target}%")
        print(f"Нужно позитивных минимум: {needed_positive}")
        print(f"Запас на негатив: {int(NEG_RISK*100)}%")
        print(f"Итого оценок собрать (с запасом): {total_needed}")
        print("-" * 70)

        print("\n" + "=" * 70)
        print("ПЛАН ПО ДНЯМ")
        print("=" * 70)

        total_check = 0
        for d, c in day_plan:
            day_total = allocated_by_day.get(d, 0)
            total_check += day_total

            if c <= 0:
                per_courier = 0
            else:
                per_courier = math.ceil(day_total / c) if day_total > 0 else 0

            mark = " (СЕГОДНЯ)" if d == today else ""
            print(f"{d.isoformat()}{mark}: курьеров {c} | всего {day_total} | на 1 курьера {per_courier}")

        print("\n" + "-" * 70)
        print(f"Проверка суммы: распределено {total_check} из {total_needed}")
        print("-" * 70)

    except ValueError:
        print("Ошибка: где-то введено не число.")
    except Exception as e:
        print(f"Ошибка: {e}")

    print("\n" + "=" * 70)
    input("Нажмите Enter для выхода...")


def main():
    calculate()


if __name__ == "__main__":
    main()
