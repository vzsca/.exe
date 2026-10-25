"""Small cross-platform control panel for .exe."""

import getpass
import os
import subprocess
import sys
import time
from pathlib import Path

import psutil

ROOT = Path(__file__).resolve().parent
ENV_PATH = ROOT / ".env"
PID_PATH = ROOT / "bot.pid"
START_PATH = ROOT / "bot.started"
LOG_PATH = ROOT / "bot.log"
IS_WINDOWS = os.name == "nt"
PYTHON = ROOT / ("venv/Scripts/python.exe" if IS_WINDOWS else "venv/bin/python")


def read_env() -> dict[str, str]:
    values = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip()
    return values


def set_env(key: str, value: str) -> None:
    lines = ENV_PATH.read_text(encoding="utf-8").splitlines() if ENV_PATH.exists() else []
    prefix = key + "="
    for i, line in enumerate(lines):
        if line.startswith(prefix):
            lines[i] = prefix + value
            break
    else:
        lines.append(prefix + value)
    temp = ENV_PATH.with_suffix(".env.tmp")
    temp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if not IS_WINDOWS:
        temp.chmod(0o600)
    temp.replace(ENV_PATH)
    if not IS_WINDOWS:
        ENV_PATH.chmod(0o600)


def running_process():
    try:
        pid = int(PID_PATH.read_text(encoding="utf-8").strip())
        proc = psutil.Process(pid)
        started = float(START_PATH.read_text(encoding="utf-8").strip())
        if not proc.is_running() or proc.status() == psutil.STATUS_ZOMBIE:
            raise psutil.NoSuchProcess(pid)
        if abs(proc.create_time() - started) > 2:
            raise psutil.NoSuchProcess(pid)
        return proc
    except (OSError, ValueError, psutil.Error):
        PID_PATH.unlink(missing_ok=True)
        START_PATH.unlink(missing_ok=True)
        return None


def start() -> None:
    if running_process():
        print("Bot déjà démarré.")
        return
    if not PYTHON.exists():
        print("[ERREUR] Environnement Python absent. Lance start_bot.bat ou start_bot.sh.")
        return
    if not ENV_PATH.exists() or not read_env().get("DISCORD_TOKEN") or not read_env().get("OWNER_ID"):
        print("[ERREUR] Configure d'abord le token et l'owner avec set_token et set_owner.")
        return
    LOG_PATH.touch(exist_ok=True)
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    try:
        with LOG_PATH.open("a", encoding="utf-8") as log:
            options = {"cwd": ROOT, "env": env, "stdin": subprocess.DEVNULL, "stdout": log, "stderr": log}
            if IS_WINDOWS:
                options["creationflags"] = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS
            else:
                options["start_new_session"] = True
            proc = subprocess.Popen([str(PYTHON), "-m", "exe_bot"], **options)
        time.sleep(1.5)
        child = psutil.Process(proc.pid)
        if child.is_running() and child.status() != psutil.STATUS_ZOMBIE:
            PID_PATH.write_text(str(proc.pid), encoding="utf-8")
            START_PATH.write_text(str(child.create_time()), encoding="utf-8")
            print(f"Bot démarré (PID {proc.pid}). Logs : bot.log")
        else:
            print("Le bot s'est arrêté au démarrage. Consulte bot.log.")
    except (OSError, psutil.Error) as exc:
        print(f"[ERREUR] Démarrage impossible : {exc}")


def stop() -> None:
    proc = running_process()
    if proc is None:
        print("Le bot n'est pas démarré.")
        return
    try:
        for child in proc.children(recursive=True):
            child.terminate()
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except psutil.TimeoutExpired:
            proc.kill()
        print("Bot arrêté.")
    except psutil.Error as exc:
        print(f"[ERREUR] Arrêt impossible : {exc}")
    finally:
        PID_PATH.unlink(missing_ok=True)
        START_PATH.unlink(missing_ok=True)


def uptime() -> None:
    proc = running_process()
    if proc is None:
        print("Bot arrêté — uptime : 0.")
        return
    seconds = max(0, int(time.time() - proc.create_time()))
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    print(f"Uptime : {days}j {hours}h {minutes}min {secs}s (PID {proc.pid}).")


def status() -> None:
    proc = running_process()
    if proc is None:
        print("État : ARRÊTÉ")
    else:
        print(f"État : ACTIF | PID {proc.pid} | RAM {proc.memory_info().rss / 1048576:.1f} Mo")
        uptime()


def configure_token() -> None:
    value = getpass.getpass("Nouveau token Discord (saisie masquée) : ").strip()
    if value:
        set_env("DISCORD_TOKEN", value)
        print("Token enregistré dans .env. Redémarre le bot pour l'appliquer.")


def configure_owner() -> None:
    value = input("ID Discord numérique du propriétaire : ").strip()
    if not value.isdigit() or int(value) <= 0:
        print("[ERREUR] L'ID doit contenir uniquement des chiffres.")
        return
    set_env("OWNER_ID", value)
    print("Owner enregistré dans .env. Redémarre le bot pour l'appliquer.")


def show_help() -> None:
    print("""
Commandes du panel .exe
  start       Démarrer le bot en arrière-plan
  stop        Arrêter le bot
  restart     Redémarrer le bot
  status      État et utilisation RAM
  uptime      Temps depuis le démarrage
  set_token   Configurer le token Discord (masqué)
  set_owner   Configurer l'ID Discord propriétaire
  logs        Afficher les 30 dernières lignes de bot.log
  help        Afficher cette aide
  exit        Fermer le panel (le bot reste actif)
""")


def main() -> None:
    print("================================")
    print("       .exe Control Panel")
    print("================================")
    print(f"Python : {sys.version.split()[0]} | Plateforme : {sys.platform}")
    show_help()
    actions = {"start": start, "stop": stop, "status": status, "uptime": uptime,
               "set_token": configure_token, "set_owner": configure_owner, "help": show_help}
    while True:
        try:
            command = input(".exe> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if command == "exit":
            break
        if command == "restart":
            stop()
            time.sleep(1)
            start()
        elif command == "logs":
            if LOG_PATH.exists():
                lines = LOG_PATH.read_text(encoding="utf-8", errors="replace").splitlines()
                print("\n".join(lines[-30:]) or "Aucun log.")
            else:
                print("bot.log n'existe pas encore.")
        elif command in actions:
            actions[command]()
        elif command:
            print('Commande inconnue. Tape "help".')


if __name__ == "__main__":
    main()
