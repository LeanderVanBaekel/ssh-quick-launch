#!/usr/bin/env python3
"""
SSH quick-launch (kleur, c-submenu, d-download met remote & local browser)

Pijltjes-bug gefixed: ESC is geen quit-toets meer in hoofd- en c-submenu.
"""

import curses, glob, os, posixpath, re, shlex, subprocess, sys, random, string
from collections import defaultdict
from pathlib import Path

# ── 1. Common commands ──────────────────────────────────────────────────────
COMMON_COMMANDS = [
    ("Tail Laravel log and follow", "tail -n 400 -f public_html/storage/logs/laravel.log"),
    ("Tail Laravel log",            "tail -n 400 public_html/storage/logs/laravel.log"),
    ("Edit .env",                   "nano public_html/.env"),
    ("Edit nginx allow.conf",       "nano .local/nginx/allow.conf"),
    ("Edit nginx variables.conf",   "nano .local/nginx/variables.conf"),
]

# ── 2. SSH-config regexen ───────────────────────────────────────────────────
MENU_LINE   = re.compile(r"^\s*#\s*MENU:\s*(.+)$", re.I)
HOST_RE     = re.compile(r"^\s*Host\s+(.+)$", re.I)
HOSTNAME_RE = re.compile(r"^\s*HostName\s+(.+)$", re.I)
USER_RE     = re.compile(r"^\s*User\s+(.+)$", re.I)
INCLUDE_RE  = re.compile(r"^\s*Include\s+(.+)$", re.I)

# ── 3. Kleuren ──────────────────────────────────────────────────────────────
HI, EXIT_NORM, EXIT_SEL, HEADER, SUBHDR = range(1, 6)
def setup_colors():
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(HI,        curses.COLOR_BLACK,  curses.COLOR_CYAN)
    curses.init_pair(EXIT_NORM, curses.COLOR_RED,    -1)
    curses.init_pair(EXIT_SEL,  curses.COLOR_BLACK,  curses.COLOR_RED)
    curses.init_pair(HEADER,    curses.COLOR_GREEN,  -1)
    curses.init_pair(SUBHDR,    curses.COLOR_MAGENTA,-1)

# ── 4. Config parser → hoofdmenu / extras ───────────────────────────────────
def _iter_cfg(start: Path):
    q=[start]
    while q:
        p=q.pop(0)
        try:
            with p.open() as fh:
                for ln in fh:
                    if (m:=INCLUDE_RE.match(ln)):
                        for pat in m.group(1).split():
                            pat=os.path.expandvars(os.path.expanduser(pat))
                            if not os.path.isabs(pat):
                                pat=str((p.parent/pat).resolve())
                            for tgt in glob.glob(pat):
                                q.append(Path(tgt))
                    else:
                        yield ln.rstrip("\n")
        except FileNotFoundError:
            pass

def load_menu(cfg="~/.ssh/config"):
    cfg=Path(os.path.expanduser(cfg))
    if not cfg.exists(): return {},{}
    menu, extras = defaultdict(list), defaultdict(list)
    metas, aliases = [], []
    hostname = user = None
    def flush():
        nonlocal metas, aliases, hostname, user
        if not metas or not aliases:
            metas.clear(); aliases.clear(); return
        host = hostname or aliases[0]
        usr  = f"{user}@" if user else ""
        base = f"ssh {usr}{host}"
        for cat, label, custom in metas:
            if custom:
                full = custom if custom.startswith("ssh ") else f"{base} {custom}"
                extras[base].append((label, full))
            else:
                menu[cat].append((label, base, base))
        metas.clear(); aliases.clear(); hostname = user = None
    for ln in _iter_cfg(cfg):
        if not ln.strip(): flush(); continue
        if (m:=MENU_LINE.match(ln)):
            if aliases: flush()
            parts=[p.strip() for p in m.group(1).split("|")]
            cat=parts[0]; label=parts[1] if len(parts)>=2 else parts[0]
            cmd=parts[2] if len(parts)>=3 else None
            metas.append((cat,label,cmd)); continue
        if ln.lstrip().startswith("#"): continue
        if (m:=HOST_RE.match(ln)): aliases=m.group(1).split()
        elif (m:=HOSTNAME_RE.match(ln)): hostname=m.group(1).strip()
        elif (m:=USER_RE.match(ln)): user=m.group(1).strip()
    flush(); return dict(menu),dict(extras)

ssh_options, host_extras = load_menu()
if not ssh_options:
    sys.exit("Geen menutags gevonden in ~/.ssh/config")

# ── 5. Zoekfilter ───────────────────────────────────────────────────────────
ALIASES={"dev":"develop","stag":"staging","prod":"production"}
terms=[ALIASES.get(a.lower(),a.lower()) for a in sys.argv[1:]]
if terms:
    tmp={}
    for cat,opts in ssh_options.items():
        sel=[o for o in opts if all(t in f"{cat} {o[0]}".lower() for t in terms)]
        if sel: tmp[cat]=sel
    ssh_options=tmp

