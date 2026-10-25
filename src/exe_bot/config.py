"""Configuration loading and validation."""

from dataclasses import dataclass
import os

from dotenv import load_dotenv


@dataclass(frozen=True, slots=True)
class Settings:
    token: str
    owner_id: int
    whitelist_ids: frozenset[int]
    script_timeout_seconds: float = 5.0
    max_script_actions: int = 20


def _positive_float(name: str, default: float) -> float:
    raw = os.getenv(name, str(default))
    try:
        value = float(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a number") from exc
    if not 0 < value <= 30:
        raise RuntimeError(f"{name} must be greater than 0 and at most 30")
    return value


def _positive_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc
    if not 1 <= value <= 100:
        raise RuntimeError(f"{name} must be between 1 and 100")
    return value


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

    whitelist: set[int] = set()
    for item in os.getenv("WHITELIST_IDS", "").split(","):
        item = item.strip()
        if item:
            try:
                whitelist.add(int(item))
            except ValueError as exc:
                raise RuntimeError("WHITELIST_IDS must be comma-separated numeric IDs") from exc

    return Settings(
        token=token,
        owner_id=owner_id,
        whitelist_ids=frozenset(whitelist),
        script_timeout_seconds=_positive_float("SCRIPT_TIMEOUT_SECONDS", 5.0),
        max_script_actions=_positive_int("MAX_SCRIPT_ACTIONS", 20),
    )
