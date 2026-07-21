import subprocess
import sys
import venv
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
VENV_DIR = APP_DIR / "venv"
REQUIREMENTS = APP_DIR / "requirements.txt"
REQUIREMENTS_AI = APP_DIR / "requirements-ai.txt"

IS_WINDOWS = sys.platform == "win32"


def _venv_bin(*parts):
    return VENV_DIR / ("Scripts" if IS_WINDOWS else "bin") / parts[0]


def banner(msg):
    print(f"\033[36m[NETZUNAMI]\033[0m {msg}")


def pip_install(*args):
    subprocess.check_call([str(_venv_bin("pip")), "install", *args])


def ensure_venv_and_package():
    first_run = not _venv_bin("python").exists()
    package_installed = _venv_bin("netzunami" + (".exe" if IS_WINDOWS else "")).exists()

    if first_run:
        banner("Prima configurazione in corso...")
        banner(f"Creazione ambiente virtuale in {VENV_DIR}")
        venv.create(VENV_DIR, with_pip=True, clear=False)

    if first_run or not package_installed:
        banner("Installazione dipendenze...")
        pip_install("-r", str(REQUIREMENTS))
        banner("Installazione netzunami...")
        pip_install("-e", str(APP_DIR))
        if first_run:
            banner("Pronto! (usa --ai per funzioni AI)")


def main():
    ensure_venv_and_package()

    args = [a for a in sys.argv[1:] if a != "--ai"]

    if "--ai" in sys.argv[1:]:
        banner("Installazione dipendenze AI...")
        pip_install("-r", str(REQUIREMENTS_AI))
        banner("Fatto!")

    if not args:
        subprocess.call([str(_venv_bin("netzunami")), "--help"])
    elif args[0] == "gui":
        subprocess.call([str(_venv_bin("python")), "-m", "netzunami.gui"])
    else:
        subprocess.call([str(_venv_bin("netzunami"))] + args)


if __name__ == "__main__":
    main()
