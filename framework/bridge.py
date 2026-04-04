import hashlib
import random
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .chain import MockChain


@dataclass
class BridgeMessage:
    msg_id: str
    token: str
    amount: int
    recipient: str
    direction: str  # "lock_and_mint" | "burn_and_release"
    source_block: int
    status: str = "pending"  # "pending" | "relayed" | "failed"
    relay_attempts: int = 0


class MockBridge:
    def __init__(
        self,
        source_chain: MockChain,
        dest_chain: MockChain,
        delay_blocks: int = 0,
        failure_rate: float = 0.0,
    ):
        self.source_chain = source_chain
        self.dest_chain = dest_chain
        self.delay_blocks = delay_blocks
        self.failure_rate = failure_rate

        # token -> (source_locked, dest_minted)
        self._locked: Dict[str, int] = {}
        self._minted: Dict[str, int] = {}
        self._messages: Dict[str, BridgeMessage] = {}
        self._relayed_ids: set = set()
        self._msg_counter = 0

        # Track per-token supply on each chain separately
        self._source_supply: Dict[str, int] = {}
        self._dest_supply: Dict[str, int] = {}

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def lock_and_mint(self, token: str, amount: int, recipient: str) -> str:
        if amount <= 0:
            raise ValueError("Amount must be positive")

        self._locked[token] = self._locked.get(token, 0) + amount
        self._source_supply[token] = self._source_supply.get(token, 0) + amount

        msg_id = self._new_msg_id("lm", token, amount, recipient)
        msg = BridgeMessage(
            msg_id=msg_id,
            token=token,
            amount=amount,
            recipient=recipient,
            direction="lock_and_mint",
            source_block=self.source_chain.block_number,
        )
        self._messages[msg_id] = msg
        return msg_id

    def burn_and_release(self, token: str, amount: int, recipient: str) -> str:
        minted = self._minted.get(token, 0)
        if amount > minted:
            raise ValueError(
                f"Cannot burn {amount} of {token}: only {minted} minted on dest chain"
            )
        if amount <= 0:
            raise ValueError("Amount must be positive")

        self._minted[token] = minted - amount
        self._dest_supply[token] = max(0, self._dest_supply.get(token, 0) - amount)

        msg_id = self._new_msg_id("br", token, amount, recipient)
        msg = BridgeMessage(
            msg_id=msg_id,
            token=token,
            amount=amount,
            recipient=recipient,
            direction="burn_and_release",
            source_block=self.dest_chain.block_number,
        )
        self._messages[msg_id] = msg
        return msg_id

    def get_pending_messages(self) -> List[BridgeMessage]:
        return [m for m in self._messages.values() if m.status == "pending"]

    def relay_messages(self) -> int:
        relayed = 0
        current_source_block = self.source_chain.block_number
        current_dest_block = self.dest_chain.block_number

        for msg in list(self._messages.values()):
            if msg.status != "pending":
                continue

            ref_block = (
                current_source_block
                if msg.direction == "lock_and_mint"
                else current_dest_block
            )
            if ref_block - msg.source_block < self.delay_blocks:
                continue

            msg.relay_attempts += 1

            if self.failure_rate > 0 and random.random() < self.failure_rate:
                continue

            if msg.msg_id in self._relayed_ids:
                msg.status = "failed"
                continue

            self._apply_relay(msg)
            self._relayed_ids.add(msg.msg_id)
            msg.status = "relayed"
            relayed += 1

        return relayed

    def is_relayed(self, msg_id: str) -> bool:
        msg = self._messages.get(msg_id)
        return msg is not None and msg.status == "relayed"

    def get_message(self, msg_id: str) -> Optional[BridgeMessage]:
        return self._messages.get(msg_id)

    def get_locked(self, token: str) -> int:
        return self._locked.get(token, 0)

    def get_minted(self, token: str) -> int:
        return self._minted.get(token, 0)

    def total_supply_on_source(self, token: str) -> int:
        return self._source_supply.get(token, 0)

    def total_supply_on_dest(self, token: str) -> int:
        return self._dest_supply.get(token, 0)

    # ------------------------------------------------------------------ #
    #  Internal helpers                                                    #
    # ------------------------------------------------------------------ #

    def _apply_relay(self, msg: BridgeMessage) -> None:
        if msg.direction == "lock_and_mint":
            self._minted[msg.token] = self._minted.get(msg.token, 0) + msg.amount
            self._dest_supply[msg.token] = (
                self._dest_supply.get(msg.token, 0) + msg.amount
            )
        else:
            locked = self._locked.get(msg.token, 0)
            self._locked[msg.token] = max(0, locked - msg.amount)
            self._source_supply[msg.token] = max(
                0, self._source_supply.get(msg.token, 0) - msg.amount
            )

    def _new_msg_id(self, prefix: str, token: str, amount: int, recipient: str) -> str:
        self._msg_counter += 1
        seed = f"{prefix}:{token}:{amount}:{recipient}:{self._msg_counter}:{time.time_ns()}"
        return "0x" + hashlib.sha256(seed.encode()).hexdigest()
