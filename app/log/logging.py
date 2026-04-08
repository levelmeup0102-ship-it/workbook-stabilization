import sys
from loguru import logger
from app.config import get_settings


def setup_logger() -> None:
    logger.remove() # 이전 로거 설정 초기화 

    env = get_settings().env
    level = "DEBUG" if env == "dev" else "INFO"

    logger.level("DEBUG", color="<cyan>")
    logger.level("INFO", color="<green>")
    logger.level("WARNING", color="<yellow>")
    logger.level("ERROR", color="<red>")
    logger.level("CRITICAL", color="<bold><red>")

    logger.add(
        sys.stdout, # local print
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