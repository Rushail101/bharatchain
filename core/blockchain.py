"""
core/blockchain.py — Blockchain Backend
=========================================
Abstraction layer over 3 possible backends:
  1. "simulation" — in-memory chain, no external dependencies (start here)
  2. "ethereum"   — connects to local Ganache/Hardhat or public network via web3.py
  3. "fabric"     — connects to Hyperledger Fabric network

Set BLOCKCHAIN_BACKEND in .env to switch.
All modules call: from core.blockchain import blockchain
"""

import hashlib
import json
import logging
from datetime import datetime
from typing import Optional

from config import settings

logger = logging.getLogger("bharatchain.blockchain")


# ── Simulated Blockchain (default — works with zero setup) ────────────────────
class SimulatedChain:
    """
    In-memory blockchain simulation.
    Perfect for development — no Ganache, no Fabric, no Docker needed.
    Data resets when the server restarts (not persistent — use DB for persistence).
    """

    def __init__(self):
        self.blocks = []       # list of block dicts
        self.block_number = 0

    async def connect(self):
        logger.info("SimulatedChain: ready (in-memory mode)")
        # Genesis block
        self._mine_block("GENESIS", {"message": "BharatChain genesis block"})

    async def disconnect(self):
        logger.info("SimulatedChain: disconnected")

    async def ping(self) -> str:
        return f"ok — simulated chain, {len(self.blocks)} blocks"

    def _mine_block(self, block_type: str, data: dict) -> dict:
        prev_hash = self.blocks[-1]["hash"] if self.blocks else "0" * 64
        payload = json.dumps({
            "block_number": self.block_number,
            "block_type": block_type,
            "data": data,
            "prev_hash": prev_hash,
            "timestamp": datetime.utcnow().isoformat(),
        }, sort_keys=True)
        block_hash = hashlib.sha3_256(payload.encode()).hexdigest()
        block = {
            "block_number": self.block_number,
            "block_type": block_type,
            "data": data,
            "prev_hash": prev_hash,
            "hash": block_hash,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self.blocks.append(block)
        self.block_number += 1
        return block

    async def write_block(self, block_type: str, data: dict) -> dict:
        block = self._mine_block(block_type, data)
        logger.info(f"Block #{block['block_number']} written [{block_type}] hash={block['hash'][:16]}...")
        return block

    async def get_block(self, block_hash: str) -> Optional[dict]:
        for block in self.blocks:
            if block["hash"] == block_hash:
                return block
        return None

    async def get_all_blocks(self) -> list:
        return self.blocks


# ── Ethereum Backend ──────────────────────────────────────────────────────────
class EthereumChain:
    """
    Connects to a real Ethereum node (local Ganache or public testnet).
    Requires: WEB3_PROVIDER_URL and DEPLOYER_PRIVATE_KEY in .env
    """

    def __init__(self):
        self.w3 = None

    async def connect(self):
        try:
            from web3 import Web3
            self.w3 = Web3(Web3.HTTPProvider(settings.WEB3_PROVIDER_URL))
            if not self.w3.is_connected():
                raise ConnectionError(f"Cannot connect to {settings.WEB3_PROVIDER_URL}")
            logger.info(f"Ethereum connected — block #{self.w3.eth.block_number}")
        except ImportError:
            raise ImportError("web3 not installed. Run: pip install web3")

    async def disconnect(self):
        self.w3 = None

    async def ping(self) -> str:
        if self.w3 and self.w3.is_connected():
            return f"ok — Ethereum block #{self.w3.eth.block_number}"
        return "disconnected"

    async def write_block(self, block_type: str, data: dict) -> dict:
        """
        Writes a record hash to the Ethereum chain as a transaction.
        In production you'd call a deployed smart contract here.
        """
        if not self.w3:
            raise RuntimeError("Not connected to Ethereum")

        data_hash = hashlib.sha3_256(json.dumps(data, sort_keys=True).encode()).hexdigest()

        # Send transaction to chain (simplified — use a smart contract in production)
        account = self.w3.eth.account.from_key(settings.DEPLOYER_PRIVATE_KEY)
        tx = {
            "from": account.address,
            "to": account.address,
            "value": 0,
            "data": self.w3.to_hex(text=f"{block_type}:{data_hash}"),
            "gas": 21000,
            "gasPrice": self.w3.eth.gas_price,
            "nonce": self.w3.eth.get_transaction_count(account.address),
            "chainId": settings.CHAIN_ID,
        }
        signed = self.w3.eth.account.sign_transaction(tx, settings.DEPLOYER_PRIVATE_KEY)
        tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

        return {
            "block_type": block_type,
            "hash": receipt.transactionHash.hex(),
            "block_number": receipt.blockNumber,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def get_block(self, block_hash: str) -> Optional[dict]:
        if not self.w3:
            return None
        tx = self.w3.eth.get_transaction(block_hash)
        return dict(tx) if tx else None

    async def get_all_blocks(self) -> list:
        return []  # Not practical for Ethereum — query events instead


# ── Hyperledger Fabric Backend ────────────────────────────────────────────────
class FabricChain:
    """
    Connects to a Hyperledger Fabric network.
    Requires: fabric network profile and credentials.
    Best for enterprise / government deployments.
    """

    def __init__(self):
        self.client = None

    async def connect(self):
        logger.warning(
            "Fabric backend selected. Ensure network is running "
            "and FABRIC_NETWORK_PROFILE is configured."
        )
        # Fabric SDK connection would go here
        # from hfc.fabric import Client
        # self.client = Client(net_profile=settings.FABRIC_NETWORK_PROFILE)
        logger.info("Fabric: connection stub (implement with hfc-py SDK)")

    async def disconnect(self):
        self.client = None

    async def ping(self) -> str:
        return "fabric stub — implement with hfc-py SDK"

    async def write_block(self, block_type: str, data: dict) -> dict:
        logger.info(f"Fabric: invoke chaincode for {block_type}")
        # Implement: self.client.chaincode_invoke(...)
        return {
            "block_type": block_type,
            "hash": hashlib.sha3_256(json.dumps(data).encode()).hexdigest(),
            "timestamp": datetime.utcnow().isoformat(),
            "note": "Fabric stub — implement chaincode invoke",
        }

    async def get_block(self, block_hash: str) -> Optional[dict]:
        return None

    async def get_all_blocks(self) -> list:
        return []


# ── Factory — picks the right backend from .env ───────────────────────────────
def _create_blockchain():
    backend = settings.BLOCKCHAIN_BACKEND.lower()
    if backend == "ethereum":
        logger.info("Using Ethereum blockchain backend")
        return EthereumChain()
    elif backend == "fabric":
        logger.info("Using Hyperledger Fabric blockchain backend")
        return FabricChain()
    else:
        logger.info("Using Simulated blockchain backend (development mode)")
        return SimulatedChain()


# Singleton — import this everywhere:  from core.blockchain import blockchain
blockchain = _create_blockchain()
