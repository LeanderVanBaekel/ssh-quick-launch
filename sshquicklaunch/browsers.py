import curses
import os
import posixpath
import random
import shlex
import string
import subprocess

from .ui import add, setup_colors, HI, HEADER


def remote_ls(base, path):
    cmd = f"{base} ls -1pA {shlex.quote(path)}"
    try:
        out = subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL)
        return [l for l in out.splitlines() if l]
    except subprocess.CalledProcessError:
        return []


def local_dirs(path):
    try:
        return sorted([d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))])
    except PermissionError:
        return []


def local_browser(stdscr, start="."):
    stdscr.keypad(True)
    path = os.path.abspath(start)
    cache = {}
    sel = 0
    while True:
        if path not in cache:
            cache[path] = local_dirs(path)
        entries = ['./'] + (['..'] if path != '/' else []) + cache[path]
        sel = max(0, min(sel, len(entries) - 1))
        h, w = stdscr.getmaxyx(); vis = max(1, h - 4)
        offset = min(max(sel - vis + 1, 0), max(len(entries) - vis, 0))
        stdscr.clear()
        add(stdscr, 0, 0, f"Lokale map kiezen: {path}", curses.color_pair(HEADER) | curses.A_BOLD)
        for i, e in enumerate(entries[offset:offset + vis]):
            y = 2 + i
            attr = curses.color_pair(HI) | curses.A_BOLD if (offset + i) == sel else 0
            add(stdscr, y, 2, e + ('/' if e not in ('./', '..') else ''), attr)
        add(stdscr, h - 1, 2, "Enter=open/download  d=download dir  q=terug", curses.A_DIM)
        stdscr.refresh()
        k = stdscr.getch()
        if k in (ord('q'), ord('Q')):
            return None
        elif k == curses.KEY_UP:
            sel = (sel - 1) % len(entries)
        elif k == curses.KEY_DOWN:
            sel = (sel + 1) % len(entries)
        elif k in (curses.KEY_ENTER, 10, 13):
            ch = entries[sel]
            if ch == './':
                return path
            if ch == '..':
                path = os.path.dirname(path) or '/'; sel = 0
            else:
                path = os.path.join(path, ch); sel = 0


def download_browser(stdscr, base):
    setup_colors(); stdscr.keypad(True); curses.curs_set(0)
    path = '.'
    cache = {}
    sel = 0
    while True:
        if path not in cache:
            cache[path] = remote_ls(base, path)
        entries = list(cache[path])
        if path not in ('/', '.'):
            entries = ['..'] + entries
        sel = max(0, min(sel, len(entries) - 1))
        h, w = stdscr.getmaxyx(); vis = max(1, h - 4)
        offset = min(max(sel - vis + 1, 0), max(len(entries) - vis, 0))
        stdscr.clear()
        add(stdscr, 0, 0, f"Download-browser: {base} : {path}", curses.color_pair(HEADER) | curses.A_BOLD)
        for i, e in enumerate(entries[offset:offset + vis]):
            y = 2 + i
            attr = curses.color_pair(HI) | curses.A_BOLD if (offset + i) == sel else 0
            add(stdscr, y, 2, e, attr)
        add(stdscr, h - 1, 2, "Enter=open/download  q=terug", curses.A_DIM)
        stdscr.refresh()
        k = stdscr.getch()
        if k in (ord('q'), ord('Q')):
            return
        elif k == curses.KEY_UP:
            sel = (sel - 1) % len(entries) if entries else 0
        elif k == curses.KEY_DOWN:
            sel = (sel + 1) % len(entries) if entries else 0
        elif k in (curses.KEY_ENTER, 10, 13) and entries:
            ch = entries[sel]
            if ch == '..':
                path = posixpath.dirname(path) or '.'; sel = 0
            elif ch.endswith('/'):
                path = posixpath.join(path, ch.rstrip('/')); sel = 0
            else:
                remote_full = f"{base.split()[1]}:{posixpath.join(path, ch)}"
                dest_dir = local_browser(stdscr, '.')
                if not dest_dir:
                    continue
                curses.endwin()
                dest = os.path.join(dest_dir, ch)
                cmd = f"scp {remote_full} {shlex.quote(dest)}"
                print(f"Uitvoeren: {cmd}")
                subprocess.run(cmd, shell=True)
                return
        elif k in (ord('d'), ord('D')) and entries:
            ch = entries[sel]
            if not ch.endswith('/'):
                continue
            remote_dir = posixpath.join(path, ch.rstrip('/'))
            dest_dir = local_browser(stdscr, '.')
            if not dest_dir:
                continue
            curses.endwin()
            rand = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
            remote_zip = f"/tmp/{os.path.basename(remote_dir)}_{rand}.zip"
            host = base.split()[1]
            cmd_zip = f"{base} zip -r {shlex.quote(remote_zip)} {shlex.quote(remote_dir)}"
            cmd_scp = f"scp {host}:{remote_zip} {shlex.quote(dest_dir)}"
            cmd_rm = f"{base} rm {shlex.quote(remote_zip)}"
            print(f"\n[1/3] Remote zippen:\n  {cmd_zip}")
            subprocess.run(cmd_zip, shell=True)
            print(f"\n[2/3] Downloaden:\n  {cmd_scp}")
            subprocess.run(cmd_scp, shell=True)
            print(f"\n[3/3] Opruimen:\n  {cmd_rm}")
            subprocess.run(cmd_rm, shell=True)
            input("\nKlaar! Druk op Enter om terug te keren…")
            return


