import datetime
import math

def last_day_of_month(d: datetime.date) -> datetime.date:
    if d.month == 12:
        return datetime.date(d.year + 1, 1, 1) - datetime.timedelta(days=1)
    return datetime.date(d.year, d.month + 1, 1) - datetime.timedelta(days=1)

def pick_target(current_percent: float, targets=(90, 93, 95, 96, 97, 98, 99, 100)) -> int:
    for t in targets:
        if current_percent < t:
            return t
    return 100

def min_x_for_strict_percent(total: int, positive: int, target_percent: int) -> int:
    """
    Minimal x >= 0 such that:
        100*(positive + x) > target_percent*(total + x)
    Works with integers (no float rounding issues).
    """
    if total < 0 or positive < 0 or positive > total:
        raise ValueError("Некорректные total/positive.")

    if target_percent >= 100:
        if positive == total:
            return 0  # уже 100%
        # 100% недостижимо, если уже есть негатив
        return math.inf

    A = 100 - target_percent
    B = target_percent * total - 100 * positive

    if B < 0:
        return 0

    # Need A*x > B  =>  x = floor(B/A) + 1
    return (B // A) + 1

def achieved_strict(total: int, positive: int, target_percent: int) -> bool:
    return 100 * positive > target_percent * total

def min_new_ratings_with_negative_risk(total: int, positive: int, target_percent: int, neg_rate: float) -> int:
    """
    Finds minimal N (total new ratings) so that even in worst-case
    negatives = ceil(neg_rate * N), positives_new = N - negatives,
    we still achieve strict target.
    """
    if not (0.0 <= neg_rate < 1.0):
        raise ValueError("neg_rate должен быть в диапазоне [0, 1).")

    # If target is 100% and already not perfect, impossible
    if target_percent >= 100 and positive < total:
        return math.inf

    # quick check: already achieved
    if achieved_strict(total, positive, target_percent):
        return 0

    # Lower bound: assume all new are positive
    x0 = min_x_for_strict_percent(total, positive, target_percent)
    if x0 is math.inf:
        return math.inf

    # We'll search from x0 upward until worst-case negatives still pass
    N = max(0, x0)
    while True:
        worst_neg = math.ceil(neg_rate * N)
        new_pos = N - worst_neg
        if new_pos < 0:
            new_pos = 0

        tot2 = total + N
        pos2 = positive + new_pos

        if achieved_strict(tot2, pos2, target_percent):
            return N

        N += 1  # N is usually not huge; this is safe for practical ranges

def calculate():
    print("=" * 60)
    print(" РАСЧЕТ ЕЖЕДНЕВНЫХ ЦЕЛЕЙ ДЛЯ КУРЬЕРОВ (корректно)")
    print("=" * 60)

    try:
        total = int(input("Сколько всего оценок сейчас: ").strip())
        positive = int(input("Сколько из них положительных: ").strip())

        if total < 0 or positive < 0 or positive > total:
            print("Ошибка: неправильные данные (positive должно быть от 0 до total).")
            return

        current_percent = (positive / total * 100) if total > 0 else 0.0
        target = pick_target(current_percent)

        print(f"\nТекущий процент: {current_percent:.2f}%")
        if target == 100 and positive < total:
            print("Цель 100% недостижима, пока уже есть негативные оценки.")
            print("Рекомендация: ставь следующую цель 99% или 99.5%, либо работай над снижением негатива.")
            # всё равно продолжим, но с target=99 как разумной заменой
            target = 99
            print("Автозамена цели на 99%.\n")

        print(f"Цель: строго больше {target}%")

        # риск негатива
        neg_rate_percent = float(input("\nКакой риск негатива в новых оценках, % (например 10): ").strip())
        neg_rate = neg_rate_percent / 100.0

        # дни до конца месяца
        today = datetime.date.today()
        last_day = last_day_of_month(today)
        days_left = (last_day - today).days + 1
        print(f"\nДней до конца месяца (включая сегодня): {days_left}")

        # план по курьерам: сколько смен до конца месяца
        n = int(input("\nСколько курьеров учитывать в плане: ").strip())
        if n <= 0:
            print("Ошибка: нужно хотя бы 1 курьера.")
            return

        couriers = []
        total_shifts = 0
        print("\nВведи курьеров и сколько смен у каждого до конца месяца (включая сегодня).")
        for i in range(n):
            name = input(f"Курьер #{i+1} имя: ").strip() or f"Курьер{i+1}"
            shifts = int(input(f"Сколько смен до конца месяца у {name}: ").strip())
            if shifts < 0:
                print("Ошибка: смены не могут быть отрицательными.")
                return
            couriers.append((name, shifts))
            total_shifts += shifts

        if total_shifts == 0:
            print("Ошибка: суммарно 0 смен — считать нечего.")
            return

        # считаем, сколько всего новых оценок нужно
        total_needed_new = min_new_ratings_with_negative_risk(total, positive, target, neg_rate)
        if total_needed_new is math.inf:
            print("\nНевозможно достичь цели при текущих вводных.")
            return

        # в худшем случае сколько из новых будет позитивных
        worst_neg = math.ceil(neg_rate * total_needed_new)
        min_new_positive = total_needed_new - worst_neg

        print("\n" + "=" * 60)
        print(" РЕЗУЛЬТАТ ")
        print("=" * 60)

        print(f"\n📊 Сейчас: {positive}/{total} = {current_percent:.2f}%")
        print(f"🎯 Цель: > {target}%")
        print(f"⚠️ Риск негатива: {neg_rate_percent:.1f}% (в худшем случае)")

        print(f"\n✅ Нужно собрать всего новых оценок: {total_needed_new}")
        print(f"   Из них положительных минимум: {min_new_positive} (если негативов будет до {worst_neg})")

        # распределение по сменам
        per_shift_target = math.ceil(total_needed_new / total_shifts)
        print(f"\n📅 План по сменам: всего смен до конца месяца: {total_shifts}")
        print(f"   Цель на 1 смену (в среднем): {per_shift_target} оценок")

        print("\n👤 По курьерам (на их смены):")
        for name, shifts in couriers:
            if shifts == 0:
                print(f" - {name}: 0 смен → 0")
                continue
            # распределяем пропорционально сменам
            share = shifts / total_shifts
            courier_total = math.ceil(total_needed_new * share)
            courier_per_day = math.ceil(courier_total / shifts)
            print(f" - {name}: всего ~{courier_total} оценок за {shifts} смен → {courier_per_day} в смену")

        # проверочный прогноз (если соберут ровно per_shift_target каждый shift)
        planned_total = per_shift_target * total_shifts
        worst_neg_plan = math.ceil(neg_rate * planned_total)
        pos_plan = positive + (planned_total - worst_neg_plan)
        tot_plan = total + planned_total
        ok = achieved_strict(tot_plan, pos_plan, target)

        print(f"\n📈 Проверка плана (в худшем случае): собрать {planned_total} новых оценок")
        if ok:
            print("   ✅ Должно хватить для достижения цели.")
        else:
            print("   ⚠️ Может не хватить — увеличь цель на смену на +1.")

    except ValueError:
        print("Ошибка: где-то введено не число.")
    except Exception as e:
        print(f"Ошибка: {e}")

    print("\n" + "=" * 60)
    input("Нажмите Enter для выхода...")

def main():
    calculate()

if __name__ == "__main__":
    main()
