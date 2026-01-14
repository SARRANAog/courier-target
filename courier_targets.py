import datetime
import math

def calculate_courier_targets():
    print("=" * 50)
    print(" РАСЧЕТ ЕЖЕДНЕВНЫХ ЦЕЛЕЙ ДЛЯ КУРЬЕРОВ ")
    print("=" * 50)
    
    try:
        # Текущие данные
        total = int(input("Сколько всего оценок сейчас: "))
        positive = int(input("Сколько из них положительных: "))
        
        if not (0 <= positive <= total):
            print("Ошибка: неправильные данные!")
            return
        
        # Определяем цель (всегда стремимся к большему)
        current_percent = positive / total * 100 if total > 0 else 0
        
        # Целевые проценты (всегда больше текущего)
        target_percents = [90, 93, 95, 96, 97, 98, 99, 100]
        
        # Находим следующую цель
        target = 90  # минимальная цель
        for t in target_percents:
            if current_percent < t:
                target = t
                break
        
        # Если уже на 100%, то остаемся на 100%
        if current_percent >= 100:
            target = 100
        
        print(f"\nТекущий процент: {current_percent:.2f}%")
        print(f"Цель: >{target}%")
        
        # Данные по курьерам
        couriers_today = int(input("\nСколько курьеров сегодня на смене: "))
        
        if couriers_today <= 0:
            print("Ошибка: должно быть хотя бы 2 курьера!")
            return
        
        # Дни до конца месяца
        today = datetime.date.today()
        if today.month == 12:
            last_day = datetime.date(today.year + 1, 1, 1) - datetime.timedelta(days=1)
        else:
            last_day = datetime.date(today.year, today.month + 1, 1) - datetime.timedelta(days=1)
        
        days_left = (last_day - today).days + 1  # включая сегодня
        
        if days_left <= 0:
            print("Месяц уже закончился!")
            return
        
        print(f"\nДней до конца месяца: {days_left}")
        
        # Расчет необходимых положительных оценок для цели
        target_fraction = target / 100.0
        
        # Решаем: (positive + x) / (total + x) > target/100
        if target_fraction >= 1:
            # Цель 100% - нужны только положительные и без негативных
            needed_positive = total - positive
            needed_total = needed_positive  # только позитивные
        else:
            x_min_exact = (target_fraction * total - positive) / (1 - target_fraction)
            needed_positive = max(0, math.ceil(x_min_exact))
            needed_total = needed_positive
        
        print(f"\nМинимально нужно положительных оценок: {needed_positive}")
        
        # УЧЕТ НЕГАТИВНЫХ ОЦЕНОК (запас 20%)
        # Предположим, что 10% новых оценок могут быть негативными
        negative_risk = 0.10  # 10% риск негатива
        reserve_factor = 1.0 / (1 - negative_risk)  # ~1.11
        
        # Итоговое количество оценок, которые нужно собрать
        total_needed = math.ceil(needed_positive * reserve_factor)
        
        # Дополнительный запас для уверенности
        total_needed = math.ceil(total_needed * 1.1)  # +10% запаса
        
        # Распределение по дням
        ratings_per_day = math.ceil(total_needed / days_left)
        
        # Распределение между курьерами
        per_courier_per_day = math.ceil(ratings_per_day / couriers_today)
        
        print("\n" + "=" * 50)
        print(" РЕЗУЛЬТАТ РАСЧЕТА ")
        print("=" * 50)
        
        print(f"\n📊 ТЕКУЩАЯ СИТУАЦИЯ:")
        print(f"   Оценок: {positive}/{total} = {current_percent:.2f}%")
        print(f"   Цель: >{target}%")
        
        print(f"\n🎯 НЕОБХОДИМО СОБРАТЬ:")
        print(f"   Всего оценок: {total_needed}")
        print(f"   Из них положительных не менее: {needed_positive}")
        print(f"   Учитывая риск негативных оценок (+20% запаса)")
        
        print(f"\n📅 РАСПРЕДЕЛЕНИЕ:")
        print(f"   Дней осталось: {days_left}")
        print(f"   Курьеров сегодня: {couriers_today}")
        print(f"   В день всего: {ratings_per_day} оценок")
        print(f"   На каждого курьера в день: {per_courier_per_day} оценок")
        
        # Рекомендации
        print(f"\n💡 РЕКОМЕНДАЦИИ:")
        print(f"   1. Цель на курьера: {per_courier_per_day} оценок в день")
        
        if per_courier_per_day > 5:
            print(f"   2. ⚠️  Цель высокая, нужна дополнительная мотивация!")
        elif per_courier_per_day <= 2:
            print(f"   2. ✅ Цель реалистичная, можно выполнить")
        else:
            print(f"   2. 📈 Цель достижима при хорошей работе")
        
        # Прогноз
        total_by_plan = per_courier_per_day * couriers_today * days_left
        print(f"\n📈 ПРОГНОЗ:")
        print(f"   По плану будет собрано: ~{total_by_plan} оценок")
        
        if total_by_plan >= total_needed:
            print(f"   ✅ План достаточен для достижения цели {target}%")
        else:
            shortage = total_needed - total_by_plan
            extra_per_day = math.ceil(shortage / days_left / couriers_today)
            print(f"   ⚠️  Не хватит ~{shortage} оценок")
            print(f"   Нужно дополнительно: +{extra_per_day} оценок на курьера в день")
        
        # Следующая цель
        if target < 100:
            next_target_idx = target_percents.index(target) + 1
            if next_target_idx < len(target_percents):
                next_target = target_percents[next_target_idx]
                print(f"\n🎯 СЛЕДУЮЩАЯ ЦЕЛЬ: {next_target}%")
        
    except ValueError:
        print("Ошибка: введите числа!")
    except Exception as e:
        print(f"Ошибка: {e}")
    
    print("\n" + "=" * 50)
    input("Нажмите Enter для выхода...")

def main():
    calculate_courier_targets()
main()
