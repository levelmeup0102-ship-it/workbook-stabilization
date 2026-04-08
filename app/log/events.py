"""
    # 얇은 로깅 헬퍼
        — loguru를 직접 import하는 유일한 모듈.
        — 앱 코드는 이 함수들을 호출하고, loguru를 직접 사용하지 않는다.
          나중에 Pydantic 이벤트로 전환 시 이 파일 내부만 수정하면 된다.
"""
from loguru import logger


# I/O전용의 입력값 체크 로깅 함수
def log_io_start(action: str, **kwargs) -> None:
    logger.info(action, **kwargs)

# I/O전용의 함수 실행 성공 로깅 함수
def log_io_success(action: str, **kwargs) -> None:
    logger.info(action, **kwargs)


# I/O전용의 함수 실행 실패 로깅 함수
def log_io_failure(action: str, **kwargs) -> None:
    logger.error(action, **kwargs)


# 로컬 개발시 디버그 용도의 로깅 함수
def log_debug(message: str, **kwargs) -> None:
    logger.debug(message, **kwargs)


# 로컬 개발시 심각 단계 로깅 함수
def log_warning(message: str, **kwargs) -> None:
    logger.warning(message, **kwargs)


# 예상 못한 예외 로깅 함수
def log_exception(message: str, **kwargs) -> None:
    logger.exception(message, **kwargs)
