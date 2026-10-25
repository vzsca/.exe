"""Run the .exe Discord bot with ``python -m exe_bot``."""

import asyncio
import logging

from .bot import run_bot
from .config import load_settings


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    settings = load_settings()
    asyncio.run(run_bot(settings))


if __name__ == "__main__":
    main()
