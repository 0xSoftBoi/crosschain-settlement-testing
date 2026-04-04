import pytest
from framework.chain import MockChain
from framework.bridge import MockBridge
from framework.assertions import assert_total_supply_conserved


FINALITY_BLOCKS = 6


def test_settlement_finality():
    source_chain = MockChain(1, "Ethereum")
    dest_chain = MockChain(10, "Optimism")
    bridge = MockBridge(source_chain, dest_chain, delay_blocks=FINALITY_BLOCKS)

    msg_id = bridge.lock_and_mint("ETH", 1000, "0xAlice")

    for _ in range(FINALITY_BLOCKS - 1):
        source_chain.finalize_block()
    bridge.relay_messages()
    assert not bridge.is_relayed(msg_id), (
        "Settlement should not be final before FINALITY_BLOCKS"
    )

    source_chain.finalize_block()
    bridge.relay_messages()
    assert bridge.is_relayed(msg_id), (
        "Settlement should be final after FINALITY_BLOCKS"
    )


def test_settlement_with_reorg():
    source_chain = MockChain(1, "Ethereum")
    dest_chain = MockChain(10, "Optimism")
    bridge = MockBridge(source_chain, dest_chain, delay_blocks=FINALITY_BLOCKS)

    # Message created at block 0
    msg_id = bridge.lock_and_mint("ETH", 500, "0xBob")
    assert bridge.get_message(msg_id).source_block == 0

    # Advance 4 blocks — not yet final (need 6)
    for _ in range(4):
        source_chain.finalize_block()
    bridge.relay_messages()
    assert not bridge.is_relayed(msg_id), "Not final before FINALITY_BLOCKS"

    # Simulate a reorg that rolls back 3 blocks (chain reverts to block 1)
    source_chain.block_number -= 3
    bridge.relay_messages()
    assert not bridge.is_relayed(msg_id), (
        "Should not finalize after reorg reduces block depth below threshold"
    )

    # Recover: advance enough blocks to clear finality threshold from block 0
    # Need block_number >= source_block + FINALITY_BLOCKS = 0 + 6 = 6
    # Currently at block 1, so advance 6 more → block 7
    for _ in range(FINALITY_BLOCKS):
        source_chain.finalize_block()
    bridge.relay_messages()
    assert bridge.is_relayed(msg_id), "Should finalize after recovering from reorg"


def test_cross_chain_atomic_swap():
    chain_a = MockChain(1, "Ethereum")
    chain_b = MockChain(10, "Optimism")

    bridge_a_to_b = MockBridge(chain_a, chain_b)
    bridge_b_to_a = MockBridge(chain_b, chain_a)

    alice_sends = bridge_a_to_b.lock_and_mint("ETH", 1000, "0xBob")
    bob_sends = bridge_b_to_a.lock_and_mint("USDC", 2000, "0xAlice")

    a_relayed = bridge_a_to_b.relay_messages()
    b_relayed = bridge_b_to_a.relay_messages()

    both_complete = bridge_a_to_b.is_relayed(alice_sends) and bridge_b_to_a.is_relayed(bob_sends)
    neither_complete = not bridge_a_to_b.is_relayed(alice_sends) and not bridge_b_to_a.is_relayed(bob_sends)

    assert both_complete or neither_complete, (
        "Atomic swap violated: one leg completed without the other. "
        f"ETH leg={bridge_a_to_b.is_relayed(alice_sends)}, "
        f"USDC leg={bridge_b_to_a.is_relayed(bob_sends)}"
    )

    assert both_complete, "Both legs of the atomic swap should complete"
    assert_total_supply_conserved(bridge_a_to_b, "ETH")
    assert_total_supply_conserved(bridge_b_to_a, "USDC")
