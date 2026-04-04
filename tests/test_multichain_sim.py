import pytest
from framework.chain import MockChain
from framework.bridge import MockBridge
from framework.assertions import assert_total_supply_conserved


def test_sequential_transfers():
    chain_a = MockChain(1, "Ethereum")
    chain_b = MockChain(10, "Optimism")
    chain_c = MockChain(137, "Polygon")

    bridge_ab = MockBridge(chain_a, chain_b)
    bridge_bc = MockBridge(chain_b, chain_c)

    msg1 = bridge_ab.lock_and_mint("USDC", 200, "0xAlice")
    bridge_ab.relay_messages()
    assert bridge_ab.is_relayed(msg1)
    assert bridge_ab.get_minted("USDC") == 200

    msg2 = bridge_bc.lock_and_mint("USDC", 150, "0xBob")
    bridge_bc.relay_messages()
    assert bridge_bc.is_relayed(msg2)
    assert bridge_bc.get_minted("USDC") == 150

    assert_total_supply_conserved(bridge_ab, "USDC")
    assert_total_supply_conserved(bridge_bc, "USDC")


def test_concurrent_transfers():
    source_chain = MockChain(1, "Ethereum")
    dest_chain = MockChain(10, "Optimism")
    bridge = MockBridge(source_chain, dest_chain)

    msg_ids = []
    for i in range(5):
        msg_id = bridge.lock_and_mint("USDC", 100 * (i + 1), f"0xUser{i}")
        msg_ids.append(msg_id)

    assert len(bridge.get_pending_messages()) == 5

    bridge.relay_messages()

    for msg_id in msg_ids:
        assert bridge.is_relayed(msg_id), f"Message {msg_id} was not relayed"

    assert bridge.get_minted("USDC") == 100 + 200 + 300 + 400 + 500
    assert_total_supply_conserved(bridge, "USDC")


def test_bridge_failure_recovery():
    source_chain = MockChain(1, "Ethereum")
    dest_chain = MockChain(10, "Optimism")

    failing_bridge = MockBridge(source_chain, dest_chain, failure_rate=1.0)

    msg_id = failing_bridge.lock_and_mint("USDC", 100, "0xAlice")
    failing_bridge.relay_messages()

    assert not failing_bridge.is_relayed(msg_id), (
        "Message should not relay when failure_rate=1.0"
    )

    failing_bridge.failure_rate = 0.0
    failing_bridge.relay_messages()

    assert failing_bridge.is_relayed(msg_id), (
        "Message should relay after bridge recovers (failure_rate=0.0)"
    )
    assert failing_bridge.get_message(msg_id).relay_attempts >= 2
