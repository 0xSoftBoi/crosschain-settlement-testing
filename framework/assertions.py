from .bridge import MockBridge


def assert_total_supply_conserved(bridge: MockBridge, token: str) -> None:
    locked = bridge.get_locked(token)
    minted = bridge.get_minted(token)
    assert locked >= minted, (
        f"Supply invariant violated for {token}: "
        f"locked={locked} < minted={minted} — tokens were created out of thin air"
    )


def assert_message_delivered(
    bridge: MockBridge,
    msg_id: str,
    timeout_blocks: int,
) -> None:
    msg = bridge.get_message(msg_id)
    assert msg is not None, f"Message {msg_id} not found in bridge"

    if msg.status == "relayed":
        return

    source_block = (
        bridge.source_chain.block_number
        if msg.direction == "lock_and_mint"
        else bridge.dest_chain.block_number
    )
    blocks_elapsed = source_block - msg.source_block
    assert msg.status == "relayed", (
        f"Message {msg_id} not delivered after {blocks_elapsed} blocks "
        f"(timeout={timeout_blocks}, status={msg.status}, attempts={msg.relay_attempts})"
    )


def assert_no_double_spend(bridge: MockBridge, msg_id: str) -> None:
    msg = bridge.get_message(msg_id)
    assert msg is not None, f"Message {msg_id} not found in bridge"

    seen_count = sum(
        1 for mid in bridge._relayed_ids if mid == msg_id
    )
    assert seen_count <= 1, (
        f"Double spend detected: message {msg_id} was relayed {seen_count} times"
    )

    if msg.status == "relayed":
        relayed_count = sum(
            1 for m in bridge._messages.values()
            if m.msg_id == msg_id and m.status == "relayed"
        )
        assert relayed_count == 1, (
            f"Double spend: {relayed_count} relayed entries for {msg_id}"
        )
