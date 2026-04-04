import hashlib
import time
from typing import Callable, Dict, List, Optional


class MockChain:
    def __init__(self, chain_id: int, name: str):
        self.chain_id = chain_id
        self.name = name
        self.block_number = 0
        self._balances: Dict[str, int] = {}
        self._contracts: Dict[str, str] = {}
        self._tx_log: List[dict] = []
        self._block_callbacks: List[Callable] = []
        self._contract_counter = 0

    def deploy_contract(self, bytecode: str) -> str:
        self._contract_counter += 1
        seed = f"{self.chain_id}:{self._contract_counter}:{bytecode[:16]}"
        address = "0x" + hashlib.sha256(seed.encode()).hexdigest()[:40]
        self._contracts[address] = bytecode
        return address

    def send_tx(
        self,
        from_addr: str,
        to_addr: str,
        value: int,
        data: bytes = b"",
    ) -> dict:
        sender_balance = self._balances.get(from_addr, 0)
        if sender_balance < value:
            raise ValueError(
                f"Insufficient balance: {sender_balance} < {value} for {from_addr}"
            )
        self._balances[from_addr] = sender_balance - value
        self._balances[to_addr] = self._balances.get(to_addr, 0) + value

        tx_seed = f"{self.chain_id}:{from_addr}:{to_addr}:{value}:{time.time_ns()}"
        tx_hash = "0x" + hashlib.sha256(tx_seed.encode()).hexdigest()

        receipt = {
            "tx_hash": tx_hash,
            "from": from_addr,
            "to": to_addr,
            "value": value,
            "data": data,
            "block_number": self.block_number,
            "status": 1,
            "chain_id": self.chain_id,
        }
        self._tx_log.append(receipt)
        return receipt

    def get_balance(self, addr: str) -> int:
        return self._balances.get(addr, 0)

    def set_balance(self, addr: str, amount: int) -> None:
        self._balances[addr] = amount

    def finalize_block(self) -> None:
        self.block_number += 1
        for cb in self._block_callbacks:
            cb(self.block_number)

    def on_block(self, callback: Callable) -> None:
        self._block_callbacks.append(callback)

    def get_tx(self, tx_hash: str) -> Optional[dict]:
        for tx in self._tx_log:
            if tx["tx_hash"] == tx_hash:
                return tx
        return None

    def __repr__(self) -> str:
        return f"MockChain(id={self.chain_id}, name={self.name!r}, block={self.block_number})"
