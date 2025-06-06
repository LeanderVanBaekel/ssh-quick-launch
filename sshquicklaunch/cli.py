import curses
import subprocess
import sys
import threading
from typing import Optional
from pathlib import Path

from .config import (
    load_menu,
    config_has_menu,
    format_config,
    add_connection,
)
from .menu import command_menu, main_menu
from .ui import setup_colors

ROOT = Path(__file__).resolve().parents[1]


def self_update() -> None:
    print("\u231B  Updating ssh-quick-launch …")
    res = subprocess.run(["git", "-C", str(ROOT), "pull", "--ff-only"])
    sys.exit(res.returncode)


def update_available() -> bool:
    """Check whether a newer revision exists upstream."""
    try:
        subprocess.run(
            ["git", "-C", str(ROOT), "fetch", "--quiet"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        local = subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True
        ).strip()
        remote = subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "@{u}"], text=True
        ).strip()
        return local != remote
    except Exception:
        return False


class AsyncUpdateCheck:
    """Runs update_available() in a separate thread."""

    def __init__(self) -> None:
        self.result: Optional[bool] = None
        self._done = threading.Event()
        self._thread = threading.Thread(target=self._check, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def _check(self) -> None:
        self.result = update_available()
        self._done.set()

    def done(self) -> bool:
        return self._done.is_set()


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    if argv and argv[0] in {"--format-config", "format-config"}:
        format_config()
        print("Config geformatteerd. Backup opgeslagen als 'config.backup'.")
        return 0
    if argv and argv[0] in {"--add", "add"}:
        add_connection()
        print("Connectie toegevoegd aan ~/.ssh/config")
        return 0
    if argv and argv[0] in {"--update", "update", "u"}:
        self_update()

    updater = AsyncUpdateCheck()
    updater.start()
    if argv and argv[0] in {"--version", "-V"}:
        ver = subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], text=True
        ).strip()
        print("ssh-quick-launch git-rev:", ver)
        return 0

    ssh_options, host_extras = load_menu()
    if not ssh_options:
        if config_has_menu():
            sys.exit(
                "Config bevat menutags, maar de structuur wordt niet herkend. "
                "Voer 's --format-config' uit."
            )
        sys.exit("Geen menutags gevonden in ~/.ssh/config")

    ALIASES = {"dev": "develop", "stag": "staging", "prod": "production"}
    terms = [ALIASES.get(a.lower(), a.lower()) for a in argv]
    if terms:
        tmp = {}
        for cat, opts in ssh_options.items():
            sel = [o for o in opts if all(t in f"{cat} {o[0]}".lower() for t in terms)]
            if sel:
                tmp[cat] = sel
        ssh_options = tmp

    EXIT_CAT = "Exit (q)"
    ssh_options[EXIT_CAT] = []
    HEADER_TXT = (
        "SSH Quick-Launch | ↑↓ ←→ ENTER=login  c=cmds  d=download  u=upload  q=quit"
    )

    real = [c for c in ssh_options if c != EXIT_CAT]
    if len(real) == 1 and len(ssh_options[real[0]]) == 1:
        base = ssh_options[real[0]][0][2]
        curses.wrapper(
            lambda s: (setup_colors(), s.keypad(True), command_menu(s, base, host_extras, HEADER_TXT))
        )
    else:
        curses.wrapper(
            lambda s: main_menu(s, ssh_options, host_extras, HEADER_TXT, EXIT_CAT)
        )

    if updater.done() and updater.result:
        print(
            "⇪  Er is een update beschikbaar. Voer 's --update' uit om bij te werken."
        )


if __name__ == "__main__":
    main()
