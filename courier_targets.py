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
# UI (ANSI) styling + helpers
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

def pad(s: str, w: int, align: str = "left") -> str:
    plain = strip_ansi(s)
    if len(plain) >= w:
        return s
    spaces = " " * (w - len(plain))
    return (spaces + s) if align == "right" else (s + spaces)

def box(title: str, lines: list[str]) -> str:
    t = f" {title} "
    w = max(len(strip_ansi(t)), *(len(strip_ansi(x)) for x in lines), 30)
    top = "┌" + "─" * (w + 2) + "┐"
    mid = "│ " + pad(t, w) + " │"
    sep = "├" + "─" * (w + 2) + "┤"
    body = "\n".join("│ " + pad(x, w) + " │" for x in lines)
    bot = "└" + "─" * (w + 2) + "┘"
    return "\n".join([top, mid, sep, body, bot])

def center_line(s: str, width: int) -> str:
    plain = strip_ansi(s)
    if len(plain) >= width:
        return s
    left = (width - len(plain)) // 2
    return (" " * left) + s

def print_centered(s: str):
    print(center_line(s, WINDOW_COLS))


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

def per_courier_text(total_ratings: int, couriers: int) -> str:
    if couriers <= 0 or total_ratings <= 0:
        return "0"
    base = total_ratings // couriers
    extra = total_ratings % couriers
    if extra == 0:
        return f"{base}"
    return f"{base} (+1×{extra})"


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

        final_alloc = {}
        extra_total = 0
        for d, ccount in day_plan:
            base = base_alloc.get(d, 0)
            extra = (EXTRA_PER_COURIER * ccount) if ccount > 0 else 0
            final_alloc[d] = base + extra
            extra_total += extra

        final_total_needed = base_total_needed + extra_total

        # Today summary numbers
        today_couriers = get_couriers_for_date(today)
        today_total = final_alloc.get(today, 0)
        today_pc = per_courier_text(today_total, today_couriers)

        clear_console()

        # Centered title
        print_centered(bold(cyan("ОТЧЁТ ПО ЦЕЛЯМ")))
        print(gray("─" * 60))

        # One combined box "Главное" (как ты попросил)
        main_lines = [
            f"{bold('Оценок всего:')}            {total}",
            f"{bold('Положительных оценок:')}    {positive}",
            f"{bold('Текущий процент:')}         {current_percent:.2f}%",
            f"{bold('Цель:')}                   > {target}%",
            gray("────────────────────────────"),
            f"{bold('Дата:')}                   {today.isoformat()}",
            f"{bold('Курьеров сегодня:')}        {today_couriers}",
            f"{bold('Оценок за день:')}          {today_total}",
            f"{bold('Оценок на курьера:')}       {today_pc}",
        ]
        # Центрируем сам бокс по ширине окна (вставляем отступ слева)
        b = box("Главное", main_lines)
        left_pad = max(0, (WINDOW_COLS - max(len(line) for line in b.splitlines())) // 2)
        pad_prefix = " " * left_pad
        print("\n".join(pad_prefix + line for line in b.splitlines()))

        # Plan box
        status_lines = [
            f"{bold('Риск:')}  {int(NEG_RISK*100)}% (запас)",
            f"{bold('Плюс:')}  +{EXTRA_PER_COURIER} оценки на курьера/день",
            "",
            f"{bold('Нужно позитивных минимум:')} {needed_positive}",
            f"{bold('План всего оценок (с запасом):')} {base_total_needed}",
            f"{bold('Дополнительно из-за +3:')} {extra_total}",
            f"{bold('ИТОГО план всего оценок:')} {final_total_needed}",
        ]
        pb = box("План", status_lines)
        left_pad2 = max(0, (WINDOW_COLS - max(len(line) for line in pb.splitlines())) // 2)
        pad_prefix2 = " " * left_pad2
        print("\n".join(pad_prefix2 + line for line in pb.splitlines()))

        # Table (fixed columns, ровная)
        print()
        print_centered(bold("План по дням (только рабочие дни)"))

        W_DATE = 12
        W_MARK = 2
        W_COUR = 8
        W_TOTAL = 12
        W_PC = 14

        header = (
            pad(gray("Дата"), W_DATE, "left") +
            pad(gray(""), W_MARK, "left") +
            pad(gray("Курьеров"), W_COUR, "right") + " " +
            pad(gray("Оценок/день"), W_TOTAL, "right") + " " +
            pad(gray("Оценок/кур"), W_PC, "right")
        )
        print(header)
        print(gray("─" * 60))

        dist_sum = 0
        shown = 0
        for d, ccount in day_plan:
            if ccount <= 0:
                continue
            day_total = final_alloc.get(d, 0)
            if day_total <= 0:
                continue

            shown += 1
            dist_sum += day_total

            mark = cyan("•") if d == today else " "
            pc_txt = per_courier_text(day_total, ccount)

            row = (
                pad(d.isoformat(), W_DATE, "left") +
                pad(mark, W_MARK, "left") +
                pad(str(ccount), W_COUR, "right") + " " +
                pad(str(day_total), W_TOTAL, "right") + " " +
                pad(pc_txt, W_PC, "right")
            )
            print(row)

        if shown == 0:
            print(dim("Нет рабочих дней с задачами (возможно, цель уже достигнута)."))

        print(gray("─" * 60))
        ctrl = green("СХОДИТСЯ") if dist_sum == final_total_needed else yellow("ПРОВЕРЬ")
        print_centered(f"{bold('Контроль:')} распределено {dist_sum} из {final_total_needed} → {ctrl}")

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
