"""Configuration loading and validation."""

from dataclasses import dataclass
import os

from dotenv import load_dotenv


@dataclass(frozen=True, slots=True)
class Settings:
    token: str
    owner_id: int
    script_timeout_seconds: float = 300.0
    max_script_actions: int = 1000
    database_path: str = "data/exe.sqlite3"
    enable_members_intent: bool = False


def _positive_float(name: str, default: float) -> float:
    raw = os.getenv(name, str(default))
    try:
        value = float(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a number") from exc
    if not 0 < value <= 300:
        raise RuntimeError(f"{name} must be greater than 0 and at most 300")
    return value


def _positive_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc
    if not 1 <= value <= 1000:
        raise RuntimeError(f"{name} must be between 1 and 1000")
    return value


def _boolean(name: str, default: bool = False) -> bool:
    raw = os.getenv(name, str(default)).strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    raise RuntimeError(f"{name} must be a boolean (true/false)")


def load_settings() -> Settings:
    load_dotenv()
    token = os.getenv("DISCORD_TOKEN", "").strip()
    if not token or token == "replace_me":
        raise RuntimeError("Set DISCORD_TOKEN in your local .env file")

    try:
        owner_id = int(os.environ["OWNER_ID"])
    except (KeyError, ValueError) as exc:
        raise RuntimeError("Set OWNER_ID to your numeric Discord user ID") from exc
    if owner_id <= 0:
        raise RuntimeError("OWNER_ID must be a positive Discord user ID")

    database_path = os.getenv("DATABASE_PATH", "data/exe.sqlite3").strip()
    if not database_path:
        raise RuntimeError("DATABASE_PATH must not be empty")

    return Settings(
        token=token,
        owner_id=owner_id,
        script_timeout_seconds=_positive_float("SCRIPT_TIMEOUT_SECONDS", 300.0),
        max_script_actions=_positive_int("MAX_SCRIPT_ACTIONS", 1000),
        database_path=database_path,
        enable_members_intent=_boolean("ENABLE_MEMBERS_INTENT", False),
    )
