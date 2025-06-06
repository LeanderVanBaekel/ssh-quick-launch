import glob
import os
import re
from collections import defaultdict
from pathlib import Path

MENU_LINE   = re.compile(r"^\s*#\s*MENU:\s*(.+)$", re.I)
HOST_RE     = re.compile(r"^\s*Host\s+(.+)$", re.I)
HOSTNAME_RE = re.compile(r"^\s*HostName\s+(.+)$", re.I)
USER_RE     = re.compile(r"^\s*User\s+(.+)$", re.I)
INCLUDE_RE  = re.compile(r"^\s*Include\s+(.+)$", re.I)


def _iter_cfg(start: Path):
    q = [start]
    while q:
        p = q.pop(0)
        try:
            with p.open() as fh:
                for ln in fh:
                    if (m := INCLUDE_RE.match(ln)):
                        for pat in m.group(1).split():
                            pat = os.path.expandvars(os.path.expanduser(pat))
                            if not os.path.isabs(pat):
                                pat = str((p.parent / pat).resolve())
                            for tgt in glob.glob(pat):
                                q.append(Path(tgt))
                    else:
                        yield ln.rstrip("\n")
        except FileNotFoundError:
            pass


def load_menu(cfg: str = "~/.ssh/config"):
    cfg = Path(os.path.expanduser(cfg))
    if not cfg.exists():
        return {}, {}
    menu, extras = defaultdict(list), defaultdict(list)
    metas, aliases = [], []
    hostname = user = None

    def flush():
        nonlocal metas, aliases, hostname, user
        if not metas or not aliases:
            metas.clear(); aliases.clear(); return
        host = hostname or aliases[0]
        usr = f"{user}@" if user else ""
        base = f"ssh {usr}{host}"
        for cat, label, custom in metas:
            if custom:
                full = custom if custom.startswith("ssh ") else f"{base} {custom}"
                extras[base].append((label, full))
            else:
                menu[cat].append((label, base, base))
        metas.clear(); aliases.clear(); hostname = user = None

    for ln in _iter_cfg(cfg):
        if not ln.strip():
            flush();
            continue
        if (m := MENU_LINE.match(ln)):
            if aliases:
                flush()
            parts = [p.strip() for p in m.group(1).split("|")]
            cat = parts[0]
            label = parts[1] if len(parts) >= 2 else parts[0]
            cmd = parts[2] if len(parts) >= 3 else None
            metas.append((cat, label, cmd))
            continue
        if ln.lstrip().startswith("#"):
            continue
        if m := HOST_RE.match(ln):
            aliases = m.group(1).split()
        elif m := HOSTNAME_RE.match(ln):
            hostname = m.group(1).strip()
        elif m := USER_RE.match(ln):
            user = m.group(1).strip()
    flush()
    return dict(menu), dict(extras)
