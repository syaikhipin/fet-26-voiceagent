"""
Write-Triggered Invalidation System for Blockchain Caching

Implements precise cache invalidation based on blockchain events rather than
fixed TTL expiration. This addresses reviewer concerns about:
1. Coarse invalidation degrading hit rates
2. Fixed TTL making freshness guarantees opaque
3. No incremental update mechanism for aggregations

Key features:
- Event-driven invalidation using blockchain event logs
- Bloom filters for efficient dependency tracking
- Incremental aggregation updates
- Precise invalidation scoping
"""

import hashlib
import time
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any, Callable, Tuple
from collections import defaultdict
import json
import math


class BloomFilter:
    """
    Bloom filter for efficient membership testing.
    Used to track which cache entries depend on which blockchain events.
    """

    def __init__(self, expected_items: int = 1000, false_positive_rate: float = 0.01):
        self.size = self._optimal_size(expected_items, false_positive_rate)
        self.hash_count = self._optimal_hash_count(self.size, expected_items)
        self.bit_array = [False] * self.size

    def _optimal_size(self, n: int, p: float) -> int:
        """Calculate optimal bit array size."""
        m = -(n * math.log(p)) / (math.log(2) ** 2)
        return int(m)

    def _optimal_hash_count(self, m: int, n: int) -> int:
        """Calculate optimal number of hash functions."""
        k = (m / n) * math.log(2)
        return max(1, int(k))

    def _hashes(self, item: str) -> List[int]:
        """Generate hash values for an item."""
        hashes = []
        for i in range(self.hash_count):
            h = hashlib.md5(f"{item}:{i}".encode()).hexdigest()
            hashes.append(int(h, 16) % self.size)
        return hashes

    def add(self, item: str):
        """Add item to filter."""
        for h in self._hashes(item):
            self.bit_array[h] = True

    def contains(self, item: str) -> bool:
        """Check if item might be in filter (may have false positives)."""
        return all(self.bit_array[h] for h in self._hashes(item))


@dataclass
class BlockchainEvent:
    """Represents a blockchain event that may trigger cache invalidation."""
    event_type: str  # e.g., 'TraceAdded', 'QualityUpdated', 'CertificationChanged'
    block_number: int
    transaction_hash: str
    timestamp: float
    data: Dict[str, Any]

    # Affected entities
    product_id: Optional[str] = None
    farm_id: Optional[str] = None
    batch_id: Optional[str] = None

    def get_affected_keys(self) -> Set[str]:
        """Generate cache keys that might be affected by this event."""
        keys = set()

        if self.product_id:
            keys.add(f"product:{self.product_id}")
            keys.add(f"trace:{self.product_id}")
            keys.add(f"history:{self.product_id}")

        if self.farm_id:
            keys.add(f"farm:{self.farm_id}")
            keys.add(f"farm_products:{self.farm_id}")
            keys.add(f"farm_stats:{self.farm_id}")

        if self.batch_id:
            keys.add(f"batch:{self.batch_id}")

        # Aggregation keys that might be affected
        keys.add("agg:total_products")
        keys.add("agg:quality_avg")

        if self.farm_id:
            keys.add(f"agg:farm_quality:{self.farm_id}")

        return keys


@dataclass
class CacheEntry:
    """Cache entry with dependency tracking."""
    key: str
    value: Any
    created_at: float
    block_number: int
    dependencies: Set[str] = field(default_factory=set)  # Keys this entry depends on
    is_aggregate: bool = False
    aggregate_components: List[str] = field(default_factory=list)  # For incremental updates


class DependencyTracker:
    """
    Tracks dependencies between cache entries and blockchain entities.
    Enables precise invalidation when blockchain events occur.
    """

    def __init__(self):
        # Map from entity (product_id, farm_id, etc.) to cache keys
        self.entity_to_keys: Dict[str, Set[str]] = defaultdict(set)

        # Map from cache key to entities it depends on
        self.key_to_entities: Dict[str, Set[str]] = defaultdict(set)

        # Bloom filter for quick negative lookups
        self.bloom = BloomFilter(expected_items=10000)

    def register_dependency(self, cache_key: str, entity_id: str):
        """Register that a cache key depends on an entity."""
        self.entity_to_keys[entity_id].add(cache_key)
        self.key_to_entities[cache_key].add(entity_id)
        self.bloom.add(entity_id)

    def get_affected_keys(self, entity_id: str) -> Set[str]:
        """Get all cache keys affected by changes to an entity."""
        # Quick check with bloom filter
        if not self.bloom.contains(entity_id):
            return set()

        return self.entity_to_keys.get(entity_id, set()).copy()

    def remove_key(self, cache_key: str):
        """Remove a cache key and its dependencies."""
        entities = self.key_to_entities.pop(cache_key, set())
        for entity_id in entities:
            self.entity_to_keys[entity_id].discard(cache_key)


