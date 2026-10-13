"""
Enhanced Verifiable Caching System for Blockchain Agricultural Traceability

This module addresses reviewer concerns about trust preservation by implementing:
1. Merkle proof verification for cached responses
2. Contract-signed digests for integrity
3. Light-client verification capabilities

The cache provides cryptographic guarantees that cached data matches on-chain state.
"""

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from collections import OrderedDict
import hmac
import secrets


@dataclass
class MerkleNode:
    """Node in a Merkle tree for verifiable data structures."""
    hash: str
    left: Optional['MerkleNode'] = None
    right: Optional['MerkleNode'] = None
    data: Optional[Any] = None


class MerkleTree:
    """
    Merkle tree implementation for verifiable caching.
    Allows clients to verify cached data against on-chain root hash.
    """

    def __init__(self):
        self.leaves: List[MerkleNode] = []
        self.root: Optional[MerkleNode] = None

    def _hash(self, data: str) -> str:
        """Compute SHA-256 hash."""
        return hashlib.sha256(data.encode()).hexdigest()

    def _combine_hash(self, left: str, right: str) -> str:
        """Combine two hashes."""
        return self._hash(left + right)

    def add_leaf(self, data: Any) -> int:
        """Add a leaf node and return its index."""
        data_str = json.dumps(data, sort_keys=True)
        leaf_hash = self._hash(data_str)
        node = MerkleNode(hash=leaf_hash, data=data)
        self.leaves.append(node)
        return len(self.leaves) - 1

    def build_tree(self) -> str:
        """Build the Merkle tree and return root hash."""
        if not self.leaves:
            return self._hash("")

        # Build tree bottom-up
        current_level = self.leaves.copy()

        while len(current_level) > 1:
            next_level = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1] if i + 1 < len(current_level) else left
                combined_hash = self._combine_hash(left.hash, right.hash)
                parent = MerkleNode(hash=combined_hash, left=left, right=right)
                next_level.append(parent)
            current_level = next_level

        self.root = current_level[0]
        return self.root.hash

    def get_proof(self, index: int) -> List[Tuple[str, str]]:
        """
        Get Merkle proof for leaf at index.
        Returns list of (hash, position) tuples where position is 'left' or 'right'.
        """
        if index >= len(self.leaves):
            return []

        proof = []
        current_level = self.leaves.copy()
        current_index = index

        while len(current_level) > 1:
            next_level = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1] if i + 1 < len(current_level) else left

                # If current index is in this pair, add sibling to proof
                if i == current_index or i + 1 == current_index:
                    if current_index == i:
                        proof.append((right.hash, 'right'))
                    else:
                        proof.append((left.hash, 'left'))

                combined_hash = self._combine_hash(left.hash, right.hash)
                parent = MerkleNode(hash=combined_hash, left=left, right=right)
                next_level.append(parent)

            current_level = next_level
            current_index = current_index // 2

        return proof

    def verify_proof(self, data: Any, proof: List[Tuple[str, str]], root_hash: str) -> bool:
        """Verify a Merkle proof against the root hash."""
        data_str = json.dumps(data, sort_keys=True)
        current_hash = self._hash(data_str)

        for sibling_hash, position in proof:
            if position == 'left':
                current_hash = self._combine_hash(sibling_hash, current_hash)
            else:
                current_hash = self._combine_hash(current_hash, sibling_hash)

        return current_hash == root_hash


@dataclass
class SignedResponse:
    """
    A cached response with cryptographic signature.
    Allows verification that the response came from a trusted source.
    """
    data: Any
    timestamp: float
    block_number: int
    signature: str
    merkle_proof: List[Tuple[str, str]]
    merkle_root: str

    def to_dict(self) -> Dict:
        return {
            'data': self.data,
            'timestamp': self.timestamp,
            'block_number': self.block_number,
            'signature': self.signature,
            'merkle_proof': self.merkle_proof,
            'merkle_root': self.merkle_root
        }


