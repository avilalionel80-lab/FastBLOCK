import hashlib
import json
import time
from typing import List, Optional
from loguru import logger


GENESIS_BLOCK = {
    "index": 0,
    "timestamp": "2024-01-01T00:00:00Z",
    "action": "genesis",
    "user": "system",
    "data_hash": "0" * 64,
    "previous_hash": "0" * 64,
    "signature": "genesis",
    "hash": "0" * 64,
}


class MockLedger:
    def __init__(self, node_id: int):
        self.node_id = node_id
        self.chain: List[dict] = [dict(GENESIS_BLOCK)]

    def _calculate_hash(self, block: dict) -> str:
        block_copy = {k: v for k, v in block.items() if k != "hash"}
        raw = json.dumps(block_copy, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()

    def add_block(self, block_data: dict) -> dict:
        previous_block = self.chain[-1]
        block = {
            "index": previous_block["index"] + 1,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "action": block_data.get("action", "unknown"),
            "user": block_data.get("user", "anonymous"),
            "data_hash": block_data.get("data_hash", ""),
            "previous_hash": previous_block["hash"],
            "signature": block_data.get("signature", ""),
            "hash": "",
        }
        block["hash"] = self._calculate_hash(block)

        errors = self._validate_block(block, previous_block)
        if errors:
            logger.error(f"Block validation failed: {errors}")
            raise ValueError(f"Block validation failed: {errors}")

        self.chain.append(block)
        logger.debug(f"Block #{block['index']} added to ledger (node {self.node_id})")
        return block

    def _validate_block(self, block: dict, previous_block: dict) -> list:
        errors = []
        expected_hash = self._calculate_hash(block)
        if block["hash"] != expected_hash:
            errors.append(f"Block hash mismatch: got {block['hash']}, expected {expected_hash}")
        if block["previous_hash"] != previous_block["hash"]:
            errors.append(
                f"Previous hash mismatch: got {block['previous_hash']}, expected {previous_block['hash']}"
            )
        return errors

    def get_chain(self) -> list:
        return list(self.chain)

    def verify_chain(self) -> dict:
        errors = []
        for i in range(1, len(self.chain)):
            block = self.chain[i]
            prev = self.chain[i - 1]
            block_errors = self._validate_block(block, prev)
            errors.extend(block_errors)
        return {"valid": len(errors) == 0, "errors": errors, "blocks": len(self.chain)}

    def reset(self):
        self.chain = [dict(GENESIS_BLOCK)]
        logger.info(f"Ledger (node {self.node_id}) reset to genesis")
