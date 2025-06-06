import curses
import subprocess
import sys
from pathlib import Path

from .config import load_menu
from .menu import command_menu, main_menu
from .ui import setup_colors

ROOT = Path(__file__).resolve().parents[1]


def self_update() -> None:
    print("\u231B  Updating ssh-quick-launch …")
    res = subprocess.run(["git", "-C", str(ROOT), "pull", "--ff-only"])
    sys.exit(res.returncode)


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    if argv and argv[0] in {"--update", "update", "u"}:
        self_update()
    if argv and argv[0] in {"--version", "-V"}:
        ver = subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], text=True
        ).strip()
        print("ssh-quick-launch git-rev:", ver)
        return 0

    ssh_options, host_extras = load_menu()
    if not ssh_options:
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


if __name__ == "__main__":
    main()