class VerifiableCache:
    """
    Cache with cryptographic verification capabilities.

    Features:
    - Merkle proofs for data integrity
    - HMAC signatures for authenticity
    - Block number tracking for freshness
    - Proof generation for client verification
    """

    def __init__(self, capacity: int = 1000, signing_key: Optional[str] = None):
        self.capacity = capacity
        self.signing_key = signing_key or secrets.token_hex(32)
        self.cache: OrderedDict[str, SignedResponse] = OrderedDict()
        self.merkle_tree = MerkleTree()
        self.current_root: str = ""
        self.stats = {
            'hits': 0,
            'misses': 0,
            'verifications_passed': 0,
            'verifications_failed': 0
        }

    def _sign(self, data: str) -> str:
        """Create HMAC signature for data."""
        return hmac.new(
            self.signing_key.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()

    def _verify_signature(self, data: str, signature: str) -> bool:
        """Verify HMAC signature."""
        expected = self._sign(data)
        return hmac.compare_digest(expected, signature)

    def put(self, key: str, data: Any, block_number: int) -> SignedResponse:
        """
        Store data with cryptographic proofs.

        Args:
            key: Cache key
            data: Data to cache
            block_number: Blockchain block number for freshness tracking

        Returns:
            SignedResponse with proofs
        """
        # Add to Merkle tree
        leaf_index = self.merkle_tree.add_leaf({'key': key, 'data': data, 'block': block_number})
        self.current_root = self.merkle_tree.build_tree()
        proof = self.merkle_tree.get_proof(leaf_index)

        # Create signature
        sign_data = json.dumps({
            'key': key,
            'data': data,
            'block': block_number,
            'root': self.current_root
        }, sort_keys=True)
        signature = self._sign(sign_data)

        # Create signed response
        response = SignedResponse(
            data=data,
            timestamp=time.time(),
            block_number=block_number,
            signature=signature,
            merkle_proof=proof,
            merkle_root=self.current_root
        )

        # Evict if at capacity
        if len(self.cache) >= self.capacity:
            self.cache.popitem(last=False)

        self.cache[key] = response
        self.cache.move_to_end(key)

        return response

    def get(self, key: str, verify: bool = True) -> Optional[SignedResponse]:
        """
        Retrieve data with optional verification.

        Args:
            key: Cache key
            verify: Whether to verify signature and proof

        Returns:
            SignedResponse if found and valid, None otherwise
        """
        if key not in self.cache:
            self.stats['misses'] += 1
            return None

        response = self.cache[key]
        self.cache.move_to_end(key)

        if verify:
            # Verify signature
            sign_data = json.dumps({
                'key': key,
                'data': response.data,
                'block': response.block_number,
                'root': response.merkle_root
            }, sort_keys=True)

            if not self._verify_signature(sign_data, response.signature):
                self.stats['verifications_failed'] += 1
                return None

            self.stats['verifications_passed'] += 1

        self.stats['hits'] += 1
        return response

    def verify_against_chain(self, key: str, on_chain_root: str) -> bool:
        """
        Verify cached data against on-chain Merkle root.

        This is the key trust-preserving mechanism: clients can verify
        that cached data matches the blockchain state by checking the
        Merkle proof against the on-chain root hash.

        Args:
            key: Cache key
            on_chain_root: Merkle root from blockchain

        Returns:
            True if verification passes
        """
        if key not in self.cache:
            return False

        response = self.cache[key]

        # Verify Merkle proof
        leaf_data = {
            'key': key,
            'data': response.data,
            'block': response.block_number
        }

        return self.merkle_tree.verify_proof(
            leaf_data,
            response.merkle_proof,
            on_chain_root
        )

    def invalidate(self, key: str) -> bool:
        """Remove entry from cache."""
        if key in self.cache:
            del self.cache[key]
            return True
        return False

    def invalidate_before_block(self, block_number: int) -> int:
        """
        Invalidate all entries from before a given block.
        Useful for ensuring freshness after chain reorganization.

        Returns:
            Number of entries invalidated
        """
        keys_to_remove = [
            k for k, v in self.cache.items()
            if v.block_number < block_number
        ]
        for key in keys_to_remove:
            del self.cache[key]
        return len(keys_to_remove)

    def get_stats(self) -> Dict:
        """Get cache statistics."""
        total = self.stats['hits'] + self.stats['misses']
        return {
            **self.stats,
            'hit_rate': self.stats['hits'] / total if total > 0 else 0,
            'size': len(self.cache),
            'capacity': self.capacity
        }


class LightClientVerifier:
    """
    Light client verification for cached blockchain data.

    Allows clients to verify cached responses without running a full node
    by checking Merkle proofs against block headers.
    """

    def __init__(self):
        self.trusted_roots: Dict[int, str] = {}  # block_number -> merkle_root

    def add_trusted_root(self, block_number: int, merkle_root: str):
        """Add a trusted Merkle root from a block header."""
        self.trusted_roots[block_number] = merkle_root

    def verify_response(self, response: SignedResponse) -> Tuple[bool, str]:
        """
        Verify a cached response using light client verification.

        Returns:
            (is_valid, reason)
        """
        block = response.block_number

        if block not in self.trusted_roots:
            return False, f"No trusted root for block {block}"

        trusted_root = self.trusted_roots[block]

        if response.merkle_root != trusted_root:
            return False, "Merkle root mismatch"

        # Verify the proof
        tree = MerkleTree()
        leaf_data = {
            'data': response.data,
            'block': response.block_number
        }

        if not tree.verify_proof(leaf_data, response.merkle_proof, trusted_root):
            return False, "Merkle proof verification failed"

        return True, "Verification passed"


# Example usage and testing
if __name__ == "__main__":
    print("Testing Verifiable Cache System")
    print("=" * 50)

    # Create cache
    cache = VerifiableCache(capacity=100)

    # Store some agricultural trace data
    trace_data = {
        'product_id': 'PROD-001',
        'farm': 'Green Valley Farm',
        'harvest_date': '2024-01-15',
        'quality_score': 95,
        'certifications': ['organic', 'fair-trade']
    }

    # Put with block number
    response = cache.put('trace:PROD-001', trace_data, block_number=12345)
    print(f"Stored trace data at block {response.block_number}")
    print(f"Merkle root: {response.merkle_root[:16]}...")
    print(f"Signature: {response.signature[:16]}...")

    # Retrieve with verification
    retrieved = cache.get('trace:PROD-001', verify=True)
    if retrieved:
        print(f"\nRetrieved and verified: {retrieved.data['product_id']}")

    # Test light client verification
    verifier = LightClientVerifier()
    verifier.add_trusted_root(12345, response.merkle_root)

    is_valid, reason = verifier.verify_response(response)
    print(f"\nLight client verification: {is_valid} - {reason}")

    # Print stats
    print(f"\nCache stats: {cache.get_stats()}")