class IncrementalAggregator:
    """
    Maintains aggregations incrementally rather than recomputing from scratch.

    Supports:
    - COUNT: Track count of items
    - SUM: Track running sum
    - AVG: Track sum and count for average
    - MIN/MAX: Track extremes (requires full recompute on deletion)
    """

    def __init__(self):
        self.aggregates: Dict[str, Dict[str, Any]] = {}

    def create_aggregate(self, name: str, agg_type: str):
        """Create a new aggregate tracker."""
        self.aggregates[name] = {
            'type': agg_type,
            'count': 0,
            'sum': 0.0,
            'min': float('inf'),
            'max': float('-inf'),
            'values': {},  # For precise tracking
            'last_updated': time.time()
        }

    def add_value(self, name: str, key: str, value: float):
        """Add a value to an aggregate."""
        if name not in self.aggregates:
            return

        agg = self.aggregates[name]
        old_value = agg['values'].get(key)

        if old_value is not None:
            # Update existing
            agg['sum'] -= old_value
            agg['sum'] += value
        else:
            # New value
            agg['count'] += 1
            agg['sum'] += value

        agg['values'][key] = value
        agg['min'] = min(agg['min'], value)
        agg['max'] = max(agg['max'], value)
        agg['last_updated'] = time.time()

    def remove_value(self, name: str, key: str):
        """Remove a value from an aggregate."""
        if name not in self.aggregates:
            return

        agg = self.aggregates[name]
        if key in agg['values']:
            old_value = agg['values'].pop(key)
            agg['count'] -= 1
            agg['sum'] -= old_value

            # Recompute min/max if needed
            if old_value == agg['min'] or old_value == agg['max']:
                if agg['values']:
                    agg['min'] = min(agg['values'].values())
                    agg['max'] = max(agg['values'].values())
                else:
                    agg['min'] = float('inf')
                    agg['max'] = float('-inf')

            agg['last_updated'] = time.time()

    def get_aggregate(self, name: str) -> Optional[Dict[str, Any]]:
        """Get current aggregate value."""
        if name not in self.aggregates:
            return None

        agg = self.aggregates[name]
        result = {
            'count': agg['count'],
            'sum': agg['sum'],
            'last_updated': agg['last_updated']
        }

        if agg['count'] > 0:
            result['avg'] = agg['sum'] / agg['count']
            result['min'] = agg['min']
            result['max'] = agg['max']

        return result


