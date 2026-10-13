"""
Multiple Cache Eviction Policies for Blockchain Caching

Implements and compares:
1. LRU (Least Recently Used) - baseline
2. LFU (Least Frequently Used) - for stable popularity patterns
3. ARC (Adaptive Replacement Cache) - balances recency and frequency
4. Adaptive TTL - adjusts TTL based on access patterns and write frequency

This addresses reviewer concerns about comparing alternative caching policies.
"""

import time
import heapq
from abc import ABC, abstractmethod
from collections import OrderedDict, defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
import math


@dataclass
class CacheEntry:
    """Entry in the cache with metadata for various policies."""
    key: str
    value: Any
    created_at: float
    last_accessed: float
    access_count: int = 1
    ttl: float = 300.0  # seconds
    block_number: int = 0
    size: int = 1  # for weighted eviction

    def is_expired(self, current_time: float) -> bool:
        return (current_time - self.created_at) > self.ttl

    def time_since_access(self, current_time: float) -> float:
        return current_time - self.last_accessed


class CachePolicy(ABC):
    """Abstract base class for cache eviction policies."""

    def __init__(self, capacity: int):
        self.capacity = capacity
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'expirations': 0
        }

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        pass

    @abstractmethod
    def put(self, key: str, value: Any, ttl: float = 300.0, block_number: int = 0) -> None:
        pass

    @abstractmethod
    def invalidate(self, key: str) -> bool:
        pass

    @abstractmethod
    def size(self) -> int:
        pass

    def get_stats(self) -> Dict:
        total = self.stats['hits'] + self.stats['misses']
        return {
            **self.stats,
            'hit_rate': self.stats['hits'] / total if total > 0 else 0,
            'size': self.size(),
            'capacity': self.capacity
        }


class LRUCache(CachePolicy):
    """
    Least Recently Used cache.
    Evicts the entry that hasn't been accessed for the longest time.
    """

    def __init__(self, capacity: int):
        super().__init__(capacity)
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()

    def get(self, key: str) -> Optional[Any]:
        current_time = time.time()

        if key not in self.cache:
            self.stats['misses'] += 1
            return None

        entry = self.cache[key]

        # Check expiration
        if entry.is_expired(current_time):
            del self.cache[key]
            self.stats['expirations'] += 1
            self.stats['misses'] += 1
            return None

        # Move to end (most recently used)
        self.cache.move_to_end(key)
        entry.last_accessed = current_time
        entry.access_count += 1

        self.stats['hits'] += 1
        return entry.value

    def put(self, key: str, value: Any, ttl: float = 300.0, block_number: int = 0) -> None:
        current_time = time.time()

        if key in self.cache:
            # Update existing
            entry = self.cache[key]
            entry.value = value
            entry.last_accessed = current_time
            entry.created_at = current_time
            entry.ttl = ttl
            entry.block_number = block_number
            self.cache.move_to_end(key)
        else:
            # Evict if necessary
            while len(self.cache) >= self.capacity:
                self.cache.popitem(last=False)
                self.stats['evictions'] += 1

            # Add new entry
            self.cache[key] = CacheEntry(
                key=key,
                value=value,
                created_at=current_time,
                last_accessed=current_time,
                ttl=ttl,
                block_number=block_number
            )

    def invalidate(self, key: str) -> bool:
        if key in self.cache:
            del self.cache[key]
            return True
        return False

    def size(self) -> int:
        return len(self.cache)


