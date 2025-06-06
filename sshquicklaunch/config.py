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


def config_has_menu(cfg: str = "~/.ssh/config") -> bool:
    """Return True if the config file contains any ``# MENU:`` tags."""
    path = Path(os.path.expanduser(cfg))
    if not path.exists():
        return False
    try:
        with path.open() as fh:
            return any(MENU_LINE.match(ln) for ln in fh)
    except OSError:
        return False


def format_config(cfg: str = "~/.ssh/config") -> None:
    """Reformat the SSH config so ``load_menu`` can parse it.

    A backup named ``config.backup`` will be created in the same directory.
    """
    path = Path(os.path.expanduser(cfg))
    if not path.exists():
        raise FileNotFoundError(cfg)
    backup = path.with_name("config.backup")
    with path.open() as fh:
        lines = fh.readlines()
    # create backup
    with backup.open("w") as fh:
        fh.writelines(lines)

    new_lines = []
    i = 0
    menu_lines: list[str] = []
    while i < len(lines):
        ln = lines[i]
        if MENU_LINE.match(ln):
            menu_lines.append(ln.rstrip("\n"))
            i += 1
            continue
        m = HOST_RE.match(ln)
        if not m:
            new_lines.extend(l + "\n" for l in menu_lines)
            menu_lines.clear()
            new_lines.append(ln)
            i += 1
            continue
        aliases = m.group(1).split()
        block = []
        i += 1
        while i < len(lines) and lines[i].strip() and not HOST_RE.match(lines[i]) and not MENU_LINE.match(lines[i]):
            block.append(lines[i].rstrip("\n"))
            i += 1
        while i < len(lines) and not lines[i].strip():
            i += 1
        for alias in aliases:
            new_lines.extend(l + "\n" for l in menu_lines)
            new_lines.append(f"Host {alias}\n")
            new_lines.extend(l + "\n" for l in block)
            new_lines.append("\n")
        menu_lines.clear()
    with path.open("w") as fh:
        fh.writelines(new_lines)


def add_connection(cfg: str = "~/.ssh/config") -> None:
    """Interactively append a new connection to the SSH config."""
    path = Path(os.path.expanduser(cfg))
    cat = input("Categorie: ").strip() or "Default"
    alias = input("Alias (Host): ").strip()
    host = input("HostName: ").strip()
    user = input("User (optioneel): ").strip()
    label = input("Label (enter voor alias): ").strip() or alias
    custom = input("Custom command (optioneel): ").strip()

    menu_line = f"# MENU: {cat} | {label}"
    if custom:
        menu_line += f" | {custom}"
    parts = [menu_line, f"Host {alias}", f"    HostName {host}"]
    if user:
        parts.append(f"    User {user}")
    parts.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as fh:
        for l in parts:
            fh.write(l + "\n")

