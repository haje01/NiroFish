"""
엔티티 읽기 및 필터링 서비스
Graphiti/Neo4j 그래프에서 노드를 읽고, 사전 정의된 엔티티 타입에 맞는 노드를 필터링
"""

from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field

from ..utils.logger import get_logger
from ..utils.graphiti_paging import fetch_all_nodes, fetch_all_edges, fetch_node_edges

logger = get_logger('mirofish.zep_entity_reader')


@dataclass
class EntityNode:
    """엔티티 노드 데이터 구조"""
    uuid: str
    name: str
    labels: List[str]
    summary: str
    attributes: Dict[str, Any]
    # 관련 엣지 정보
    related_edges: List[Dict[str, Any]] = field(default_factory=list)
    # 관련 다른 노드 정보
    related_nodes: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "uuid": self.uuid,
            "name": self.name,
            "labels": self.labels,
            "summary": self.summary,
            "attributes": self.attributes,
            "related_edges": self.related_edges,
            "related_nodes": self.related_nodes,
        }

    def get_entity_type(self) -> Optional[str]:
        """엔티티 타입 가져오기 (기본 Entity 라벨 제외)"""
        for label in self.labels:
            if label not in ["Entity", "Node", "Episodic"]:
                return label
        return None


@dataclass
class FilteredEntities:
    """필터링된 엔티티 집합"""
    entities: List[EntityNode]
    entity_types: Set[str]
    total_count: int
    filtered_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entities": [e.to_dict() for e in self.entities],
            "entity_types": list(self.entity_types),
            "total_count": self.total_count,
            "filtered_count": self.filtered_count,
        }


