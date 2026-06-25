import pytest
from app.blockchain.ledger import MockLedger, GENESIS_BLOCK


class TestLedger:
    def test_genesis_block(self):
        ledger = MockLedger(node_id=0)
        chain = ledger.get_chain()
        assert len(chain) == 1
        assert chain[0]["action"] == "genesis"
        assert chain[0]["index"] == 0

    def test_add_block(self):
        ledger = MockLedger(node_id=0)
        block_data = {
            "action": "test_action",
            "user": "test_user",
            "data_hash": "abcdef123456",
            "signature": "test_sig",
        }
        block = ledger.add_block(block_data)
        assert block["index"] == 1
        assert block["action"] == "test_action"
        assert block["user"] == "test_user"
        assert block["previous_hash"] == GENESIS_BLOCK["hash"]
        assert len(block["hash"]) == 64

    def test_chain_integrity(self):
        ledger = MockLedger(node_id=0)
        for i in range(5):
            ledger.add_block({
                "action": f"action_{i}",
                "user": "user",
                "data_hash": f"hash_{i}",
                "signature": f"sig_{i}",
            })
        result = ledger.verify_chain()
        assert result["valid"] is True
        assert result["blocks"] == 6

    def test_tampered_block(self):
        ledger = MockLedger(node_id=0)
        ledger.add_block({"action": "a", "user": "u", "data_hash": "h", "signature": "s"})
        ledger.chain[1]["data_hash"] = "tampered"
        result = ledger.verify_chain()
        assert result["valid"] is False

    def test_reset(self):
        ledger = MockLedger(node_id=0)
        ledger.add_block({"action": "a", "user": "u", "data_hash": "h", "signature": "s"})
        assert len(ledger.get_chain()) == 2
        ledger.reset()
        assert len(ledger.get_chain()) == 1
        assert ledger.get_chain()[0]["action"] == "genesis"

    def test_multi_node_consistency(self):
        l1 = MockLedger(node_id=0)
        l2 = MockLedger(node_id=1)
        l3 = MockLedger(node_id=2)
        for i in range(3):
            bd = {"action": f"a{i}", "user": "u", "data_hash": f"h{i}", "signature": "s"}
            l1.add_block(bd)
            l2.add_block(bd)
            l3.add_block(bd)
        assert l1.verify_chain()["valid"]
        assert l2.verify_chain()["valid"]
        assert l3.verify_chain()["valid"]
        c1 = [b["hash"] for b in l1.get_chain()]
        c2 = [b["hash"] for b in l2.get_chain()]
        c3 = [b["hash"] for b in l3.get_chain()]
        assert c1 == c2 == c3
