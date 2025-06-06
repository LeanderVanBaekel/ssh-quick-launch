import curses
import shlex

# ── Colors ──
HI, EXIT_NORM, EXIT_SEL, HEADER, SUBHDR = range(1, 6)


def setup_colors():
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(HI,        curses.COLOR_BLACK,  curses.COLOR_CYAN)
    curses.init_pair(EXIT_NORM, curses.COLOR_RED,    -1)
    curses.init_pair(EXIT_SEL,  curses.COLOR_BLACK,  curses.COLOR_RED)
    curses.init_pair(HEADER,    curses.COLOR_GREEN,  -1)
    curses.init_pair(SUBHDR,    curses.COLOR_MAGENTA,-1)


# ── Common commands ──
COMMON_COMMANDS = [
    ("Tail Laravel log and follow", "tail -n 400 -f public_html/storage/logs/laravel.log"),
    ("Tail Laravel log",            "tail -n 400 public_html/storage/logs/laravel.log"),
    ("Edit .env",                   "nano public_html/.env"),
    ("Edit nginx allow.conf",       "nano .local/nginx/allow.conf"),
    ("Edit nginx variables.conf",   "nano .local/nginx/variables.conf"),
]


# ── Utility helpers ──
def add(win, y, x, s, attr=0):
    h, w = win.getmaxyx()
    if 0 <= y < h and x < w:
        win.addnstr(y, x, s, max(0, w - x - 1), attr)


def build_common(base, remote):
    return f"{base} -t {shlex.quote(remote + ' ; exec $SHELL -l')}"