class ZepEntityReader:
    """
    엔티티 읽기 및 필터링 서비스 (Graphiti/Neo4j 기반)

    주요 기능:
    1. Graphiti/Neo4j 그래프에서 모든 노드 읽기
    2. 사전 정의된 엔티티 타입에 맞는 노드 필터링
    3. 각 엔티티의 관련 엣지 및 연결 노드 정보 가져오기
    """

    def __init__(self):
        from .graphiti_client import GraphitiClientManager
        self._graphiti = GraphitiClientManager.get_client()

    def get_all_nodes(self, graph_id: str) -> List[Dict[str, Any]]:
        """그래프의 모든 노드 가져오기"""
        logger.info(f"그래프 {graph_id}의 모든 노드 가져오는 중...")
        nodes = fetch_all_nodes(self._graphiti, graph_id)
        logger.info(f"총 {len(nodes)}개 노드 가져옴")
        return nodes

    def get_all_edges(self, graph_id: str) -> List[Dict[str, Any]]:
        """그래프의 모든 엣지 가져오기"""
        logger.info(f"그래프 {graph_id}의 모든 엣지 가져오는 중...")
        edges = fetch_all_edges(self._graphiti, graph_id)
        logger.info(f"총 {len(edges)}개 엣지 가져옴")
        return edges

    def get_node_edges(self, node_uuid: str) -> List[Dict[str, Any]]:
        """지정 노드의 모든 관련 엣지 가져오기"""
        try:
            edges = fetch_node_edges(self._graphiti, node_uuid)
            return edges
        except Exception as e:
            logger.warning(f"노드 {node_uuid}의 엣지 가져오기 실패: {str(e)}")
            return []

    def filter_defined_entities(
        self,
        graph_id: str,
        defined_entity_types: Optional[List[str]] = None,
        enrich_with_edges: bool = True
    ) -> FilteredEntities:
        """
        사전 정의된 엔티티 타입에 맞는 노드 필터링

        필터링 로직:
        - 노드의 Labels가 "Entity"/"Node"/"Episodic"만이라면 사전 정의된 타입에 맞지 않으므로 건너뜀
        - 그 외 라벨이 포함되면 사전 정의된 타입에 맞으므로 유지
        """
        logger.info(f"그래프 {graph_id}의 엔티티 필터링 시작...")

        all_nodes = self.get_all_nodes(graph_id)
        total_count = len(all_nodes)
        all_edges = self.get_all_edges(graph_id) if enrich_with_edges else []
        node_map = {n["uuid"]: n for n in all_nodes}

        filtered_entities = []
        entity_types_found = set()
        _base_labels = {"Entity", "Node", "Episodic"}

        for node in all_nodes:
            labels = node.get("labels", [])
            custom_labels = [l for l in labels if l not in _base_labels]

            if not custom_labels:
                continue

            if defined_entity_types:
                matching_labels = [l for l in custom_labels if l in defined_entity_types]
                if not matching_labels:
                    continue
                entity_type = matching_labels[0]
            else:
                entity_type = custom_labels[0]

            entity_types_found.add(entity_type)

            entity = EntityNode(
                uuid=node["uuid"],
                name=node["name"],
                labels=labels,
                summary=node.get("summary", ""),
                attributes=node.get("attributes", {}),
            )

            if enrich_with_edges:
                related_edges = []
                related_node_uuids = set()

                for edge in all_edges:
                    if edge["source_node_uuid"] == node["uuid"]:
                        related_edges.append({
                            "direction": "outgoing",
                            "edge_name": edge["name"],
                            "fact": edge["fact"],
                            "target_node_uuid": edge["target_node_uuid"],
                        })
                        related_node_uuids.add(edge["target_node_uuid"])
                    elif edge["target_node_uuid"] == node["uuid"]:
                        related_edges.append({
                            "direction": "incoming",
                            "edge_name": edge["name"],
                            "fact": edge["fact"],
                            "source_node_uuid": edge["source_node_uuid"],
                        })
                        related_node_uuids.add(edge["source_node_uuid"])

                entity.related_edges = related_edges

                related_nodes = []
                for related_uuid in related_node_uuids:
                    if related_uuid in node_map:
                        related_node = node_map[related_uuid]
                        related_nodes.append({
                            "uuid": related_node["uuid"],
                            "name": related_node["name"],
                            "labels": related_node["labels"],
                            "summary": related_node.get("summary", ""),
                        })
                entity.related_nodes = related_nodes

            filtered_entities.append(entity)

        logger.info(f"필터링 완료: 전체 노드 {total_count}, 조건 만족 {len(filtered_entities)}, "
                    f"엔티티 타입: {entity_types_found}")

        return FilteredEntities(
            entities=filtered_entities,
            entity_types=entity_types_found,
            total_count=total_count,
            filtered_count=len(filtered_entities),
        )

    def get_entity_with_context(
        self,
        graph_id: str,
        entity_uuid: str
    ) -> Optional[EntityNode]:
        """단일 엔티티 및 전체 컨텍스트 가져오기"""
        from ..utils.graphiti_paging import fetch_node_by_uuid

        try:
            node = fetch_node_by_uuid(self._graphiti, entity_uuid)
            if not node:
                return None

            edges = self.get_node_edges(entity_uuid)
            all_nodes = self.get_all_nodes(graph_id)
            node_map = {n["uuid"]: n for n in all_nodes}

            related_edges = []
            related_node_uuids = set()

            for edge in edges:
                if edge["source_node_uuid"] == entity_uuid:
                    related_edges.append({
                        "direction": "outgoing",
                        "edge_name": edge["name"],
                        "fact": edge["fact"],
                        "target_node_uuid": edge["target_node_uuid"],
                    })
                    related_node_uuids.add(edge["target_node_uuid"])
                else:
                    related_edges.append({
                        "direction": "incoming",
                        "edge_name": edge["name"],
                        "fact": edge["fact"],
                        "source_node_uuid": edge["source_node_uuid"],
                    })
                    related_node_uuids.add(edge["source_node_uuid"])

            related_nodes = []
            for related_uuid in related_node_uuids:
                if related_uuid in node_map:
                    related_node = node_map[related_uuid]
                    related_nodes.append({
                        "uuid": related_node["uuid"],
                        "name": related_node["name"],
                        "labels": related_node["labels"],
                        "summary": related_node.get("summary", ""),
                    })

            return EntityNode(
                uuid=node["uuid"],
                name=node["name"],
                labels=node["labels"],
                summary=node.get("summary", ""),
                attributes=node.get("attributes", {}),
                related_edges=related_edges,
                related_nodes=related_nodes,
            )

        except Exception as e:
            logger.error(f"엔티티 {entity_uuid} 가져오기 실패: {str(e)}")
            return None

    def get_entities_by_type(
        self,
        graph_id: str,
        entity_type: str,
        enrich_with_edges: bool = True
    ) -> List[EntityNode]:
        """지정 타입의 모든 엔티티 가져오기"""
        result = self.filter_defined_entities(
            graph_id=graph_id,
            defined_entity_types=[entity_type],
            enrich_with_edges=enrich_with_edges
        )
        return result.entities
