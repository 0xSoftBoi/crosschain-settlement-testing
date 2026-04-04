import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from framework.chain import MockChain
from framework.bridge import MockBridge


@pytest.fixture
def source_chain():
    chain = MockChain(1, "Ethereum")
    chain.set_balance("0xBridge", 10_000_000)
    return chain


@pytest.fixture
def dest_chain():
    chain = MockChain(10, "Optimism")
    chain.set_balance("0xBridge", 10_000_000)
    return chain


@pytest.fixture
def bridge(source_chain, dest_chain):
    return MockBridge(source_chain, dest_chain)