class WriteTriggeredCache:
    """
    Cache with write-triggered invalidation.

    Instead of relying on TTL expiration, this cache invalidates entries
    precisely when relevant blockchain events occur.
    """

    def __init__(self, capacity: int = 1000):
        self.capacity = capacity
        self.cache: Dict[str, CacheEntry] = {}
        self.dependency_tracker = DependencyTracker()
        self.aggregator = IncrementalAggregator()

        # Event handlers
        self.event_handlers: Dict[str, List[Callable]] = defaultdict(list)

        # Statistics
        self.stats = {
            'hits': 0,
            'misses': 0,
            'invalidations': 0,
            'incremental_updates': 0,
            'events_processed': 0
        }

        # Last processed block
        self.last_block: int = 0

    def register_event_handler(self, event_type: str, handler: Callable):
        """Register a handler for a specific event type."""
        self.event_handlers[event_type].append(handler)

    def put(self, key: str, value: Any, block_number: int,
            dependencies: Optional[Set[str]] = None,
            is_aggregate: bool = False) -> CacheEntry:
        """
        Store a value with dependency tracking.

        Args:
            key: Cache key
            value: Value to cache
            block_number: Block number when data was fetched
            dependencies: Entity IDs this entry depends on
            is_aggregate: Whether this is an aggregate value
        """
        # Evict if at capacity
        if len(self.cache) >= self.capacity and key not in self.cache:
            # Simple LRU eviction
            oldest_key = min(self.cache.keys(),
                           key=lambda k: self.cache[k].created_at)
            self._remove(oldest_key)

        entry = CacheEntry(
            key=key,
            value=value,
            created_at=time.time(),
            block_number=block_number,
            dependencies=dependencies or set(),
            is_aggregate=is_aggregate
        )

        self.cache[key] = entry

        # Register dependencies
        for entity_id in entry.dependencies:
            self.dependency_tracker.register_dependency(key, entity_id)

        return entry

    def get(self, key: str) -> Optional[Any]:
        """Get a value from cache."""
        if key not in self.cache:
            self.stats['misses'] += 1
            return None

        self.stats['hits'] += 1
        return self.cache[key].value

    def _remove(self, key: str):
        """Remove an entry and clean up dependencies."""
        if key in self.cache:
            self.dependency_tracker.remove_key(key)
            del self.cache[key]

    def process_event(self, event: BlockchainEvent):
        """
        Process a blockchain event and invalidate affected cache entries.

        This is the core of write-triggered invalidation.
        """
        self.stats['events_processed'] += 1
        self.last_block = max(self.last_block, event.block_number)

        # Find affected cache keys
        affected_keys = set()

        # Direct entity dependencies
        if event.product_id:
            affected_keys.update(
                self.dependency_tracker.get_affected_keys(f"product:{event.product_id}")
            )
        if event.farm_id:
            affected_keys.update(
                self.dependency_tracker.get_affected_keys(f"farm:{event.farm_id}")
            )
        if event.batch_id:
            affected_keys.update(
                self.dependency_tracker.get_affected_keys(f"batch:{event.batch_id}")
            )

        # Also check event-generated keys
        affected_keys.update(event.get_affected_keys() & set(self.cache.keys()))

        # Invalidate affected entries
        for key in affected_keys:
            if key in self.cache:
                entry = self.cache[key]

                # For aggregates, try incremental update first
                if entry.is_aggregate and self._try_incremental_update(key, event):
                    self.stats['incremental_updates'] += 1
                    continue

                # Otherwise, invalidate
                self._remove(key)
                self.stats['invalidations'] += 1

        # Call registered event handlers
        for handler in self.event_handlers.get(event.event_type, []):
            handler(event)

    def _try_incremental_update(self, key: str, event: BlockchainEvent) -> bool:
        """
        Try to update an aggregate incrementally instead of invalidating.

        Returns True if successful, False if full recompute needed.
        """
        if key not in self.cache:
            return False

        entry = self.cache[key]

        # Handle quality score updates
        if event.event_type == 'QualityUpdated' and 'quality_score' in event.data:
            if key.startswith('agg:quality'):
                # Update the aggregate
                entity_key = event.product_id or event.farm_id
                if entity_key:
                    self.aggregator.add_value(
                        key,
                        entity_key,
                        event.data['quality_score']
                    )

                    # Update cached value
                    new_agg = self.aggregator.get_aggregate(key)
                    if new_agg:
                        entry.value = new_agg
                        entry.created_at = time.time()
                        entry.block_number = event.block_number
                        return True

        # Handle count updates
        if event.event_type == 'TraceAdded':
            if key == 'agg:total_products':
                if isinstance(entry.value, dict) and 'count' in entry.value:
                    entry.value['count'] += 1
                    entry.created_at = time.time()
                    entry.block_number = event.block_number
                    return True

        return False

    def process_events_batch(self, events: List[BlockchainEvent]):
        """Process multiple events efficiently."""
        # Sort by block number
        events = sorted(events, key=lambda e: e.block_number)

        # Collect all affected keys first
        all_affected: Dict[str, List[BlockchainEvent]] = defaultdict(list)

        for event in events:
            affected_keys = event.get_affected_keys() & set(self.cache.keys())
            for key in affected_keys:
                all_affected[key].append(event)

        # Process each affected key once with the latest event
        for key, key_events in all_affected.items():
            latest_event = key_events[-1]

            if key in self.cache:
                entry = self.cache[key]

                if entry.is_aggregate:
                    # Apply all events incrementally
                    success = True
                    for event in key_events:
                        if not self._try_incremental_update(key, event):
                            success = False
                            break

                    if success:
                        self.stats['incremental_updates'] += len(key_events)
                        continue

                # Invalidate
                self._remove(key)
                self.stats['invalidations'] += 1

        self.stats['events_processed'] += len(events)
        if events:
            self.last_block = events[-1].block_number

    def get_invalidation_scope(self, event: BlockchainEvent) -> Dict[str, Any]:
        """
        Get detailed information about what would be invalidated by an event.
        Useful for debugging and understanding invalidation behavior.
        """
        affected_keys = event.get_affected_keys() & set(self.cache.keys())

        return {
            'event_type': event.event_type,
            'block_number': event.block_number,
            'affected_entities': {
                'product_id': event.product_id,
                'farm_id': event.farm_id,
                'batch_id': event.batch_id
            },
            'affected_cache_keys': list(affected_keys),
            'would_invalidate': len(affected_keys),
            'incremental_possible': sum(
                1 for k in affected_keys
                if k in self.cache and self.cache[k].is_aggregate
            )
        }

    def get_stats(self) -> Dict:
        """Get cache statistics."""
        total = self.stats['hits'] + self.stats['misses']
        return {
            **self.stats,
            'hit_rate': self.stats['hits'] / total if total > 0 else 0,
            'size': len(self.cache),
            'capacity': self.capacity,
            'last_block': self.last_block
        }


