import datetime
import math
import os
import platform

NEG_RISK = 0.15
TARGET_PERCENTS = [90, 93, 95, 96, 97, 98, 99, 100]

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

DEFAULT_COURIERS = 5


def clear_console():
    # Windows: cls, Linux/Mac: clear
    os.system("cls" if os.name == "nt" else "clear")


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
    Строго ">" и только целые.
    """
    if target_percent >= 100:
        if positive == total:
            return 0
        return math.inf

    A = 100 - target_percent
    B = target_percent * total - 100 * positive

    if B < 0:
        return 0

    return (B // A) + 1


def get_couriers_for_date(d: datetime.date) -> int:
    return int(SCHEDULE_BY_DATE.get(d.isoformat(), DEFAULT_COURIERS))


def build_day_plan(today: datetime.date):
    end = last_day_of_month(today)
    out = []
    cur = today
    while cur <= end:
        out.append((cur, get_couriers_for_date(cur)))
        cur += datetime.timedelta(days=1)
    return out


def allocate_weighted_total(total_needed: int, day_plan: list):
    """
    Распределяем total_needed по дням пропорционально числу курьеров.
    Возвращает dict date -> allocated_total_for_day
    """
    if total_needed <= 0:
        return {d: 0 for d, _ in day_plan}

    weights = [(d, max(0, c)) for d, c in day_plan]
    total_weight = sum(w for _, w in weights)
    if total_weight == 0:
        return {d: 0 for d, _ in day_plan}

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

    remaining = total_needed - allocated_sum
    remainders.sort(key=lambda x: x[1], reverse=True)

    i = 0
    while remaining > 0 and i < len(remainders):
        d, _ = remainders[i]
        alloc[d] += 1
        remaining -= 1
        i += 1

    i = 0
    while remaining > 0 and remainders:
        d, _ = remainders[i % len(remainders)]
        alloc[d] += 1
        remaining -= 1
        i += 1

    return alloc


def fmt_int(n: int) -> str:
    return f"{n:d}"


def print_header(title: str):
    print("\n" + title)
    print("-" * len(title))


def calculate():
    print("=" * 60)
    print("ЦЕЛИ ПО ОЦЕНКАМ ДЛЯ КУРЬЕРОВ")
    print("=" * 60)

    try:
        total = int(input("Всего оценок сейчас: ").strip())
        positive = int(input("Положительных из них: ").strip())

        if total < 0 or positive < 0 or positive > total:
            print("Ошибка: positive должен быть в диапазоне [0..total].")
            return

        current_percent = (positive / total * 100) if total > 0 else 0.0
        target = pick_target(current_percent)

        # 100% недостижимо при наличии негатива — автосдвиг на 99
        if target == 100 and positive < total:
            target = 99

        needed_positive = min_positive_needed_strict(total, positive, target)
        if needed_positive is math.inf:
            print("Цель 100% недостижима при наличии негатива.")
            return

        total_needed = 0 if needed_positive == 0 else math.ceil(needed_positive / (1.0 - NEG_RISK))

        today = datetime.date.today()
        day_plan = build_day_plan(today)
        allocated_by_day = allocate_weighted_total(total_needed, day_plan)

        # после ввода всех данных — чистим консоль
        clear_console()

        # ======= СТИЛИЗОВАННЫЙ ВЫВОД =======

        # Сводка
        print("=" * 60)
        print("РЕЗУЛЬТАТ")
        print("=" * 60)

        print_header("Сводка")
        print(f"Сейчас: {positive}/{total} = {current_percent:.2f}%")
        print(f"Цель:  > {target}%")
        print(f"Риск:  {int(NEG_RISK*100)}% (запас)")
        print(f"Нужно позитивных минимум: {fmt_int(needed_positive)}")
        print(f"Собрать всего оценок:     {fmt_int(total_needed)}")

        # Сегодня
        today_couriers = get_couriers_for_date(today)
        today_total = allocated_by_day.get(today, 0)
        today_per = math.ceil(today_total / today_couriers) if today_couriers > 0 and today_total > 0 else 0

        print_header("Сегодня")
        print(f"Дата:     {today.isoformat()}")
        print(f"Курьеров: {fmt_int(today_couriers)}")
        print(f"Всего:    {fmt_int(today_total)}")
        print(f"На 1:     {fmt_int(today_per)}")

        # План по дням (только где есть курьеры и есть задача)
        print_header("План по дням (только рабочие)")
        # Заголовок колонок
        print(f"{'Дата':<12} {'Курьеров':>8} {'Всего':>8} {'На 1':>8}")
        print(f"{'-'*12} {'-'*8:>8} {'-'*8:>8} {'-'*8:>8}")

        shown = 0
        distributed_sum = 0
        for d, c in day_plan:
            day_total = allocated_by_day.get(d, 0)
            if c <= 0:
                continue
            if day_total <= 0:
                # убираем “воду”: не показываем нулевые задачи
                continue

            per = math.ceil(day_total / c)
            distributed_sum += day_total
            shown += 1
            marker = "*" if d == today else " "
            print(f"{d.isoformat():<12}{marker} {c:>8} {day_total:>8} {per:>8}")

        if shown == 0:
            print("(Нет рабочих дней с задачами — либо уже всё достигнуто, либо total_needed=0.)")

        print_header("Контроль")
        print(f"Распределено: {fmt_int(distributed_sum)} из {fmt_int(total_needed)}")

    except ValueError:
        print("Ошибка: введи числа.")
    except Exception as e:
        print(f"Ошибка: {e}")

    print("\n" + "=" * 60)
    input("Enter для выхода...")


def main():
    calculate()


if __name__ == "__main__":
    main()
