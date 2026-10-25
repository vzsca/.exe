"""Identity-based permissions. Server Administrator is deliberately irrelevant."""

from collections.abc import Collection

from .config import Settings


def is_owner(user_id: int, settings: Settings) -> bool:
    return user_id == settings.owner_id


def may_run_scripts(
    user_id: int,
    settings: Settings,
    whitelist_ids: Collection[int] = (),
) -> bool:
    return is_owner(user_id, settings) or user_id in whitelist_ids


def may_manage_access(user_id: int, settings: Settings) -> bool:
    return is_owner(user_id, settings)