# ── 6. UI helpers ───────────────────────────────────────────────────────────
EXIT_CAT="Exit (q)"
ssh_options[EXIT_CAT]=[]
HEADER_TXT="SSH Quick-Launch | ↑↓ ←→ ENTER=login  c=cmds  d=download  q=quit"

def add(win,y,x,s,attr=0):
    h,w=win.getmaxyx()
    if 0<=y<h and x<w:
        win.addnstr(y,x,s,max(0,w-x-1),attr)

def build_common(base,remote):
    return f"{base} -t {shlex.quote(remote+' ; exec $SHELL -l')}"

# ── 7. Download-browsers ────────────────────────────────────────────────────
def remote_ls(base, path):
    cmd=f"{base} ls -1pA {shlex.quote(path)}"
    try:
        out=subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL)
        return [l for l in out.splitlines() if l]
    except subprocess.CalledProcessError:
        return []

def local_dirs(path):
    try:
        return sorted([d for d in os.listdir(path) if os.path.isdir(os.path.join(path,d))])
    except PermissionError:
        return []

def local_browser(stdscr, start="."):
    stdscr.keypad(True)
    path=os.path.abspath(start); cache={}; sel=0
    while True:
        if path not in cache: cache[path]=local_dirs(path)
        entries=['./']+(['..'] if path!="/" else [])+cache[path]
        sel=max(0,min(sel,len(entries)-1))
        h,w=stdscr.getmaxyx(); vis=max(1,h-4)
        offset=min(max(sel-vis+1,0), max(len(entries)-vis,0))
        stdscr.clear()
        add(stdscr,0,0,f"Lokale map kiezen: {path}",curses.color_pair(HEADER)|curses.A_BOLD)
        for i,e in enumerate(entries[offset:offset+vis]):
            y=2+i
            attr=curses.color_pair(HI)|curses.A_BOLD if (offset+i)==sel else 0
            add(stdscr,y,2,e + ("/" if e not in ("./","..") else ""),attr)
        add(stdscr,h-1,2,"Enter=open/download  d=download dir  q=terug",curses.A_DIM); stdscr.refresh()
        k=stdscr.getch()
        if k in (ord('q'),ord('Q')): return None
        elif k==curses.KEY_UP:   sel=(sel-1)%len(entries)
        elif k==curses.KEY_DOWN: sel=(sel+1)%len(entries)
        elif k in (curses.KEY_ENTER,10,13):
            ch=entries[sel]
            if ch=='./': return path
            if ch=='..': path=os.path.dirname(path) or '/'; sel=0
            else: path=os.path.join(path,ch); sel=0

def download_browser(stdscr, base):
    setup_colors(); stdscr.keypad(True); curses.curs_set(0)
    path="."; cache={}; sel=0
    while True:
        if path not in cache: cache[path]=remote_ls(base,path)
        entries=list(cache[path]); 
        if path not in ("/","."): entries=['..']+entries
        sel=max(0,min(sel,len(entries)-1))
        h,w=stdscr.getmaxyx(); vis=max(1,h-4); offset=min(max(sel-vis+1,0),max(len(entries)-vis,0))
        stdscr.clear()
        add(stdscr,0,0,f"Download-browser: {base} : {path}",curses.color_pair(HEADER)|curses.A_BOLD)
        for i,e in enumerate(entries[offset:offset+vis]):
            y=2+i
            attr=curses.color_pair(HI)|curses.A_BOLD if (offset+i)==sel else 0
            add(stdscr,y,2,e,attr)
        add(stdscr,h-1,2,"Enter=open/download  q=terug",curses.A_DIM); stdscr.refresh()
        k=stdscr.getch()
        if k in (ord('q'),ord('Q')): return
        elif k==curses.KEY_UP:   sel=(sel-1)%len(entries) if entries else 0
        elif k==curses.KEY_DOWN: sel=(sel+1)%len(entries) if entries else 0
        elif k in (curses.KEY_ENTER,10,13) and entries:
            ch=entries[sel]
            if ch=='..': path=posixpath.dirname(path) or '.'; sel=0
            elif ch.endswith('/'): path=posixpath.join(path,ch.rstrip('/')); sel=0
            else:
                remote_full=f"{base.split()[1]}:{posixpath.join(path,ch)}"
                dest_dir=local_browser(stdscr,'.')
                if not dest_dir: continue
                curses.endwin()
                dest=os.path.join(dest_dir,ch)
                cmd=f"scp {remote_full} {shlex.quote(dest)}"
                print(f"Uitvoeren: {cmd}")
                subprocess.run(cmd,shell=True)
                return
        #── NIEUW: map zippen & downloaden ──
        elif k in (ord('d'), ord('D')) and entries:
            ch = entries[sel]
            if not ch.endswith('/'):
                continue        # alleen mappen

            remote_dir = posixpath.join(path, ch.rstrip('/'))
            dest_dir   = local_browser(stdscr, '.')
            if not dest_dir:
                continue

            curses.endwin()

            rand        = ''.join(random.choices(string.ascii_lowercase+string.digits, k=6))
            remote_zip  = f"/tmp/{os.path.basename(remote_dir)}_{rand}.zip"
            host        = base.split()[1]

            cmd_zip = f"{base} zip -r {shlex.quote(remote_zip)} {shlex.quote(remote_dir)}"
            cmd_scp = f"scp {host}:{remote_zip} {shlex.quote(dest_dir)}"
            cmd_rm  = f"{base} rm {shlex.quote(remote_zip)}"

            print(f"\n[1/3] Remote zippen:\n  {cmd_zip}")
            subprocess.run(cmd_zip, shell=True)

            print(f"\n[2/3] Downloaden:\n  {cmd_scp}")
            subprocess.run(cmd_scp, shell=True)

            print(f"\n[3/3] Opruimen:\n  {cmd_rm}")
            subprocess.run(cmd_rm, shell=True)

            input("\nKlaar! Druk op Enter om terug te keren…")
            return

