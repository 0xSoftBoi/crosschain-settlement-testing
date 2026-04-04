# Cross-Chain Settlement Testing Framework

Automated testing framework for cross-chain bridges and settlement layers. No external nodes or RPC endpoints required — everything runs in-process with deterministic mock chains.

## What It Does

- **MockChain** — in-memory EVM-like chain with block production, balances, and tx receipts
- **MockBridge** — lock-and-mint / burn-and-release bridge with configurable relay delay and failure injection
- **Assertions** — supply conservation, message delivery, and double-spend checks
- **Test suites** — bridge security, multi-chain simulation, and settlement finality

## Install

```bash
git clone https://github.com/0xSoftBoi/crosschain-settlement-testing.git
cd crosschain-settlement-testing
pip install pytest
```

No other dependencies required for the core framework.

## Run Tests

```bash
pytest tests/ -v
```

## Example Output

```
tests/test_bridge_security.py::test_supply_conservation_after_transfer PASSED
tests/test_bridge_security.py::test_double_spend_prevention PASSED
tests/test_bridge_security.py::test_replay_attack_prevention PASSED
tests/test_bridge_security.py::test_bridge_with_delay PASSED
tests/test_multichain_sim.py::test_sequential_transfers PASSED
tests/test_multichain_sim.py::test_concurrent_transfers PASSED
tests/test_multichain_sim.py::test_bridge_failure_recovery PASSED
tests/test_settlement.py::test_settlement_finality PASSED
tests/test_settlement.py::test_settlement_with_reorg PASSED
tests/test_settlement.py::test_cross_chain_atomic_swap PASSED

10 passed in 0.16s
```

## Framework Overview

### `framework/chain.py` — MockChain

```python
from framework.chain import MockChain

chain = MockChain(chain_id=1, name="Ethereum")
chain.set_balance("0xAlice", 1_000_000)
receipt = chain.send_tx("0xAlice", "0xBob", 500)
chain.finalize_block()  # advances block number
print(chain.block_number)  # 1
```

### `framework/bridge.py` — MockBridge

```python
from framework.bridge import MockBridge

bridge = MockBridge(
    source_chain=eth,
    dest_chain=op,
    delay_blocks=6,       # finality delay
    failure_rate=0.1,     # 10% relay failure for chaos testing
)

msg_id = bridge.lock_and_mint("USDC", 1000, "0xRecipient")
for _ in range(6):
    eth.finalize_block()
bridge.relay_messages()
print(bridge.is_relayed(msg_id))  # True
```

### `framework/assertions.py` — Test Helpers

```python
from framework.assertions import (
    assert_total_supply_conserved,
    assert_message_delivered,
    assert_no_double_spend,
)

assert_total_supply_conserved(bridge, "USDC")
assert_message_delivered(bridge, msg_id, timeout_blocks=10)
assert_no_double_spend(bridge, msg_id)
```

## Test Suites

| File | What it covers |
|------|---------------|
| `tests/test_bridge_security.py` | Supply conservation, double-spend prevention, replay attacks, delay enforcement |
| `tests/test_multichain_sim.py` | A→B→C sequential transfers, concurrent transfers, failure + recovery |
| `tests/test_settlement.py` | Finality thresholds, reorg handling, atomic swap (both legs or neither) |

## Chaos Testing

Set `failure_rate` between 0.0 and 1.0 to inject random relay failures:

```python
bridge = MockBridge(source, dest, failure_rate=0.3)  # 30% failure rate
```

Set `delay_blocks` to simulate finality windows:

```python
bridge = MockBridge(source, dest, delay_blocks=12)  # 12-block finality
```

## License

MIT
