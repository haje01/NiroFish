"""
그래프 구축 서비스
인터페이스2: Neo4j + Graphiti를 사용하여 지식 그래프 구축
"""

import uuid
import threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass

from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType

from ..config import Config
from ..models.task import TaskManager, TaskStatus
from ..utils.graphiti_paging import fetch_all_nodes, fetch_all_edges
from ..utils.async_runner import AsyncRunner
from .graphiti_client import GraphitiClientManager
from .text_processor import TextProcessor


@dataclass
class GraphInfo:
    """그래프 정보"""
    graph_id: str
    node_count: int
    edge_count: int
    entity_types: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "graph_id": self.graph_id,
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "entity_types": self.entity_types,
        }


class GraphBuilderService:
    """
    그래프 구축 서비스
    Graphiti API를 호출하여 Neo4j 지식 그래프를 구축하는 역할
    """

    def __init__(self):
        self._graphiti: Graphiti = GraphitiClientManager.get_client()
        self.task_manager = TaskManager()
        # 온톨로지 캐시: graph_id → entity_types dict
        self._entity_types_cache: Dict[str, Dict] = {}

    def build_graph_async(
        self,
        text: str,
        ontology: Dict[str, Any],
        graph_name: str = "NiroFish Graph",
        chunk_size: int = None,
        chunk_overlap: int = 50,
        batch_size: int = 3
    ) -> str:
        """
        비동기 그래프 구축

        Args:
            text: 입력 텍스트
            ontology: 온톨로지 정의 (인터페이스1의 출력)
            graph_name: 그래프 이름
            chunk_size: 텍스트 청크 크기 (None이면 Config.DEFAULT_CHUNK_SIZE 사용)
            chunk_overlap: 청크 오버랩 크기
            batch_size: 배치당 전송할 청크 수 (Graphiti에서는 순차 처리이므로 참고용)

        Returns:
            작업 ID
        """
        if chunk_size is None:
            chunk_size = Config.DEFAULT_CHUNK_SIZE

        # 작업 생성
        task_id = self.task_manager.create_task(
            task_type="graph_build",
            metadata={
                "graph_name": graph_name,
                "chunk_size": chunk_size,
                "text_length": len(text),
            }
        )

        # 백그라운드 스레드에서 구축 실행
        thread = threading.Thread(
            target=self._build_graph_worker,
            args=(task_id, text, ontology, graph_name, chunk_size, chunk_overlap)
        )
        thread.daemon = True
        thread.start()

        return task_id

    def _build_graph_worker(
        self,
        task_id: str,
        text: str,
        ontology: Dict[str, Any],
        graph_name: str,
        chunk_size: int,
        chunk_overlap: int,
    ):
        """그래프 구축 워커 스레드"""
        try:
            self.task_manager.update_task(
                task_id,
                status=TaskStatus.PROCESSING,
                progress=5,
                message="그래프 구축 시작 중..."
            )

            # 1. 그래프 ID 생성 (Neo4j에서는 별도 그래프 생성 불필요)
            graph_id = self.create_graph(graph_name)
            self.task_manager.update_task(
                task_id,
                progress=10,
                message=f"그래프 ID 생성됨: {graph_id}"
            )

            # 2. 온톨로지 캐시에 저장
            self.set_ontology(graph_id, ontology)
            self.task_manager.update_task(
                task_id,
                progress=15,
                message="온톨로지 설정 완료"
            )

            # 3. 텍스트 청크 분할
            chunks = TextProcessor.split_text(text, chunk_size, chunk_overlap)
            total_chunks = len(chunks)
            self.task_manager.update_task(
                task_id,
                progress=20,
                message=f"텍스트를 {total_chunks}개 청크로 분할 완료"
            )

            # 4. 청크를 순차적으로 Graphiti에 추가 (Graphiti는 add_episode마다 동기 완료)
            self.add_text_batches(
                graph_id, chunks,
                lambda msg, prog: self.task_manager.update_task(
                    task_id,
                    progress=20 + int(prog * 0.70),  # 20-90%
                    message=msg
                )
            )

            # 5. 그래프 정보 가져오기
            self.task_manager.update_task(
                task_id,
                progress=90,
                message="그래프 정보 가져오는 중..."
            )

            graph_info = self._get_graph_info(graph_id)

            # 완료
            self.task_manager.complete_task(task_id, {
                "graph_id": graph_id,
                "graph_info": graph_info.to_dict(),
                "chunks_processed": total_chunks,
            })

        except Exception as e:
            import traceback
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            self.task_manager.fail_task(task_id, error_msg)

    def create_graph(self, name: str) -> str:
        """
        그래프 ID 생성.
        Graphiti/Neo4j에서는 별도 그래프 생성 API 없음.
        group_id로 사용할 고유 ID만 발급.
        """
        graph_id = f"nirofish_{uuid.uuid4().hex[:16]}"
        return graph_id

    def set_ontology(self, graph_id: str, ontology: Dict[str, Any]):
        """
        온톨로지를 Pydantic 모델 dict로 변환하여 캐시에 저장.
        Graphiti는 add_episode 시 entity_types 파라미터로 전달.
        entity_types 형식: {TypeName: PydanticModel 서브클래스}
        """
        import re
        from pydantic import BaseModel

        def to_pascal_case(name: str) -> str:
            words = re.split(r'[\s_\-\.]+', name.strip())
            pascal = ''.join(w.capitalize() for w in words if w)
            pascal = re.sub(r'[^A-Za-z0-9]', '', pascal)
            if pascal and pascal[0].isdigit():
                pascal = 'T' + pascal
            return pascal or 'Entity'

        entity_types = {}
        for entity_def in ontology.get("entity_types", []):
            type_name = to_pascal_case(entity_def["name"])
            description = entity_def.get("description", f"A {type_name} entity.")

            # 동적으로 Pydantic BaseModel 서브클래스 생성
            # Graphiti는 entity_types 값으로 BaseModel 서브클래스를 기대함
            model_class = type(type_name, (BaseModel,), {
                "__doc__": description,
                "__annotations__": {},
            })
            entity_types[type_name] = model_class

        self._entity_types_cache[graph_id] = entity_types

    def add_text_batches(
        self,
        graph_id: str,
        chunks: List[str],
        progress_callback: Optional[Callable] = None
    ) -> None:
        """
        텍스트 청크를 Graphiti에 순차 추가.

        Graphiti의 add_episode는 await 시점에 동기적으로 완료되므로
        Zep의 _wait_for_episodes() 폴링이 불필요.
        """
        total_chunks = len(chunks)
        entity_types = self._entity_types_cache.get(graph_id, {})

        for i, chunk in enumerate(chunks):
            if progress_callback:
                progress = (i + 1) / total_chunks
                progress_callback(
                    f"{i + 1}/{total_chunks} 번째 청크 처리 중...",
                    progress
                )

            try:
                AsyncRunner.run(
                    self._graphiti.add_episode(
                        name=f"chunk_{i}",
                        episode_body=chunk,
                        source_description="NiroFish knowledge document",
                        reference_time=datetime.now(timezone.utc),
                        source=EpisodeType.text,
                        group_id=graph_id,
                        entity_types=entity_types if entity_types else None,
                    ),
                    timeout=300
                )
            except Exception as e:
                if progress_callback:
                    progress_callback(f"청크 {i + 1} 처리 실패: {str(e)}", (i + 1) / total_chunks)
                raise

    def _get_graph_info(self, graph_id: str) -> GraphInfo:
        """그래프 정보 가져오기"""
        nodes = fetch_all_nodes(self._graphiti, graph_id)
        edges = fetch_all_edges(self._graphiti, graph_id)

        # 엔티티 타입 집계
        entity_types = set()
        for node in nodes:
            for label in node.get("labels", []):
                if label not in ["Entity", "Node", "Episodic"]:
                    entity_types.add(label)

        return GraphInfo(
            graph_id=graph_id,
            node_count=len(nodes),
            edge_count=len(edges),
            entity_types=list(entity_types)
        )

    def get_graph_data(self, graph_id: str) -> Dict[str, Any]:
        """
        전체 그래프 데이터 가져오기 (상세 정보 포함)

        Returns:
            nodes와 edges를 포함하는 딕셔너리
        """
        nodes = fetch_all_nodes(self._graphiti, graph_id)
        edges = fetch_all_edges(self._graphiti, graph_id)

        # 노드 이름 맵
        node_map = {n["uuid"]: n.get("name", "") for n in nodes}

        nodes_data = []
        for node in nodes:
            nodes_data.append({
                "uuid": node["uuid"],
                "name": node["name"],
                "labels": node["labels"],
                "summary": node.get("summary", ""),
                "attributes": node.get("attributes", {}),
                "created_at": node.get("created_at"),
            })

        edges_data = []
        for edge in edges:
            edges_data.append({
                "uuid": edge["uuid"],
                "name": edge.get("name", ""),
                "fact": edge.get("fact", ""),
                "fact_type": edge.get("name", ""),
                "source_node_uuid": edge["source_node_uuid"],
                "target_node_uuid": edge["target_node_uuid"],
                "source_node_name": node_map.get(edge["source_node_uuid"], ""),
                "target_node_name": node_map.get(edge["target_node_uuid"], ""),
                "attributes": edge.get("attributes", {}),
                "created_at": edge.get("created_at"),
                "valid_at": edge.get("valid_at"),
                "invalid_at": edge.get("invalid_at"),
                "expired_at": edge.get("expired_at"),
                "episodes": [],
            })

        return {
            "graph_id": graph_id,
            "nodes": nodes_data,
            "edges": edges_data,
            "node_count": len(nodes_data),
            "edge_count": len(edges_data),
        }

    def delete_graph(self, graph_id: str):
        """그래프의 모든 노드·엣지 삭제"""
        from ..utils.graphiti_paging import delete_graph
        deleted = delete_graph(self._graphiti, graph_id)
        # 캐시도 제거
        self._entity_types_cache.pop(graph_id, None)
        return deleted
