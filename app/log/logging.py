import os
import sys
from loguru import logger


def setup_logger() -> None:
    logger.remove()

    env = os.getenv("ENV", "dev")
    level = "DEBUG" if env == "dev" else "INFO"

    logger.level("DEBUG", color="<cyan>")
    logger.level("INFO", color="<green>")
    logger.level("WARNING", color="<yellow>")
    logger.level("ERROR", color="<red>")
    logger.level("CRITICAL", color="<bold><red>")

    logger.add(
        sys.stdout,
        level=level,
        format=(
            "<dim>{time:YYYY-MM-DD HH:mm:ss}</dim> "
            "[<level>{level:<8}</level>] "
            "<bold>{message:<30}</bold> "
            "<cyan>{extra}</cyan>"
        ),
        colorize=True,
        backtrace=True,
        diagnose=(env == "dev"),
        catch=True,
    )
