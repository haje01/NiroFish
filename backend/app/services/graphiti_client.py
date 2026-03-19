"""
Graphiti 클라이언트 싱글턴

Neo4j + Graphiti 기반 지식 그래프 클라이언트.
앱 전체에서 하나의 인스턴스를 공유한다.
"""

import threading
from typing import Optional

from graphiti_core import Graphiti
from graphiti_core.llm_client.openai_client import OpenAIClient, LLMConfig

from ..config import Config
from ..utils.logger import get_logger
from ..utils.async_runner import AsyncRunner

logger = get_logger('mirofish.graphiti_client')


class GraphitiClientManager:
    """
    Graphiti 클라이언트 싱글턴 매니저.

    최초 호출 시 Neo4j 연결 + 인덱스 초기화.
    이후 동일 인스턴스 반환.
    """

    _client: Optional[Graphiti] = None
    _lock = threading.Lock()
    _initialized = False

    @classmethod
    def get_client(cls) -> Graphiti:
        """
        Graphiti 클라이언트 반환 (없으면 생성 + 초기화).

        Returns:
            Graphiti 클라이언트 인스턴스
        """
        with cls._lock:
            if cls._client is None:
                cls._client = cls._create_client()
            return cls._client

    @classmethod
    def _create_client(cls) -> Graphiti:
        """Graphiti 클라이언트 생성 및 초기화"""
        logger.info(f"Graphiti 클라이언트 생성: uri={Config.NEO4J_URI}")

        # OpenAI 호환 LLM 클라이언트 구성
        llm_config = LLMConfig(
            api_key=Config.LLM_API_KEY,
            model=Config.LLM_MODEL_NAME,
            base_url=Config.LLM_BASE_URL,
        )
        llm_client = OpenAIClient(config=llm_config)

        client = Graphiti(
            uri=Config.NEO4J_URI,
            user=Config.NEO4J_USER,
            password=Config.NEO4J_PASSWORD,
            llm_client=llm_client,
        )

        # 인덱스 및 제약 조건 초기화 (최초 1회)
        if not cls._initialized:
            try:
                AsyncRunner.run(client.build_indices_and_constraints(), timeout=60)
                cls._initialized = True
                logger.info("Graphiti 인덱스 및 제약 조건 초기화 완료")
            except Exception as e:
                logger.warning(f"Graphiti 인덱스 초기화 실패 (Neo4j 미실행?): {e}")

        logger.info("Graphiti 클라이언트 생성 완료")
        return client

    @classmethod
    def reset(cls):
        """클라이언트 초기화 (테스트 또는 재연결 시 사용)"""
        with cls._lock:
            if cls._client is not None:
                try:
                    AsyncRunner.run(cls._client.close(), timeout=10)
                except Exception:
                    pass
            cls._client = None
            cls._initialized = False
        logger.info("Graphiti 클라이언트 리셋됨")
