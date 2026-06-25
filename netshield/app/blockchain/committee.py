import hashlib
import json
import time
from typing import Optional, Dict, Any, List
import httpx
from loguru import logger
from app.config import get_settings
from app.blockchain.ledger import MockLedger


class NodeConnectionError(Exception):
    pass


class MockNode:
    def __init__(self, node_id: int):
        self.node_id = node_id
        self.fragments: Dict[str, bytes] = {}
        self.ledger = MockLedger(node_id)
        self.active = True

    def store_fragment(self, fragment_id: str, fragment: bytes) -> str:
        self.fragments[fragment_id] = fragment
        return hashlib.sha256(fragment).hexdigest()

    def get_fragment(self, fragment_id: str) -> Optional[bytes]:
        return self.fragments.get(fragment_id)

    def has_fragment(self, fragment_id: str) -> bool:
        return fragment_id in self.fragments

    def transact(self, block_data: dict) -> dict:
        return self.ledger.add_block(block_data)

    def get_ledger(self) -> list:
        return self.ledger.get_chain()

    def verify_ledger(self) -> dict:
        return self.ledger.verify_chain()

    def health(self) -> bool:
        return self.active

    def reset(self):
        self.fragments.clear()
        self.ledger.reset()


_mock_nodes: List[MockNode] = []


def _get_mock_nodes() -> List[MockNode]:
    global _mock_nodes
    if not _mock_nodes:
        _mock_nodes = [MockNode(i) for i in range(3)]
        logger.info("Blockchain committee running in MOCK mode")
    return _mock_nodes


class BlockchainCommittee:
    def __init__(self):
        self.settings = get_settings()
        self.mock_mode = self.settings.mock_blockchain
        self.nodes: List[MockNode] = []
        self.node_urls: List[str] = []
        if self.mock_mode:
            self.nodes = _get_mock_nodes()
        else:
            self.node_urls = [
                self.settings.node1_url,
                self.settings.node2_url,
                self.settings.node3_url,
            ]
            logger.info("Blockchain committee running in PRODUCTION mode")

    async def store_fragment(self, node_index: int, fragment_id: str, fragment: bytes) -> str:
        if self.mock_mode:
            return self.nodes[node_index].store_fragment(fragment_id, fragment)
        async with httpx.AsyncClient(timeout=5.0) as client:
            payload = {
                "jsonrpc": "2.0",
                "method": "eth_sendRawTransaction",
                "params": [f"0x{fragment.hex()}"],
                "id": 1,
            }
            try:
                resp = await client.post(self.node_urls[node_index], json=payload)
                resp.raise_for_status()
                return hashlib.sha256(fragment).hexdigest()
            except (httpx.TimeoutException, httpx.RequestError) as exc:
                raise NodeConnectionError(
                    f"Node {node_index + 1} unreachable: {exc}"
                ) from exc

    async def get_fragment(self, node_index: int, fragment_id: str) -> Optional[bytes]:
        if self.mock_mode:
            return self.nodes[node_index].get_fragment(fragment_id)
        async with httpx.AsyncClient(timeout=5.0) as client:
            payload = {
                "jsonrpc": "2.0",
                "method": "eth_getStorageAt",
                "params": [f"0x{fragment_id}", "0x0", "latest"],
                "id": 1,
            }
            try:
                resp = await client.post(self.node_urls[node_index], json=payload)
                resp.raise_for_status()
                result = resp.json().get("result", "")
                if result and result.startswith("0x"):
                    return bytes.fromhex(result[2:])
                return None
            except (httpx.TimeoutException, httpx.RequestError) as exc:
                raise NodeConnectionError(
                    f"Node {node_index + 1} unreachable: {exc}"
                ) from exc

    async def transact(self, block_data: dict) -> dict:
        if self.mock_mode:
            results = []
            for node in self.nodes:
                results.append(node.transact(block_data))
            r = dict(results[0])
            r["consensus"] = "PBFT (simulated) - 3/3 confirmed"
            return r
        async with httpx.AsyncClient(timeout=5.0) as client:
            payload = {
                "jsonrpc": "2.0",
                "method": "eth_sendTransaction",
                "params": [block_data],
                "id": 1,
            }
            try:
                resp = await client.post(self.node_urls[0], json=payload)
                resp.raise_for_status()
                return resp.json()
            except (httpx.TimeoutException, httpx.RequestError) as exc:
                raise NodeConnectionError(
                    f"Transaction failed: {exc}"
                ) from exc

    async def get_ledger(self) -> list:
        if self.mock_mode:
            return self.nodes[0].get_ledger()
        return []

    async def verify_ledger(self) -> dict:
        if self.mock_mode:
            results = [node.verify_ledger() for node in self.nodes]
            valid = all(r["valid"] for r in results)
            return {
                "valid": valid,
                "node_results": results,
                "consensus": "all nodes agree" if valid else "INCONSISTENCY DETECTED",
            }
        return {"valid": False, "message": "Ledger verification only available in mock mode"}

    async def health_check(self) -> dict:
        statuses = {}
        if self.mock_mode:
            for i, node in enumerate(self.nodes):
                statuses[f"node{i + 1}"] = "healthy" if node.health() else "unreachable"
        else:
            for i, url in enumerate(self.node_urls):
                try:
                    async with httpx.AsyncClient(timeout=2.0) as client:
                        resp = await client.post(
                            url,
                            json={
                                "jsonrpc": "2.0",
                                "method": "net_version",
                                "params": [],
                                "id": 1,
                            },
                        )
                        statuses[f"node{i + 1}"] = "healthy" if resp.status_code == 200 else "error"
                except Exception:
                    statuses[f"node{i + 1}"] = "unreachable"
        return statuses

    async def reset(self):
        if self.mock_mode:
            for node in self.nodes:
                node.reset()
            logger.info("All mock nodes reset")

    def force_reinit(self):
        global _mock_nodes
        _mock_nodes = []
        self.nodes = _get_mock_nodes()
