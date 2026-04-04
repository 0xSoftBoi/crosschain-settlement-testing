import pytest
from framework.bridge import MockBridge
from framework.chain import MockChain
from framework.assertions import (
    assert_total_supply_conserved,
    assert_message_delivered,
    assert_no_double_spend,
)


def test_supply_conservation_after_transfer(bridge, source_chain, dest_chain):
    initial_locked = bridge.get_locked("USDC")
    initial_minted = bridge.get_minted("USDC")

    msg_id = bridge.lock_and_mint("USDC", 100, "0xRecipient")

    assert bridge.get_locked("USDC") == initial_locked + 100

    bridge.relay_messages()

    assert bridge.get_minted("USDC") == initial_minted + 100
    assert_total_supply_conserved(bridge, "USDC")

    assert bridge.get_locked("USDC") >= bridge.get_minted("USDC")


def test_double_spend_prevention(bridge, source_chain, dest_chain):
    msg_id = bridge.lock_and_mint("USDC", 100, "0xRecipient")
    bridge.relay_messages()

    assert bridge.is_relayed(msg_id)

    original_minted = bridge.get_minted("USDC")

    # Simulate a second relay attempt with the same msg_id (attacker re-submits proof).
    # The bridge must reject it because msg_id is in _relayed_ids.
    duplicate_msg = bridge._messages[msg_id]
    duplicate_msg.status = "pending"

    # Re-relay; bridge should detect msg_id already in _relayed_ids and skip.
    bridge.relay_messages()

    assert bridge.get_minted("USDC") == original_minted, (
        "Minted amount increased — double spend succeeded (should not happen)"
    )
    assert_no_double_spend(bridge, msg_id)


def test_replay_attack_prevention(bridge, source_chain, dest_chain):
    msg_id = bridge.lock_and_mint("USDC", 100, "0xRecipient")
    bridge.relay_messages()

    assert bridge.is_relayed(msg_id)
    minted_after_first = bridge.get_minted("USDC")

    bridge._messages[msg_id].status = "pending"
    bridge.relay_messages()

    assert bridge.get_minted("USDC") == minted_after_first, (
        "Replaying an old message should not increase minted supply"
    )
    assert msg_id in bridge._relayed_ids, "msg_id should stay in relayed set"


def test_bridge_with_delay(source_chain, dest_chain):
    delayed_bridge = MockBridge(source_chain, dest_chain, delay_blocks=3)
    msg_id = delayed_bridge.lock_and_mint("ETH", 50, "0xAlice")

    delayed_bridge.relay_messages()
    assert not delayed_bridge.is_relayed(msg_id), (
        "Message should not relay before delay_blocks have passed"
    )

    for _ in range(3):
        source_chain.finalize_block()

    delayed_bridge.relay_messages()
    assert delayed_bridge.is_relayed(msg_id), (
        "Message should be relayed after delay_blocks have passed"
    )

    assert_message_delivered(delayed_bridge, msg_id, timeout_blocks=5)