def remote_dir_browser(stdscr, base, start='.'):
    stdscr.keypad(True)
    path = start
    cache = {}
    sel = 0
    while True:
        if path not in cache:
            cache[path] = [d for d in remote_ls(base, path) if d.endswith('/')]
        entries = ['./'] + (['..'] if path not in ('/', '.') else []) + cache[path]
        sel = max(0, min(sel, len(entries) - 1))
        h, w = stdscr.getmaxyx(); vis = max(1, h - 4)
        offset = min(max(sel - vis + 1, 0), max(len(entries) - vis, 0))
        stdscr.clear()
        add(stdscr, 0, 0, f"Remote map kiezen: {path}", curses.color_pair(HEADER) | curses.A_BOLD)
        for i, e in enumerate(entries[offset:offset + vis]):
            y = 2 + i
            attr = curses.color_pair(HI) | curses.A_BOLD if (offset + i) == sel else 0
            add(stdscr, y, 2, e, attr)
        add(stdscr, h - 1, 2, "Enter=open/kies  q=terug", curses.A_DIM)
        stdscr.refresh()
        k = stdscr.getch()
        if k in (ord('q'), ord('Q')):
            return None
        elif k == curses.KEY_UP:
            sel = (sel - 1) % len(entries)
        elif k == curses.KEY_DOWN:
            sel = (sel + 1) % len(entries)
        elif k in (curses.KEY_ENTER, 10, 13):
            ch = entries[sel]
            if ch == './':
                return path
            if ch == '..':
                path = posixpath.dirname(path) or '.'; sel = 0
            else:
                path = posixpath.join(path, ch.rstrip('/')); sel = 0


def upload_browser(stdscr, base):
    setup_colors(); stdscr.keypad(True); curses.curs_set(0)
    path = '.'
    cache = {}
    sel = 0
    while True:
        if path not in cache:
            try:
                items = sorted(os.listdir(path))
                cache[path] = [i + ('/' if os.path.isdir(os.path.join(path, i)) else '') for i in items]
            except PermissionError:
                cache[path] = []
        entries = list(cache[path])
        if path not in ('/', '.'):
            entries = ['..'] + entries
        sel = max(0, min(sel, len(entries) - 1))
        h, w = stdscr.getmaxyx(); vis = max(1, h - 4)
        offset = min(max(sel - vis + 1, 0), max(len(entries) - vis, 0))
        stdscr.clear()
        add(stdscr, 0, 0, f"Upload-browser: {base} : {path}", curses.color_pair(HEADER) | curses.A_BOLD)
        for i, e in enumerate(entries[offset:offset + vis]):
            y = 2 + i
            attr = curses.color_pair(HI) | curses.A_BOLD if (offset + i) == sel else 0
            add(stdscr, y, 2, e, attr)
        add(stdscr, h - 1, 2, "Enter=open/upload  d=upload dir  q=terug", curses.A_DIM)
        stdscr.refresh()
        k = stdscr.getch()
        if k in (ord('q'), ord('Q')):
            return
        elif k == curses.KEY_UP:
            sel = (sel - 1) % len(entries) if entries else 0
        elif k == curses.KEY_DOWN:
            sel = (sel + 1) % len(entries) if entries else 0
        elif k in (curses.KEY_ENTER, 10, 13) and entries:
            ch = entries[sel]
            if ch == '..':
                path = os.path.dirname(path) or '/'; sel = 0
            elif ch.endswith('/'):
                path = os.path.join(path, ch.rstrip('/')); sel = 0
            else:
                local_full = os.path.join(path, ch)
                dest_dir = remote_dir_browser(stdscr, base, '.')
                if not dest_dir:
                    continue
                curses.endwin()
                dest = f"{base.split()[1]}:{posixpath.join(dest_dir, ch)}"
                cmd = f"scp {shlex.quote(local_full)} {dest}"
                print(f"Uitvoeren: {cmd}")
                subprocess.run(cmd, shell=True)
                return
        elif k in (ord('d'), ord('D')) and entries:
            ch = entries[sel]
            if not ch.endswith('/'):
                continue
            local_dir = os.path.join(path, ch.rstrip('/'))
            dest_dir = remote_dir_browser(stdscr, base, '.')
            if not dest_dir:
                continue
            curses.endwin()
            rand = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
            local_zip = f"/tmp/{os.path.basename(local_dir)}_{rand}.zip"
            remote_zip = posixpath.join(dest_dir, os.path.basename(local_zip))
            host = base.split()[1]
            cmd_zip = f"zip -r {shlex.quote(local_zip)} {shlex.quote(local_dir)}"
            cmd_scp = f"scp {shlex.quote(local_zip)} {host}:{shlex.quote(remote_zip)}"
            cmd_rm = f"rm {shlex.quote(local_zip)}"
            print(f"\n[1/3] Lokaal zippen:\n  {cmd_zip}")
            subprocess.run(cmd_zip, shell=True)
            print(f"\n[2/3] Uploaden:\n  {cmd_scp}")
            subprocess.run(cmd_scp, shell=True)
            print(f"\n[3/3] Opruimen:\n  {cmd_rm}")
            subprocess.run(cmd_rm, shell=True)
            input("\nKlaar! Druk op Enter om terug te keren…")
            return