class LFUCache(CachePolicy):
    """
    Least Frequently Used cache.
    Evicts the entry with the lowest access count.
    Better for workloads with stable popularity distributions.
    """

    def __init__(self, capacity: int):
        super().__init__(capacity)
        self.cache: Dict[str, CacheEntry] = {}
        self.freq_map: Dict[int, OrderedDict[str, None]] = defaultdict(OrderedDict)
        self.min_freq: int = 0

    def get(self, key: str) -> Optional[Any]:
        current_time = time.time()

        if key not in self.cache:
            self.stats['misses'] += 1
            return None

        entry = self.cache[key]

        # Check expiration
        if entry.is_expired(current_time):
            self._remove(key)
            self.stats['expirations'] += 1
            self.stats['misses'] += 1
            return None

        # Update frequency
        self._update_freq(key)
        entry.last_accessed = current_time

        self.stats['hits'] += 1
        return entry.value

    def _update_freq(self, key: str):
        entry = self.cache[key]
        old_freq = entry.access_count

        # Remove from old frequency list
        del self.freq_map[old_freq][key]
        if not self.freq_map[old_freq]:
            del self.freq_map[old_freq]
            if self.min_freq == old_freq:
                self.min_freq += 1

        # Add to new frequency list
        entry.access_count += 1
        self.freq_map[entry.access_count][key] = None

    def _remove(self, key: str):
        if key in self.cache:
            entry = self.cache[key]
            del self.freq_map[entry.access_count][key]
            if not self.freq_map[entry.access_count]:
                del self.freq_map[entry.access_count]
            del self.cache[key]

    def put(self, key: str, value: Any, ttl: float = 300.0, block_number: int = 0) -> None:
        current_time = time.time()

        if self.capacity <= 0:
            return

        if key in self.cache:
            entry = self.cache[key]
            entry.value = value
            entry.created_at = current_time
            entry.last_accessed = current_time
            entry.ttl = ttl
            entry.block_number = block_number
            self._update_freq(key)
        else:
            # Evict if necessary
            if len(self.cache) >= self.capacity:
                # Find and remove LFU entry
                lfu_keys = self.freq_map[self.min_freq]
                evict_key = next(iter(lfu_keys))
                self._remove(evict_key)
                self.stats['evictions'] += 1

            # Add new entry
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=current_time,
                last_accessed=current_time,
                access_count=1,
                ttl=ttl,
                block_number=block_number
            )
            self.cache[key] = entry
            self.freq_map[1][key] = None
            self.min_freq = 1

    def invalidate(self, key: str) -> bool:
        if key in self.cache:
            self._remove(key)
            return True
        return False

    def size(self) -> int:
        return len(self.cache)


class ARCCache(CachePolicy):
    """
    Adaptive Replacement Cache (ARC).
    Balances between recency (LRU) and frequency (LFU) adaptively.

    Maintains four lists:
    - T1: Recent entries (seen once recently)
    - T2: Frequent entries (seen multiple times recently)
    - B1: Ghost entries evicted from T1
    - B2: Ghost entries evicted from T2

    The parameter p adapts based on workload to balance T1 and T2.
    """

    def __init__(self, capacity: int):
        super().__init__(capacity)
        self.c = capacity  # Cache size

        # Main cache lists
        self.t1: OrderedDict[str, CacheEntry] = OrderedDict()  # Recent
        self.t2: OrderedDict[str, CacheEntry] = OrderedDict()  # Frequent

        # Ghost lists (store keys only, not values)
        self.b1: OrderedDict[str, None] = OrderedDict()
        self.b2: OrderedDict[str, None] = OrderedDict()

        # Adaptive parameter
        self.p: float = 0  # Target size for T1

    def get(self, key: str) -> Optional[Any]:
        current_time = time.time()

        # Check T1
        if key in self.t1:
            entry = self.t1[key]
            if entry.is_expired(current_time):
                del self.t1[key]
                self.stats['expirations'] += 1
                self.stats['misses'] += 1
                return None

            # Move from T1 to T2 (promote to frequent)
            del self.t1[key]
            entry.last_accessed = current_time
            entry.access_count += 1
            self.t2[key] = entry
            self.t2.move_to_end(key)

            self.stats['hits'] += 1
            return entry.value

        # Check T2
        if key in self.t2:
            entry = self.t2[key]
            if entry.is_expired(current_time):
                del self.t2[key]
                self.stats['expirations'] += 1
                self.stats['misses'] += 1
                return None

            # Move to end of T2
            entry.last_accessed = current_time
            entry.access_count += 1
            self.t2.move_to_end(key)

            self.stats['hits'] += 1
            return entry.value

        self.stats['misses'] += 1
        return None

    def put(self, key: str, value: Any, ttl: float = 300.0, block_number: int = 0) -> None:
        current_time = time.time()

        # Case 1: Key in T1 or T2 (update)
        if key in self.t1:
            entry = self.t1[key]
            entry.value = value
            entry.created_at = current_time
            entry.last_accessed = current_time
            entry.ttl = ttl
            entry.block_number = block_number
            # Move to T2
            del self.t1[key]
            self.t2[key] = entry
            return

        if key in self.t2:
            entry = self.t2[key]
            entry.value = value
            entry.created_at = current_time
            entry.last_accessed = current_time
            entry.ttl = ttl
            entry.block_number = block_number
            self.t2.move_to_end(key)
            return

        # Case 2: Key in B1 (ghost hit - was recently evicted from T1)
        if key in self.b1:
            # Adapt: increase p (favor recency)
            delta = max(1, len(self.b2) / max(1, len(self.b1)))
            self.p = min(self.c, self.p + delta)

            del self.b1[key]
            self._replace(key, in_b2=False)

            entry = CacheEntry(
                key=key, value=value, created_at=current_time,
                last_accessed=current_time, ttl=ttl, block_number=block_number
            )
            self.t2[key] = entry
            return

        # Case 3: Key in B2 (ghost hit - was recently evicted from T2)
        if key in self.b2:
            # Adapt: decrease p (favor frequency)
            delta = max(1, len(self.b1) / max(1, len(self.b2)))
            self.p = max(0, self.p - delta)

            del self.b2[key]
            self._replace(key, in_b2=True)

            entry = CacheEntry(
                key=key, value=value, created_at=current_time,
                last_accessed=current_time, ttl=ttl, block_number=block_number
            )
            self.t2[key] = entry
            return

        # Case 4: New key
        l1 = len(self.t1) + len(self.b1)
        l2 = len(self.t2) + len(self.b2)

        if l1 == self.c:
            if len(self.t1) < self.c:
                # Remove from B1
                if self.b1:
                    self.b1.popitem(last=False)
                self._replace(key, in_b2=False)
            else:
                # Remove from T1
                if self.t1:
                    self.t1.popitem(last=False)
                    self.stats['evictions'] += 1
        elif l1 < self.c and l1 + l2 >= self.c:
            if l1 + l2 >= 2 * self.c:
                # Remove from B2
                if self.b2:
                    self.b2.popitem(last=False)
            self._replace(key, in_b2=False)

        # Add to T1
        entry = CacheEntry(
            key=key, value=value, created_at=current_time,
            last_accessed=current_time, ttl=ttl, block_number=block_number
        )
        self.t1[key] = entry

    def _replace(self, key: str, in_b2: bool):
        """Replace a page from cache."""
        if self.t1 and (len(self.t1) > self.p or (in_b2 and len(self.t1) == self.p)):
            # Evict from T1
            old_key, _ = self.t1.popitem(last=False)
            self.b1[old_key] = None
            self.stats['evictions'] += 1
        elif self.t2:
            # Evict from T2
            old_key, _ = self.t2.popitem(last=False)
            self.b2[old_key] = None
            self.stats['evictions'] += 1

    def invalidate(self, key: str) -> bool:
        if key in self.t1:
            del self.t1[key]
            return True
        if key in self.t2:
            del self.t2[key]
            return True
        return False

    def size(self) -> int:
        return len(self.t1) + len(self.t2)


