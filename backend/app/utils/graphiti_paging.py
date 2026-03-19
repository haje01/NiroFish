"""
Graphiti/Neo4j 기반 노드·엣지 조회 유틸리티.

Zep의 UUID 커서 페이지네이션 대신 Neo4j Cypher 쿼리 직접 실행.
"""

from __future__ import annotations

from typing import Any
from graphiti_core import Graphiti

from .logger import get_logger

logger = get_logger('nirofish.graphiti_paging')

_MAX_NODES = 2000
_MAX_EDGES = 5000


async def fetch_all_nodes_async(
    graphiti_client: Graphiti,
    group_id: str,
    max_nodes: int = _MAX_NODES,
) -> list[dict[str, Any]]:
    """
    Neo4j에서 group_id에 속한 모든 엔티티 노드 조회 (async).

    Returns:
        노드 딕셔너리 목록. 각 항목:
        {uuid, name, labels, summary, attributes, created_at}
    """
    query = (
        "MATCH (n:Entity {group_id: $gid}) "
        "RETURN n LIMIT $limit"
    )
    try:
        async with graphiti_client.driver.session() as session:
            result = await session.run(query, gid=group_id, limit=max_nodes)
            records = await result.data()

        nodes = []
        for record in records:
            n = record["n"]
            # neo4j 드라이버 버전에 따라 Node 객체 또는 dict로 반환됨
            if isinstance(n, dict):
                props = n
                labels = n.get("labels", [])
            else:
                props = dict(n)
                labels = list(n.labels)

            nodes.append({
                "uuid": props.get("uuid", ""),
                "name": props.get("name", ""),
                "labels": labels,
                "summary": props.get("summary", ""),
                "attributes": _safe_dict(props.get("attributes", {})),
                "created_at": str(props["created_at"]) if props.get("created_at") else None,
            })

        if len(nodes) >= max_nodes:
            logger.warning(f"노드 수가 제한({max_nodes})에 도달: graph_id={group_id}")

        logger.info(f"그래프 {group_id}: 노드 {len(nodes)}개 조회 완료")
        return nodes

    except Exception as e:
        logger.error(f"노드 조회 실패 (graph_id={group_id}): {e}")
        return []


async def fetch_all_edges_async(
    graphiti_client: Graphiti,
    group_id: str,
    max_edges: int = _MAX_EDGES,
) -> list[dict[str, Any]]:
    """
    Neo4j에서 group_id에 속한 모든 엔티티 엣지 조회 (async).

    Returns:
        엣지 딕셔너리 목록. 각 항목:
        {uuid, name, fact, source_node_uuid, target_node_uuid,
         created_at, valid_at, invalid_at, expired_at}
    """
    query = (
        "MATCH (s:Entity)-[r:RELATES_TO {group_id: $gid}]->(t:Entity) "
        "RETURN r.uuid AS uuid, r.name AS name, r.fact AS fact, "
        "r.created_at AS created_at, r.valid_at AS valid_at, "
        "r.invalid_at AS invalid_at, r.expired_at AS expired_at, "
        "s.uuid AS source_uuid, t.uuid AS target_uuid "
        "LIMIT $limit"
    )
    try:
        async with graphiti_client.driver.session() as session:
            result = await session.run(query, gid=group_id, limit=max_edges)
            records = await result.data()

        edges = []
        for record in records:
            edges.append({
                "uuid": record.get("uuid", ""),
                "name": record.get("name", ""),
                "fact": record.get("fact", ""),
                "source_node_uuid": record.get("source_uuid", ""),
                "target_node_uuid": record.get("target_uuid", ""),
                "attributes": {},
                "created_at": _dt_str(record.get("created_at")),
                "valid_at": _dt_str(record.get("valid_at")),
                "invalid_at": _dt_str(record.get("invalid_at")),
                "expired_at": _dt_str(record.get("expired_at")),
            })

        logger.info(f"그래프 {group_id}: 엣지 {len(edges)}개 조회 완료")
        return edges

    except Exception as e:
        logger.error(f"엣지 조회 실패 (graph_id={group_id}): {e}")
        return []


async def fetch_node_by_uuid_async(
    graphiti_client: Graphiti,
    node_uuid: str,
) -> dict[str, Any] | None:
    """UUID로 단일 노드 조회 (async)"""
    query = "MATCH (n:Entity {uuid: $uuid}) RETURN n LIMIT 1"
    try:
        async with graphiti_client.driver.session() as session:
            result = await session.run(query, uuid=node_uuid)
            records = await result.data()

        if not records:
            return None

        n = records[0]["n"]
        props = dict(n)
        return {
            "uuid": props.get("uuid", ""),
            "name": props.get("name", ""),
            "labels": list(n.labels),
            "summary": props.get("summary", ""),
            "attributes": _safe_dict(props.get("attributes", {})),
            "created_at": _dt_str(props.get("created_at")),
        }
    except Exception as e:
        logger.error(f"노드 조회 실패 (uuid={node_uuid}): {e}")
        return None