class EventWatcher:
    """
    Watches blockchain for events and triggers cache invalidation.
    Simulates integration with blockchain event subscription.
    """

    def __init__(self, cache: WriteTriggeredCache):
        self.cache = cache
        self.event_queue: List[BlockchainEvent] = []
        self.last_processed_block: int = 0

    def add_event(self, event: BlockchainEvent):
        """Add an event to the queue."""
        self.event_queue.append(event)

    def process_pending(self) -> int:
        """Process all pending events. Returns number processed."""
        if not self.event_queue:
            return 0

        # Sort by block number
        self.event_queue.sort(key=lambda e: e.block_number)

        # Process events
        count = len(self.event_queue)
        self.cache.process_events_batch(self.event_queue)

        self.last_processed_block = self.event_queue[-1].block_number
        self.event_queue.clear()

        return count


# Example usage and testing
if __name__ == "__main__":
    print("Testing Write-Triggered Invalidation")
    print("=" * 60)

    # Create cache
    cache = WriteTriggeredCache(capacity=1000)

    # Initialize aggregator
    cache.aggregator.create_aggregate('agg:quality_avg', 'avg')

    # Add some cached data
    cache.put(
        'product:PROD-001',
        {'name': 'Organic Tomatoes', 'quality': 95},
        block_number=1000,
        dependencies={'product:PROD-001', 'farm:FARM-A'}
    )

    cache.put(
        'farm_stats:FARM-A',
        {'total_products': 50, 'avg_quality': 92},
        block_number=1000,
        dependencies={'farm:FARM-A'},
        is_aggregate=True
    )

    cache.put(
        'agg:quality_avg',
        {'count': 100, 'sum': 9200, 'avg': 92},
        block_number=1000,
        dependencies={'global:quality'},
        is_aggregate=True
    )

    print(f"Initial cache size: {len(cache.cache)}")
    print(f"Product data: {cache.get('product:PROD-001')}")

    # Simulate blockchain event
    event = BlockchainEvent(
        event_type='QualityUpdated',
        block_number=1001,
        transaction_hash='0xabc123',
        timestamp=time.time(),
        data={'quality_score': 98},
        product_id='PROD-001',
        farm_id='FARM-A'
    )

    # Check what would be invalidated
    scope = cache.get_invalidation_scope(event)
    print(f"\nInvalidation scope for event:")
    print(f"  Affected keys: {scope['affected_cache_keys']}")
    print(f"  Would invalidate: {scope['would_invalidate']}")

    # Process the event
    cache.process_event(event)

    print(f"\nAfter event processing:")
    print(f"  Cache size: {len(cache.cache)}")
    print(f"  Product data: {cache.get('product:PROD-001')}")  # Should be None
    print(f"  Stats: {cache.get_stats()}")