class AdaptiveTTLCache(CachePolicy):
    """
    Cache with adaptive TTL based on access patterns and write frequency.

    Key features:
    - TTL increases for frequently accessed entries
    - TTL decreases for entries in high-write-rate categories
    - Learns optimal TTL per key pattern

    This addresses reviewer concerns about fixed TTL limitations.
    """

    def __init__(self, capacity: int, base_ttl: float = 300.0,
                 min_ttl: float = 10.0, max_ttl: float = 3600.0):
        super().__init__(capacity)
        self.base_ttl = base_ttl
        self.min_ttl = min_ttl
        self.max_ttl = max_ttl

        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()

        # Track write rates per key prefix (e.g., "farm:", "product:")
        self.write_counts: Dict[str, int] = defaultdict(int)
        self.write_window_start: float = time.time()
        self.write_window_size: float = 60.0  # 1 minute window

        # Track access patterns
        self.access_history: Dict[str, List[float]] = defaultdict(list)

    def _get_prefix(self, key: str) -> str:
        """Extract prefix from key for category-based TTL."""
        if ':' in key:
            return key.split(':')[0]
        return 'default'

    def _calculate_adaptive_ttl(self, key: str) -> float:
        """
        Calculate adaptive TTL based on:
        1. Access frequency (more access = longer TTL)
        2. Write rate for category (more writes = shorter TTL)
        """
        current_time = time.time()
        prefix = self._get_prefix(key)

        # Reset write window if needed
        if current_time - self.write_window_start > self.write_window_size:
            self.write_counts.clear()
            self.write_window_start = current_time

        # Factor 1: Access frequency
        access_times = self.access_history.get(key, [])
        recent_accesses = [t for t in access_times if current_time - t < 300]
        access_factor = min(2.0, 1.0 + len(recent_accesses) * 0.1)

        # Factor 2: Write rate (inverse relationship)
        write_rate = self.write_counts.get(prefix, 0) / max(1, self.write_window_size)
        write_factor = max(0.5, 1.0 - write_rate * 0.1)

        # Calculate final TTL
        ttl = self.base_ttl * access_factor * write_factor
        return max(self.min_ttl, min(self.max_ttl, ttl))

    def get(self, key: str) -> Optional[Any]:
        current_time = time.time()

        if key not in self.cache:
            self.stats['misses'] += 1
            return None

        entry = self.cache[key]

        # Check expiration
        if entry.is_expired(current_time):
            del self.cache[key]
            self.stats['expirations'] += 1
            self.stats['misses'] += 1
            return None

        # Update access history
        self.access_history[key].append(current_time)
        # Keep only recent history
        self.access_history[key] = [
            t for t in self.access_history[key]
            if current_time - t < 300
        ][-100:]  # Keep max 100 entries

        # Move to end and update
        self.cache.move_to_end(key)
        entry.last_accessed = current_time
        entry.access_count += 1

        # Extend TTL based on access pattern
        new_ttl = self._calculate_adaptive_ttl(key)
        entry.ttl = new_ttl
        entry.created_at = current_time  # Reset TTL timer

        self.stats['hits'] += 1
        return entry.value

    def put(self, key: str, value: Any, ttl: float = None, block_number: int = 0) -> None:
        current_time = time.time()
        prefix = self._get_prefix(key)

        # Track write
        self.write_counts[prefix] += 1

        # Calculate adaptive TTL if not specified
        if ttl is None:
            ttl = self._calculate_adaptive_ttl(key)

        if key in self.cache:
            entry = self.cache[key]
            entry.value = value
            entry.created_at = current_time
            entry.last_accessed = current_time
            entry.ttl = ttl
            entry.block_number = block_number
            self.cache.move_to_end(key)
        else:
            # Evict if necessary
            while len(self.cache) >= self.capacity:
                self.cache.popitem(last=False)
                self.stats['evictions'] += 1

            self.cache[key] = CacheEntry(
                key=key,
                value=value,
                created_at=current_time,
                last_accessed=current_time,
                ttl=ttl,
                block_number=block_number
            )

    def invalidate(self, key: str) -> bool:
        if key in self.cache:
            del self.cache[key]
            return True
        return False

    def invalidate_by_prefix(self, prefix: str) -> int:
        """Invalidate all entries with given prefix."""
        keys_to_remove = [k for k in self.cache if k.startswith(prefix)]
        for key in keys_to_remove:
            del self.cache[key]
        return len(keys_to_remove)

    def size(self) -> int:
        return len(self.cache)

    def get_ttl_stats(self) -> Dict:
        """Get statistics about TTL distribution."""
        if not self.cache:
            return {'avg_ttl': 0, 'min_ttl': 0, 'max_ttl': 0}

        ttls = [e.ttl for e in self.cache.values()]
        return {
            'avg_ttl': sum(ttls) / len(ttls),
            'min_ttl': min(ttls),
            'max_ttl': max(ttls),
            'ttl_distribution': {
                '<60s': sum(1 for t in ttls if t < 60),
                '60-300s': sum(1 for t in ttls if 60 <= t < 300),
                '300-600s': sum(1 for t in ttls if 300 <= t < 600),
                '>600s': sum(1 for t in ttls if t >= 600)
            }
        }