# ── 8. c-submenu ───────────────────────────────────────────────────────────
def command_menu(stdscr, base):
    stdscr.keypad(True)               # ■■■ pijltjes werken
    custom = host_extras.get(base, [])
    items = [("Login shell", base, False)]
    if custom:
        items.append(("── Custom commands ──", None, True))
        items.extend([(lbl, cmd, False) for lbl, cmd in custom])
    items.append(("── Common commands ──", None, True))
    items.extend([(lbl, build_common(base, r), False) for lbl, r in COMMON_COMMANDS])

    # eerste selecteerbare regel
    sel = next(i for i, t in enumerate(items) if not t[2])

    while True:
        stdscr.clear()
        add(stdscr, 0, 0, f"{HEADER_TXT}  —  {base}",
            curses.color_pair(HEADER) | curses.A_BOLD)
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
        elif k in (curses.KEY_ENTER, 10, 13):
            curses.endwin()
            subprocess.run(items[sel][1], shell=True)
            return True

# ── 9. Hoofdmenu ────────────────────────────────────────────────────────────
def main_menu(stdscr):
    curses.curs_set(0); setup_colors(); stdscr.keypad(True)
    cats=list(ssh_options.keys())
    sel_cat=0; sel_opt=[0]*len(cats); offset=0; rows=3
    while True:
        stdscr.clear()
        H,W=stdscr.getmaxyx(); vis=max(1,(H-2)//rows)
        if sel_cat<offset: offset=sel_cat
        elif sel_cat>=offset+vis: offset=sel_cat-vis+1
        add(stdscr,0,0,HEADER_TXT,curses.color_pair(HEADER)|curses.A_BOLD)
        for idx in range(offset,min(offset+vis,len(cats))):
            cat=cats[idx]; y=2+(idx-offset)*rows
            if cat==EXIT_CAT:
                add(stdscr,y,0,cat,curses.color_pair(EXIT_SEL) if idx==sel_cat else curses.color_pair(EXIT_NORM))
            else:
                attr=curses.color_pair(HI)|curses.A_BOLD if idx==sel_cat else curses.color_pair(HEADER)|curses.A_BOLD
                add(stdscr,y,0,cat,attr)
            x=4
            for oidx,(lbl,_,_) in enumerate(ssh_options[cat]):
                opt_attr=curses.color_pair(HI)|curses.A_BOLD if (idx==sel_cat and oidx==sel_opt[idx]) else 0
                add(stdscr,y+1,x,lbl,opt_attr); x+=len(lbl)+3
        stdscr.refresh()
        k=stdscr.getch()
        if k in (ord('q'),ord('Q')): break
        elif k==curses.KEY_UP:   sel_cat=(sel_cat-1)%len(cats)
        elif k==curses.KEY_DOWN: sel_cat=(sel_cat+1)%len(cats)
        elif k==curses.KEY_LEFT and ssh_options[cats[sel_cat]]:
            sel_opt[sel_cat]=(sel_opt[sel_cat]-1)%len(ssh_options[cats[sel_cat]])
        elif k==curses.KEY_RIGHT and ssh_options[cats[sel_cat]]:
            sel_opt[sel_cat]=(sel_opt[sel_cat]+1)%len(ssh_options[cats[sel_cat]])
        elif k in (ord('c'),ord('C')) and cats[sel_cat]!=EXIT_CAT:
            base=ssh_options[cats[sel_cat]][sel_opt[sel_cat]][2]
            if command_menu(stdscr,base): return
        elif k in (ord('d'),ord('D')) and cats[sel_cat]!=EXIT_CAT:
            base=ssh_options[cats[sel_cat]][sel_opt[sel_cat]][2]
            download_browser(stdscr,base); return
        elif k in (curses.KEY_ENTER,10,13):
            if cats[sel_cat]==EXIT_CAT: break
            cmd=ssh_options[cats[sel_cat]][sel_opt[sel_cat]][1]
            curses.endwin(); subprocess.run(cmd,shell=True); return

# ── 10. Start ───────────────────────────────────────────────────────────────
def main():
    real=[c for c in ssh_options if c!=EXIT_CAT]
    if len(real)==1 and len(ssh_options[real[0]])==1:
        base=ssh_options[real[0]][0][2]
        curses.wrapper(lambda s:(setup_colors(),s.keypad(True),command_menu(s,base)))
    else:
        curses.wrapper(main_menu)

if __name__=="__main__":
    main()
