import datetime
import math
import os
import sys

# -------------------------
# CONFIG
# -------------------------
NEG_RISK = 0.15
TARGET_PERCENTS = [90, 93, 95, 96, 97, 98, 99, 100]
EXTRA_PER_COURIER = 3

# Размер окна (в символах)
WINDOW_COLS = 92
WINDOW_ROWS = 30
WINDOW_TITLE = "Courier Ratings Targets"

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


# -------------------------
# Console window control (Windows, cmd/exe)
# -------------------------
def setup_console_window(cols: int, rows: int, title: str):
    """
    Windows-only:
    - заголовок
    - размер окна cols x rows (символы)
    - убрать скроллбар (буфер = окно)
    - центрирование
    - включить ANSI (Virtual Terminal Processing)
    """
    if os.name != "nt":
        return

    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        user32 = ctypes.WinDLL("user32", use_last_error=True)

        class COORD(ctypes.Structure):
            _fields_ = [("X", wintypes.SHORT), ("Y", wintypes.SHORT)]

        class SMALL_RECT(ctypes.Structure):
            _fields_ = [("Left", wintypes.SHORT),
                        ("Top", wintypes.SHORT),
                        ("Right", wintypes.SHORT),
                        ("Bottom", wintypes.SHORT)]

        class RECT(ctypes.Structure):
            _fields_ = [("left", wintypes.LONG),
                        ("top", wintypes.LONG),
                        ("right", wintypes.LONG),
                        ("bottom", wintypes.LONG)]

        STD_OUTPUT_HANDLE = -11
        ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004

        SWP_NOZORDER = 0x0004
        SWP_NOSIZE = 0x0001

        SM_CXSCREEN = 0
        SM_CYSCREEN = 1

        kernel32.SetConsoleTitleW(wintypes.LPCWSTR(title))

        h_out = kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
        if h_out in (0, -1):
            return

        # enable ANSI
        mode = wintypes.DWORD()
        if kernel32.GetConsoleMode(h_out, ctypes.byref(mode)):
            kernel32.SetConsoleMode(h_out, wintypes.DWORD(mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING))

        # remove scrollbar: buffer == window
        tiny = SMALL_RECT(0, 0, 1, 1)
        kernel32.SetConsoleWindowInfo(h_out, True, ctypes.byref(tiny))

        buf = COORD(cols, rows)
        kernel32.SetConsoleScreenBufferSize(h_out, buf)

        win = SMALL_RECT(0, 0, cols - 1, rows - 1)
        kernel32.SetConsoleWindowInfo(h_out, True, ctypes.byref(win))
        kernel32.SetConsoleScreenBufferSize(h_out, buf)

        # center
        hwnd = kernel32.GetConsoleWindow()
        if hwnd:
            rect = RECT()
            if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                win_w = rect.right - rect.left
                win_h = rect.bottom - rect.top
                scr_w = user32.GetSystemMetrics(SM_CXSCREEN)
                scr_h = user32.GetSystemMetrics(SM_CYSCREEN)
                x = max(0, (scr_w - win_w) // 2)
                y = max(0, (scr_h - win_h) // 2)
                user32.SetWindowPos(hwnd, None, x, y, 0, 0, SWP_NOZORDER | SWP_NOSIZE)

    except Exception:
        return


# -------------------------
# UI (ANSI) styling
# -------------------------
def supports_ansi() -> bool:
    if os.getenv("NO_COLOR"):
        return False
    if os.name == "nt":
        return True
    return sys.stdout.isatty()

ANSI = supports_ansi()

def _c(s: str, code: str) -> str:
    if not ANSI:
        return s
    return f"\033[{code}m{s}\033[0m"

def bold(s: str) -> str: return _c(s, "1")
def dim(s: str) -> str: return _c(s, "2")
def red(s: str) -> str: return _c(s, "31")
def green(s: str) -> str: return _c(s, "32")
def yellow(s: str) -> str: return _c(s, "33")
def cyan(s: str) -> str: return _c(s, "36")
def gray(s: str) -> str: return _c(s, "90")

def clear_console():
    os.system("cls" if os.name == "nt" else "clear")

def strip_ansi(s: str) -> str:
    out = []
    i = 0
    while i < len(s):
        if s[i] == "\033" and i + 1 < len(s) and s[i + 1] == "[":
            j = i + 2
            while j < len(s) and s[j] != "m":
                j += 1
            i = j + 1
            continue
        out.append(s[i])
        i += 1
    return "".join(out)

def pad(s: str, w: int) -> str:
    return s + " " * max(0, w - len(strip_ansi(s)))

def box(title: str, lines: list[str]) -> str:
    t = f" {title} "
    w = max(len(strip_ansi(t)), *(len(strip_ansi(x)) for x in lines), 26)
    top = "┌" + "─" * (w + 2) + "┐"
    mid = "│ " + pad(t, w) + " │"
    sep = "├" + "─" * (w + 2) + "┤"
    body = "\n".join("│ " + pad(x, w) + " │" for x in lines)
    bot = "└" + "─" * (w + 2) + "┘"
    return "\n".join([top, mid, sep, body, bot])


# -------------------------
# Core math
# -------------------------
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
    # 100*(positive+x) > target*(total+x)
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

def allocate_weighted_total(total_needed: int, day_plan: list[tuple[datetime.date, int]]):
    if total_needed <= 0:
        return {d: 0 for d, _ in day_plan}

    weights = [(d, max(0, c)) for d, c in day_plan]
    total_weight = sum(w for _, w in weights)
    if total_weight == 0:
        return {d: 0 for d, _ in day_plan}

    alloc = {}
    rema = []
    s = 0
    for d, w in weights:
        if w == 0:
            alloc[d] = 0
            continue
        exact = total_needed * (w / total_weight)
        base = int(math.floor(exact))
        alloc[d] = base
        s += base
        rema.append((d, exact - base))

    remaining = total_needed - s
    rema.sort(key=lambda x: x[1], reverse=True)

    i = 0
    while remaining > 0 and i < len(rema):
        alloc[rema[i][0]] += 1
        remaining -= 1
        i += 1

    i = 0
    while remaining > 0 and rema:
        alloc[rema[i % len(rema)][0]] += 1
        remaining -= 1
        i += 1

    return alloc

def per_courier_split(total_ratings: int, couriers: int) -> tuple[int, int]:
    """
    Возвращает (base, extra_count):
    base — минимум на каждого
    extra_count — сколько курьеров получат +1 (чтобы сумма сошлась ровно)
    Пример: total=22, couriers=5 => base=4, extra=2 (двое по 5, трое по 4)
    """
    if couriers <= 0:
        return 0, 0
    base = total_ratings // couriers
    extra = total_ratings % couriers
    return base, extra

def per_courier_text(total_ratings: int, couriers: int) -> str:
    base, extra = per_courier_split(total_ratings, couriers)
    if couriers <= 0:
        return "0"
    if total_ratings <= 0:
        return "0"
    if extra == 0:
        return f"{base}"
    return f"{base} (+1 для {extra})"


# -------------------------
# Program
# -------------------------
def calculate():
    setup_console_window(WINDOW_COLS, WINDOW_ROWS, WINDOW_TITLE)

    print("=" * 60)
    print("ЦЕЛИ ПО ОЦЕНКАМ ДЛЯ КУРЬЕРОВ")
    print("=" * 60)

    try:
        total = int(input("Всего оценок сейчас: ").strip())
        positive = int(input("Положительных из них: ").strip())
        if total < 0 or positive < 0 or positive > total:
            print("Ошибка: положительные должны быть в диапазоне [0..всего].")
            return

        current_percent = (positive / total * 100) if total > 0 else 0.0
        target = pick_target(current_percent)
        if target == 100 and positive < total:
            target = 99

        needed_positive = min_positive_needed_strict(total, positive, target)
        if needed_positive is math.inf:
            print("Цель 100% недостижима при наличии негатива.")
            return

        base_total_needed = 0 if needed_positive == 0 else math.ceil(needed_positive / (1.0 - NEG_RISK))

        today = datetime.date.today()
        day_plan = build_day_plan(today)
        base_alloc = allocate_weighted_total(base_total_needed, day_plan)

        # Add +3 per courier per day
        final_alloc = {}
        extra_total = 0
        for d, ccount in day_plan:
            base = base_alloc.get(d, 0)
            extra = (EXTRA_PER_COURIER * ccount) if ccount > 0 else 0
            final_alloc[d] = base + extra
            extra_total += extra

        final_total_needed = base_total_needed + extra_total

        # clean after inputs
        clear_console()

        print(bold(cyan("ОТЧЁТ ПО ЦЕЛЯМ")))
        print(gray("─" * 60))

        # NEW: верхний бокс "как ты просил"
        top_lines = [
            f"{bold('Оценок всего:')}        {total}",
            f"{bold('Положительных оценок:')} {positive}",
            f"{bold('Текущий процент:')}     {current_percent:.2f}%",
            f"{bold('Цель:')}               > {target}%",
        ]
        print(box("Текущие данные", top_lines))

        status_lines = [
            f"{bold('Риск:')}  {int(NEG_RISK*100)}% (запас)",
            f"{bold('Плюс:')}  +{EXTRA_PER_COURIER} оценки на курьера/день",
            "",
            f"{bold('Нужно позитивных минимум:')} {needed_positive}",
            f"{bold('План всего оценок (с запасом):')} {base_total_needed}",
            f"{bold('Дополнительно из-за +3:')} {extra_total}",
            f"{bold('ИТОГО план всего оценок:')} {final_total_needed}",
        ]
        print(box("План", status_lines))

        # Today box with correct per-courier split
        today_couriers = get_couriers_for_date(today)
        today_total_ratings = final_alloc.get(today, 0)
        pc_text = per_courier_text(today_total_ratings, today_couriers)
        badge = green("OK") if today_total_ratings > 0 else yellow("CHECK")

        today_lines = [
            f"{bold('Дата:')}                 {today.isoformat()}",
            f"{bold('Курьеров:')}             {today_couriers}",
            f"{bold('Всего оценок:')}         {today_total_ratings}",
            f"{bold('Оценок на курьера:')}    {pc_text}  {dim(f'({badge})')}",
        ]
        print(box("Сегодня", today_lines))

        # Table (only working days)
        print(bold("План по дням (только рабочие дни)"))
        header = (
            f"{gray('Дата'.ljust(12))} "
            f"{gray('Курьеров'.rjust(8))} "
            f"{gray('Всего оценок'.rjust(12))} "
            f"{gray('Оценок/кур'.rjust(14))}"
        )
        print(header)
        print(gray("─" * 60))

        shown = 0
        dist_sum = 0
        for d, ccount in day_plan:
            if ccount <= 0:
                continue

            day_total = final_alloc.get(d, 0)
            if day_total <= 0:
                continue

            dist_sum += day_total
            shown += 1

            mark = cyan("•") if d == today else " "
            pc = per_courier_text(day_total, ccount)
            print(f"{d.isoformat():<12} {mark} {ccount:>8} {day_total:>12} {pc:>14}")

        if shown == 0:
            print(dim("Нет рабочих дней с задачами (возможно, цель уже достигнута)."))

        print(gray("─" * 60))
        ok = (dist_sum == final_total_needed)
        ctrl = green("СХОДИТСЯ") if ok else red("НЕ СХОДИТСЯ")
        print(f"{bold('Контроль:')} распределено {dist_sum} из {final_total_needed} → {ctrl}")

    except ValueError:
        print("Ошибка: введи числа.")
    except Exception as e:
        print(f"Ошибка: {e}")

    print("\n" + gray("─" * 60))
    input("Enter для выхода...")


def main():
    calculate()


if __name__ == "__main__":
    main()