def create_cache(policy: str, capacity: int, **kwargs) -> CachePolicy:
    """Factory function to create cache with specified policy."""
    policies = {
        'lru': LRUCache,
        'lfu': LFUCache,
        'arc': ARCCache,
        'adaptive': AdaptiveTTLCache
    }

    if policy.lower() not in policies:
        raise ValueError(f"Unknown policy: {policy}. Available: {list(policies.keys())}")

    return policies[policy.lower()](capacity, **kwargs)


# Testing
if __name__ == "__main__":
    import random

    print("Testing Cache Policies")
    print("=" * 60)

    # Create test workload with Zipf distribution
    num_keys = 1000
    num_requests = 10000

    # Zipf distribution (skewed access pattern)
    def zipf_key(n, s=1.5):
        weights = [1.0 / (i ** s) for i in range(1, n + 1)]
        total = sum(weights)
        weights = [w / total for w in weights]
        return random.choices(range(n), weights=weights)[0]

    # Test each policy
    for policy_name in ['lru', 'lfu', 'arc', 'adaptive']:
        cache = create_cache(policy_name, capacity=100)

        # Warm up
        for i in range(100):
            cache.put(f"key:{i}", f"value:{i}")

        # Run workload
        start_time = time.time()
        for _ in range(num_requests):
            key_id = zipf_key(num_keys)
            key = f"key:{key_id}"

            result = cache.get(key)
            if result is None:
                cache.put(key, f"value:{key_id}")

        elapsed = time.time() - start_time
        stats = cache.get_stats()

        print(f"\n{policy_name.upper()} Cache:")
        print(f"  Hit rate: {stats['hit_rate']:.2%}")
        print(f"  Evictions: {stats['evictions']}")
        print(f"  Throughput: {num_requests / elapsed:.0f} ops/sec")

        if policy_name == 'adaptive':
            ttl_stats = cache.get_ttl_stats()
            print(f"  Avg TTL: {ttl_stats['avg_ttl']:.1f}s")
