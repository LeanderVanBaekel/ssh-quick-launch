import curses
import subprocess

from .ui import (
    add,
    setup_colors,
    build_common,
    COMMON_COMMANDS,
    HI,
    EXIT_NORM,
    EXIT_SEL,
    HEADER,
    SUBHDR,
)
from .browsers import download_browser, upload_browser


def command_menu(stdscr, base, host_extras, header_txt, updater=None):
    stdscr.keypad(True)
    custom = host_extras.get(base, [])
    items = [("Login shell", base, False)]
    if custom:
        items.append(("── Custom commands ──", None, True))
        items.extend([(lbl, cmd, False) for lbl, cmd in custom])
    items.append(("── Common commands ──", None, True))
    items.extend([(lbl, build_common(base, r), False) for lbl, r in COMMON_COMMANDS])

    sel = next(i for i, t in enumerate(items) if not t[2])
    while True:
        stdscr.clear()
        update = updater and updater.done() and updater.result
        add(stdscr, 0, 0, f"{header_txt}  —  {base}", curses.color_pair(HEADER) | curses.A_BOLD)
        if update:
            add(stdscr, 1, 0, "⇪  Update beschikbaar. Ga terug naar hoofdmenu om bij te werken.", curses.A_BOLD)
            y = 3
        else:
            y = 2
        for i, (lbl, _, hdr) in enumerate(items):
            if hdr:
                add(stdscr, y, 2, lbl, curses.color_pair(SUBHDR) | curses.A_BOLD)
            else:
                attr = curses.color_pair(HI) | curses.A_BOLD if i == sel else 0
                add(stdscr, y, 4, lbl, attr)
            y += 1
        add(stdscr, y + 1, 4, "Esc/Q terug", curses.A_DIM)
        stdscr.refresh()

        k = stdscr.getch()
        if k in (27, ord('q'), ord('Q')):
            return False
        elif k == curses.KEY_UP:
            while True:
                sel = (sel - 1) % len(items)
                if not items[sel][2]:
                    break
        elif k == curses.KEY_DOWN:
            while True:
                sel = (sel + 1) % len(items)
                if not items[sel][2]:
                    break
        elif k in (ord('d'), ord('D')):
            download_browser(stdscr, base)
        elif k in (ord('u'), ord('U')):
            upload_browser(stdscr, base)
        elif k in (curses.KEY_ENTER, 10, 13):
            curses.endwin()
            subprocess.run(items[sel][1], shell=True)
            return True


UPDATE_CAT = "Update (⇪)"


def main_menu(stdscr, ssh_options, host_extras, header_txt, exit_cat, updater=None):
    curses.curs_set(0)
    setup_colors()
    stdscr.keypad(True)
    cats = list(ssh_options.keys())
    sel_cat = 0
    sel_opt = [0] * len(cats)
    offset = 0
    rows = 3
    update_added = False
    while True:
        stdscr.clear()
        update_ready = updater and updater.done() and updater.result
        if update_ready and not update_added:
            cats.insert(0, UPDATE_CAT)
            ssh_options[UPDATE_CAT] = [("Nu bijwerken", "update", "update")]
            sel_opt.insert(0, 0)
            update_added = True
        H, W = stdscr.getmaxyx()
        start_y = 3 if update_ready else 2
        vis = max(1, (H - start_y) // rows)
        if sel_cat < offset:
            offset = sel_cat
        elif sel_cat >= offset + vis:
            offset = sel_cat - vis + 1
        add(stdscr, 0, 0, header_txt, curses.color_pair(HEADER) | curses.A_BOLD)
        if update_ready:
            add(stdscr, 1, 0, "⇪  Update beschikbaar", curses.A_BOLD)
        for idx in range(offset, min(offset + vis, len(cats))):
            cat = cats[idx]
            y = start_y + (idx - offset) * rows
            if cat == exit_cat:
                add(
                    stdscr,
                    y,
                    0,
                    cat,
                    curses.color_pair(EXIT_SEL) if idx == sel_cat else curses.color_pair(EXIT_NORM),
                )
            else:
                attr = (
                    curses.color_pair(HI) | curses.A_BOLD if idx == sel_cat else curses.color_pair(HEADER) | curses.A_BOLD
                )
                add(stdscr, y, 0, cat, attr)
            x = 4
            for oidx, (lbl, _, _) in enumerate(ssh_options[cat]):
                opt_attr = curses.color_pair(HI) | curses.A_BOLD if (idx == sel_cat and oidx == sel_opt[idx]) else 0
                add(stdscr, y + 1, x, lbl, opt_attr)
                x += len(lbl) + 3
        stdscr.refresh()
        k = stdscr.getch()
        if k in (ord('q'), ord('Q')):
            break
        elif k == curses.KEY_UP:
            sel_cat = (sel_cat - 1) % len(cats)
        elif k == curses.KEY_DOWN:
            sel_cat = (sel_cat + 1) % len(cats)
        elif k == curses.KEY_LEFT and ssh_options[cats[sel_cat]]:
            sel_opt[sel_cat] = (sel_opt[sel_cat] - 1) % len(ssh_options[cats[sel_cat]])
        elif k == curses.KEY_RIGHT and ssh_options[cats[sel_cat]]:
            sel_opt[sel_cat] = (sel_opt[sel_cat] + 1) % len(ssh_options[cats[sel_cat]])
        elif k in (ord('c'), ord('C')) and cats[sel_cat] not in (exit_cat, UPDATE_CAT):
            base = ssh_options[cats[sel_cat]][sel_opt[sel_cat]][2]
            if command_menu(stdscr, base, host_extras, header_txt, updater):
                return
        elif k in (ord('d'), ord('D')) and cats[sel_cat] not in (exit_cat, UPDATE_CAT):
            base = ssh_options[cats[sel_cat]][sel_opt[sel_cat]][2]
            download_browser(stdscr, base)
            return
        elif k in (ord('u'), ord('U')) and cats[sel_cat] not in (exit_cat, UPDATE_CAT):
            base = ssh_options[cats[sel_cat]][sel_opt[sel_cat]][2]
            upload_browser(stdscr, base)
            return
        elif k in (curses.KEY_ENTER, 10, 13):
            if cats[sel_cat] == exit_cat:
                break
            if cats[sel_cat] == UPDATE_CAT:
                curses.endwin()
                from .cli import self_update
                self_update()
                return
            cmd = ssh_options[cats[sel_cat]][sel_opt[sel_cat]][1]
            curses.endwin()
            subprocess.run(cmd, shell=True)
            return