async def fetch_node_edges_async(
    graphiti_client: Graphiti,
    node_uuid: str,
) -> list[dict[str, Any]]:
    """특정 노드에 연결된 모든 엣지 조회 (async)"""
    query = (
        "MATCH (n:Entity {uuid: $uuid})-[r:RELATES_TO]-(m:Entity) "
        "RETURN r.uuid AS uuid, r.name AS name, r.fact AS fact, "
        "r.created_at AS created_at, r.valid_at AS valid_at, "
        "r.invalid_at AS invalid_at, r.expired_at AS expired_at, "
        "startNode(r).uuid AS source_uuid, endNode(r).uuid AS target_uuid"
    )
    try:
        async with graphiti_client.driver.session() as session:
            result = await session.run(query, uuid=node_uuid)
            records = await result.data()

        edges = []
        for record in records:
            edges.append({
                "uuid": record.get("uuid", ""),
                "name": record.get("name", ""),
                "fact": record.get("fact", ""),
                "source_node_uuid": record.get("source_uuid", ""),
                "target_node_uuid": record.get("target_uuid", ""),
                "attributes": {},
                "created_at": _dt_str(record.get("created_at")),
                "valid_at": _dt_str(record.get("valid_at")),
                "invalid_at": _dt_str(record.get("invalid_at")),
                "expired_at": _dt_str(record.get("expired_at")),
            })
        return edges
    except Exception as e:
        logger.error(f"노드 엣지 조회 실패 (uuid={node_uuid}): {e}")
        return []


async def delete_graph_async(
    graphiti_client: Graphiti,
    group_id: str,
) -> int:
    """group_id에 속한 모든 노드·엣지 삭제 (async). 삭제된 노드 수 반환."""
    query = (
        "MATCH (n:Entity {group_id: $gid}) "
        "DETACH DELETE n "
        "RETURN count(n) AS deleted"
    )
    try:
        async with graphiti_client.driver.session() as session:
            result = await session.run(query, gid=group_id)
            records = await result.data()

        deleted = records[0]["deleted"] if records else 0
        logger.info(f"그래프 {group_id}: 노드 {deleted}개 삭제 완료")
        return deleted
    except Exception as e:
        logger.error(f"그래프 삭제 실패 (graph_id={group_id}): {e}")
        return 0


# ── 동기 래퍼 (Flask에서 호출용) ──────────────────────────────────────────────

def fetch_all_nodes(graphiti_client: Graphiti, group_id: str, max_nodes: int = _MAX_NODES) -> list[dict]:
    """동기 버전: fetch_all_nodes_async 래핑"""
    from .async_runner import AsyncRunner
    return AsyncRunner.run(fetch_all_nodes_async(graphiti_client, group_id, max_nodes))


def fetch_all_edges(graphiti_client: Graphiti, group_id: str, max_edges: int = _MAX_EDGES) -> list[dict]:
    """동기 버전: fetch_all_edges_async 래핑"""
    from .async_runner import AsyncRunner
    return AsyncRunner.run(fetch_all_edges_async(graphiti_client, group_id, max_edges))


def fetch_node_by_uuid(graphiti_client: Graphiti, node_uuid: str) -> dict | None:
    """동기 버전: fetch_node_by_uuid_async 래핑"""
    from .async_runner import AsyncRunner
    return AsyncRunner.run(fetch_node_by_uuid_async(graphiti_client, node_uuid))


def fetch_node_edges(graphiti_client: Graphiti, node_uuid: str) -> list[dict]:
    """동기 버전: fetch_node_edges_async 래핑"""
    from .async_runner import AsyncRunner
    return AsyncRunner.run(fetch_node_edges_async(graphiti_client, node_uuid))


def delete_graph(graphiti_client: Graphiti, group_id: str) -> int:
    """동기 버전: delete_graph_async 래핑"""
    from .async_runner import AsyncRunner
    return AsyncRunner.run(delete_graph_async(graphiti_client, group_id))


# ── 내부 헬퍼 ─────────────────────────────────────────────────────────────────

def _rel_to_props(r) -> dict:
    """neo4j Relationship 또는 dict에서 속성 dict 추출"""
    if isinstance(r, dict):
        return r
    if hasattr(r, 'data'):
        return r.data()
    if hasattr(r, 'items'):
        return dict(r.items())
    return {}


def _dt_str(val) -> str | None:
    """datetime 또는 문자열을 str로 변환. None이면 None 반환."""
    if val is None:
        return None
    return str(val)


def _safe_dict(val) -> dict:
    """속성값을 dict로 안전하게 변환"""
    if isinstance(val, dict):
        return val
    if isinstance(val, str):
        import json
        try:
            result = json.loads(val)
            return result if isinstance(result, dict) else {}
        except Exception:
            return {}
    return {}
