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
        print("Bot is already running.")
        return
    if not PYTHON.exists():
        print("[ERROR] Python environment not found. Run start_bot.bat or start_bot.sh first.")
        return
    if not ENV_PATH.exists() or not read_env().get("DISCORD_TOKEN") or not read_env().get("OWNER_ID"):
        print("[ERROR] Configure the token and owner first with set_token and set_owner.")
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
            print(f"Bot started (PID {proc.pid}). Logs: bot.log")
        else:
            print("The bot exited during startup. Check bot.log.")
    except (OSError, psutil.Error) as exc:
        print(f"[ERROR] Could not start the bot: {exc}")


def stop() -> None:
    proc = running_process()
    if proc is None:
        print("The bot is not running.")
        return
    try:
        for child in proc.children(recursive=True):
            child.terminate()
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except psutil.TimeoutExpired:
            proc.kill()
        print("Bot stopped.")
    except psutil.Error as exc:
        print(f"[ERROR] Could not stop the bot: {exc}")
    finally:
        PID_PATH.unlink(missing_ok=True)
        START_PATH.unlink(missing_ok=True)


def uptime() -> None:
    proc = running_process()
    if proc is None:
        print("Bot stopped — uptime: 0.")
        return
    seconds = max(0, int(time.time() - proc.create_time()))
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    print(f"Uptime: {days}d {hours}h {minutes}m {secs}s (PID {proc.pid}).")


def status() -> None:
    proc = running_process()
    if proc is None:
        print("Status: STOPPED")
    else:
        print(f"Status: RUNNING | PID {proc.pid} | RAM {proc.memory_info().rss / 1048576:.1f} MB")
        uptime()


def configure_token() -> None:
    value = getpass.getpass("New Discord bot token (hidden input): ").strip()
    if value:
        set_env("DISCORD_TOKEN", value)
        print("Token saved to .env. Restart the bot to apply it.")


def configure_owner() -> None:
    value = input("Numeric Discord user ID of the owner: ").strip()
    if not value.isdigit() or int(value) <= 0:
        print("[ERROR] The ID must contain digits only.")
        return
    set_env("OWNER_ID", value)
    print("Owner ID saved to .env. Restart the bot to apply it.")


def show_help() -> None:
    print("""
.exe Control Panel commands
  start       Start the bot in the background
  stop        Stop the bot
  restart     Restart the bot
  status      Status and RAM usage
  uptime      Time since startup
  set_token   Configure the Discord token (hidden input)
  set_owner   Configure the owner's Discord ID
  logs        Show the last 30 lines of bot.log
  help        Show this help
  exit        Close the panel (the bot keeps running)
""")


def main() -> None:
    print("================================")
    print("       .exe Control Panel")
    print("================================")
    print(f"Python: {sys.version.split()[0]} | Platform: {sys.platform}")
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
                print("\n".join(lines[-30:]) or "No log entries.")
            else:
                print("bot.log does not exist yet.")
        elif command in actions:
            actions[command]()
        elif command:
            print('Unknown command. Type "help".')


if __name__ == "__main__":
    main()
