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

# Окно побольше (но без ограничения буфера — скролл есть)
WINDOW_COLS = 110
WINDOW_ROWS = 45
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
    - размер окна (cols x rows)
    - центрирование окна
    - включить ANSI
    ВАЖНО: buffer не трогаем (скролл доступен, ничего не режется)
    """
    if os.name != "nt":
        return

    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        user32 = ctypes.WinDLL("user32", use_last_error=True)

        class RECT(ctypes.Structure):
            _fields_ = [
                ("left", wintypes.LONG),
                ("top", wintypes.LONG),
                ("right", wintypes.LONG),
                ("bottom", wintypes.LONG),
            ]

        STD_OUTPUT_HANDLE = -11
        ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004

        SWP_NOZORDER = 0x0004
        SWP_NOSIZE = 0x0001

        SM_CXSCREEN = 0
        SM_CYSCREEN = 1

        kernel32.SetConsoleTitleW(wintypes.LPCWSTR(title))

        # set window size
        os.system(f"mode con: cols={cols} lines={rows}")

        # enable ANSI
        h_out = kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
        if h_out not in (0, -1):
            mode = wintypes.DWORD()
            if kernel32.GetConsoleMode(h_out, ctypes.byref(mode)):
                kernel32.SetConsoleMode(
                    h_out, wintypes.DWORD(mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING)
                )

        # center window
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


def bold(s: str) -> str:
    return _c(s, "1")


def dim(s: str) -> str:
    return _c(s, "2")


def green(s: str) -> str:
    return _c(s, "32")


def yellow(s: str) -> str:
    return _c(s, "33")


def cyan(s: str) -> str:
    return _c(s, "36")


def gray(s: str) -> str:
    return _c(s, "90")


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


def block_width(lines: list[str]) -> int:
    return max((len(strip_ansi(x)) for x in lines), default=0)


def center_block(lines: list[str], width: int) -> list[str]:
    max_len = block_width(lines)
    left_pad = max(0, (width - max_len) // 2)
    pref = " " * left_pad
    return [pref + x for x in lines]


def print_centered_line(s: str):
    plain = strip_ansi(s)
    if len(plain) >= WINDOW_COLS:
        print(s)
        return
    left = max(0, (WINDOW_COLS - len(plain)) // 2)
    print((" " * left) + s)


def print_centered_hr(content_width: int, char: str = "─"):
    """
    Линия, подогнанная под ширину контента, и центрированная как блоки.
    """
    w = max(0, min(content_width, WINDOW_COLS))
    line = gray(char * w)
    plain = strip_ansi(line)
    left = max(0, (WINDOW_COLS - len(plain)) // 2)
    print((" " * left) + line)


def box_lines(title: str, lines: list[str]) -> list[str]:
    t = f" {title} "
    w = max(len(strip_ansi(t)), *(len(strip_ansi(x)) for x in lines), 30)
    top = "┌" + "─" * (w + 2) + "┐"
    mid = "│ " + pad(t, w) + " │"
    sep = "├" + "─" * (w + 2) + "┤"
    body = ["│ " + pad(x, w) + " │" for x in lines]
    bot = "└" + "─" * (w + 2) + "┘"
    return [top, mid, sep, *body, bot]


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


def per_courier_text(total_ratings: int, couriers: int) -> str:
    if couriers <= 0 or total_ratings <= 0:
        return "0"
    base = total_ratings // couriers
    extra = total_ratings % couriers
    if extra == 0:
        return f"{base}"
    return f"{base} (+1×{extra})"


# -------------------------
# Table rendering (boxed + centered)
# -------------------------
def build_table_box(day_plan, final_alloc, today: datetime.date) -> list[str]:
    W_DATE = 10
    W_MARK = 1
    W_COUR = 7
    W_DAY = 10
    W_PC = 12

    def cell(text: str, w: int, align: str):
        return pad(text, w, align)

    header = (
        "│ "
        + cell("Дата", W_DATE, "left")
        + " "
        + cell("", W_MARK, "left")
        + " │ "
        + cell("Курьеров", W_COUR, "right")
        + " │ "
        + cell("Оценок/день", W_DAY, "right")
        + " │ "
        + cell("Оценок/кур", W_PC, "right")
        + " │"
    )

    width = len(strip_ansi(header)) - 2
    top = "┌" + "─" * width + "┐"
    mid = "├" + "─" * width + "┤"
    bot = "└" + "─" * width + "┘"

    rows = [top, header, mid]

    any_rows = False
    for d, ccount in day_plan:
        if ccount <= 0:
            continue
        day_total = final_alloc.get(d, 0)
        if day_total <= 0:
            continue
        any_rows = True

        mark = cyan("•") if d == today else " "
        pc_txt = per_courier_text(day_total, ccount)

        r = (
            "│ "
            + cell(d.isoformat(), W_DATE, "left")
            + " "
            + cell(mark, W_MARK, "left")
            + " │ "
            + cell(str(ccount), W_COUR, "right")
            + " │ "
            + cell(str(day_total), W_DAY, "right")
            + " │ "
            + cell(pc_txt, W_PC, "right")
            + " │"
        )
        rows.append(r)

    if not any_rows:
        msg = dim("Нет рабочих дней с задачами.")
        r = "│ " + pad(msg, width - 2, "left") + " │"
        rows.append(r)

    rows.append(bot)
    return rows


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

        today_couriers = get_couriers_for_date(today)
        today_total = final_alloc.get(today, 0)
        today_pc = per_courier_text(today_total, today_couriers)

        clear_console()

        # Build blocks first to know widths (для идеальных линий)
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
        main_box = box_lines("Главное", main_lines)

        plan_lines = [
            f"{bold('План всего оценок (с запасом):')} {base_total_needed}",
            f"{bold('Дополнительно из-за +3:')}         {extra_total}",
            f"{bold('ИТОГО план всего оценок:')}        {final_total_needed}",
        ]
        plan_box = box_lines("План", plan_lines)

        table_box = build_table_box(day_plan, final_alloc, today)

        # Compute content width for perfect HR lines
        content_w = max(block_width(main_box), block_width(plan_box), block_width(table_box), 40)

        # Output
        print_centered_line(bold(cyan("ОТЧЁТ ПО ЦЕЛЯМ")))
        print_centered_hr(content_w)

        for line in center_block(main_box, WINDOW_COLS):
            print(line)

        for line in center_block(plan_box, WINDOW_COLS):
            print(line)

        print()
        print_centered_line(bold("План по дням (только рабочие дни)"))
        for line in center_block(table_box, WINDOW_COLS):
            print(line)

        print_centered_hr(content_w)

       

    except ValueError:
        print("Ошибка: введи числа.")
    except Exception as e:
        print(f"Ошибка: {e}")

    print("\n" + gray("─" * min(WINDOW_COLS, 140)))
    input("Enter для выхода...")


def main():
    calculate()


if __name__ == "__main__":
    main()
