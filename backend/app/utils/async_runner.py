"""
Flask(동기) ↔ asyncio 브릿지 싱글턴

Graphiti API는 전부 async def인데 Flask는 동기 환경.
전용 이벤트루프 스레드(AsyncRunner)로 브릿지.
"""

import asyncio
import threading

from .logger import get_logger

logger = get_logger('nirofish.async_runner')


class AsyncRunner:
    """
    전용 이벤트루프 스레드로 동기 컨텍스트에서 async 코루틴을 실행.

    Flask 요청 스레드에서 asyncio 코루틴을 안전하게 실행하기 위해
    데몬 스레드에서 이벤트루프를 영구적으로 실행하고,
    run_coroutine_threadsafe로 코루틴을 제출한다.
    """

    _loop: asyncio.AbstractEventLoop = None
    _lock = threading.Lock()

    @classmethod
    def get_loop(cls) -> asyncio.AbstractEventLoop:
        """실행 중인 이벤트루프 반환 (필요 시 신규 생성)"""
        with cls._lock:
            if cls._loop is None or not cls._loop.is_running():
                cls._loop = asyncio.new_event_loop()
                t = threading.Thread(
                    target=cls._loop.run_forever,
                    daemon=True,
                    name="AsyncRunner-EventLoop"
                )
                t.start()
                logger.info("AsyncRunner 이벤트루프 스레드 시작됨")
        return cls._loop

    @classmethod
    def run(cls, coro, timeout: int = 300):
        """
        동기 컨텍스트에서 async 코루틴 실행.

        Args:
            coro: 실행할 코루틴 (async def 함수 호출 결과)
            timeout: 타임아웃(초), 기본 300초

        Returns:
            코루틴 반환값

        Raises:
            TimeoutError: timeout 초과 시
            Exception: 코루틴 내부 예외
        """
        loop = cls.get_loop()
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        return future.result(timeout=timeout)

    @classmethod
    def initialize(cls):
        """앱 시작 시 이벤트루프를 미리 초기화"""
        cls.get_loop()
        logger.info("AsyncRunner 초기화 완료")
