"""
Baseline Comparison Systems for Blockchain Caching

Implements alternative approaches commonly used in blockchain ecosystems:
1. The Graph-style subgraph indexer
2. Event-driven materialized views
3. Database-backed mirrors
4. Direct blockchain access (no caching)

This addresses reviewer concerns about weak baselines and missing comparisons
to off-chain indexing solutions.
"""

import time
import sqlite3
import json
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from collections import defaultdict
import hashlib
import random


@dataclass
class TraceEvent:
    """Represents a trace event in the supply chain."""
    event_id: str
    product_id: str
    event_type: str  # 'harvest', 'process', 'ship', 'receive'
    timestamp: float
    location: str
    farm_id: str
    quality_score: float
    data: Dict[str, Any] = field(default_factory=dict)
    block_number: int = 0


class BlockchainSimulator:
    """
    Simulates blockchain behavior with configurable latency.
    Supports variable latency to test different network conditions.
    """

    def __init__(self, base_latency_ms: float = 50.0, latency_std: float = 10.0):
        self.base_latency_ms = base_latency_ms
        self.latency_std = latency_std
        self.events: Dict[str, TraceEvent] = {}
        self.events_by_product: Dict[str, List[TraceEvent]] = defaultdict(list)
        self.events_by_farm: Dict[str, List[TraceEvent]] = defaultdict(list)
        self.current_block: int = 0
        self.call_count: int = 0

    def _simulate_latency(self):
        """Simulate network latency."""
        latency = max(5, random.gauss(self.base_latency_ms, self.latency_std))
        time.sleep(latency / 1000.0)
        self.call_count += 1

    def add_event(self, event: TraceEvent) -> str:
        """Add an event to the blockchain."""
        self._simulate_latency()
        self.current_block += 1
        event.block_number = self.current_block

        self.events[event.event_id] = event
        self.events_by_product[event.product_id].append(event)
        self.events_by_farm[event.farm_id].append(event)

        return event.event_id

    def get_event(self, event_id: str) -> Optional[TraceEvent]:
        """Get a single event by ID."""
        self._simulate_latency()
        return self.events.get(event_id)

    def get_product_trace(self, product_id: str) -> List[TraceEvent]:
        """Get all events for a product."""
        self._simulate_latency()
        return self.events_by_product.get(product_id, [])

    def get_farm_events(self, farm_id: str) -> List[TraceEvent]:
        """Get all events for a farm."""
        self._simulate_latency()
        return self.events_by_farm.get(farm_id, [])

    def get_all_events(self) -> List[TraceEvent]:
        """Get all events (expensive operation)."""
        self._simulate_latency()
        return list(self.events.values())

    def compute_aggregate(self, agg_type: str, field: str = 'quality_score') -> float:
        """Compute aggregate over all events."""
        # This requires fetching all data - very expensive
        events = self.get_all_events()

        if not events:
            return 0.0

        values = [getattr(e, field) for e in events if hasattr(e, field)]

        if agg_type == 'avg':
            return sum(values) / len(values) if values else 0.0
        elif agg_type == 'sum':
            return sum(values)
        elif agg_type == 'count':
            return len(values)
        elif agg_type == 'min':
            return min(values) if values else 0.0
        elif agg_type == 'max':
            return max(values) if values else 0.0

        return 0.0

    def reset_stats(self):
        """Reset call counter."""
        self.call_count = 0


class QuerySystem(ABC):
    """Abstract base class for query systems."""

    @abstractmethod
    def get_product_trace(self, product_id: str) -> List[TraceEvent]:
        pass

    @abstractmethod
    def get_aggregate(self, agg_type: str, field: str = 'quality_score') -> float:
        pass

    @abstractmethod
    def on_new_event(self, event: TraceEvent):
        pass

    @abstractmethod
    def get_stats(self) -> Dict:
        pass


class DirectBlockchainAccess(QuerySystem):
    """
    Baseline: Direct blockchain access without any caching.
    Every query goes directly to the blockchain.
    """

    def __init__(self, blockchain: BlockchainSimulator):
        self.blockchain = blockchain
        self.query_count = 0
        self.total_latency = 0.0

    def get_product_trace(self, product_id: str) -> List[TraceEvent]:
        start = time.time()
        result = self.blockchain.get_product_trace(product_id)
        self.total_latency += time.time() - start
        self.query_count += 1
        return result

    def get_aggregate(self, agg_type: str, field: str = 'quality_score') -> float:
        start = time.time()
        result = self.blockchain.compute_aggregate(agg_type, field)
        self.total_latency += time.time() - start
        self.query_count += 1
        return result

    def on_new_event(self, event: TraceEvent):
        # No action needed - always reads from blockchain
        pass

    def get_stats(self) -> Dict:
        return {
            'name': 'DirectBlockchain',
            'query_count': self.query_count,
            'blockchain_calls': self.blockchain.call_count,
            'avg_latency_ms': (self.total_latency / self.query_count * 1000)
                              if self.query_count > 0 else 0,
            'cache_hit_rate': 0.0  # No caching
        }


class TheGraphStyleIndexer(QuerySystem):
    """
    Simulates The Graph-style subgraph indexing.

    Features:
    - Indexes blockchain events into a queryable database
    - Supports GraphQL-like queries
    - Maintains sync with blockchain
    - Provides fast reads at cost of indexing overhead
    """

    def __init__(self, blockchain: BlockchainSimulator):
        self.blockchain = blockchain

        # In-memory index (production would use PostgreSQL)
        self.product_index: Dict[str, List[TraceEvent]] = defaultdict(list)
        self.farm_index: Dict[str, List[TraceEvent]] = defaultdict(list)
        self.all_events: List[TraceEvent] = []

        # Aggregation caches
        self.agg_cache: Dict[str, float] = {}
        self.agg_dirty: bool = True

        # Stats
        self.query_count = 0
        self.index_operations = 0
        self.total_latency = 0.0
        self.last_indexed_block = 0

    def index_event(self, event: TraceEvent):
        """Index a new event."""
        self.product_index[event.product_id].append(event)
        self.farm_index[event.farm_id].append(event)
        self.all_events.append(event)
        self.agg_dirty = True
        self.index_operations += 1
        self.last_indexed_block = event.block_number

    def get_product_trace(self, product_id: str) -> List[TraceEvent]:
        start = time.time()

        # Fast index lookup (simulated ~1ms latency)
        time.sleep(0.001)
        result = self.product_index.get(product_id, [])

        self.total_latency += time.time() - start
        self.query_count += 1
        return result

    def get_aggregate(self, agg_type: str, field: str = 'quality_score') -> float:
        start = time.time()

        cache_key = f"{agg_type}:{field}"

        # Recompute if dirty
        if self.agg_dirty or cache_key not in self.agg_cache:
            time.sleep(0.005)  # Index scan latency

            values = [getattr(e, field) for e in self.all_events if hasattr(e, field)]

            if agg_type == 'avg':
                result = sum(values) / len(values) if values else 0.0
            elif agg_type == 'sum':
                result = sum(values)
            elif agg_type == 'count':
                result = float(len(values))
            elif agg_type == 'min':
                result = min(values) if values else 0.0
            elif agg_type == 'max':
                result = max(values) if values else 0.0
            else:
                result = 0.0

            self.agg_cache[cache_key] = result
            self.agg_dirty = False
        else:
            time.sleep(0.001)  # Cache hit latency
            result = self.agg_cache[cache_key]

        self.total_latency += time.time() - start
        self.query_count += 1
        return result

    def on_new_event(self, event: TraceEvent):
        """Handle new blockchain event."""
        self.index_event(event)

    def sync_from_blockchain(self):
        """Sync index with blockchain (initial or catch-up)."""
        events = self.blockchain.get_all_events()
        for event in events:
            if event.block_number > self.last_indexed_block:
                self.index_event(event)

    def get_stats(self) -> Dict:
        return {
            'name': 'TheGraphIndexer',
            'query_count': self.query_count,
            'index_operations': self.index_operations,
            'indexed_events': len(self.all_events),
            'avg_latency_ms': (self.total_latency / self.query_count * 1000)
                              if self.query_count > 0 else 0,
            'last_indexed_block': self.last_indexed_block
        }


class MaterializedViewSystem(QuerySystem):
    """
    Event-driven materialized views.

    Maintains pre-computed views that are updated incrementally
    when new events arrive. Similar to database materialized views
    but optimized for append-only blockchain data.
    """

    def __init__(self, blockchain: BlockchainSimulator):
        self.blockchain = blockchain

        # Materialized views
        self.product_traces: Dict[str, List[TraceEvent]] = defaultdict(list)
        self.farm_summaries: Dict[str, Dict] = {}
        self.global_stats: Dict[str, float] = {
            'count': 0,
            'quality_sum': 0.0,
            'quality_min': float('inf'),
            'quality_max': float('-inf')
        }

        # Stats
        self.query_count = 0
        self.view_updates = 0
        self.total_latency = 0.0

    def _update_views(self, event: TraceEvent):
        """Incrementally update materialized views."""
        # Update product trace view
        self.product_traces[event.product_id].append(event)

        # Update farm summary view
        if event.farm_id not in self.farm_summaries:
            self.farm_summaries[event.farm_id] = {
                'event_count': 0,
                'quality_sum': 0.0,
                'products': set()
            }

        summary = self.farm_summaries[event.farm_id]
        summary['event_count'] += 1
        summary['quality_sum'] += event.quality_score
        summary['products'].add(event.product_id)

        # Update global stats
        self.global_stats['count'] += 1
        self.global_stats['quality_sum'] += event.quality_score
        self.global_stats['quality_min'] = min(
            self.global_stats['quality_min'], event.quality_score
        )
        self.global_stats['quality_max'] = max(
            self.global_stats['quality_max'], event.quality_score
        )

        self.view_updates += 1

    def get_product_trace(self, product_id: str) -> List[TraceEvent]:
        start = time.time()

        # Direct view lookup (very fast)
        time.sleep(0.0005)  # 0.5ms
        result = self.product_traces.get(product_id, [])

        self.total_latency += time.time() - start
        self.query_count += 1
        return result

    def get_aggregate(self, agg_type: str, field: str = 'quality_score') -> float:
        start = time.time()

        # Pre-computed aggregates (very fast)
        time.sleep(0.0002)  # 0.2ms

        if field == 'quality_score':
            if agg_type == 'avg':
                count = self.global_stats['count']
                result = self.global_stats['quality_sum'] / count if count > 0 else 0.0
            elif agg_type == 'sum':
                result = self.global_stats['quality_sum']
            elif agg_type == 'count':
                result = float(self.global_stats['count'])
            elif agg_type == 'min':
                result = self.global_stats['quality_min']
            elif agg_type == 'max':
                result = self.global_stats['quality_max']
            else:
                result = 0.0
        else:
            result = 0.0

        self.total_latency += time.time() - start
        self.query_count += 1
        return result

    def on_new_event(self, event: TraceEvent):
        """Handle new event by updating views."""
        self._update_views(event)

    def get_stats(self) -> Dict:
        return {
            'name': 'MaterializedViews',
            'query_count': self.query_count,
            'view_updates': self.view_updates,
            'products_tracked': len(self.product_traces),
            'farms_tracked': len(self.farm_summaries),
            'avg_latency_ms': (self.total_latency / self.query_count * 1000)
                              if self.query_count > 0 else 0
        }


class DatabaseMirror(QuerySystem):
    """
    Database-backed mirror of blockchain data.

    Uses SQLite to store a copy of blockchain data with indexes
    for fast querying. Common pattern in production systems.
    """

    def __init__(self, blockchain: BlockchainSimulator, db_path: str = ':memory:'):
        self.blockchain = blockchain
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_schema()

        # Stats
        self.query_count = 0
        self.insert_count = 0
        self.total_latency = 0.0

    def _init_schema(self):
        """Initialize database schema."""
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                product_id TEXT,
                event_type TEXT,
                timestamp REAL,
                location TEXT,
                farm_id TEXT,
                quality_score REAL,
                block_number INTEGER,
                data TEXT
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_product ON events(product_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_farm ON events(farm_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_block ON events(block_number)')
        self.conn.commit()

    def _insert_event(self, event: TraceEvent):
        """Insert event into database."""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO events
            (event_id, product_id, event_type, timestamp, location, farm_id,
             quality_score, block_number, data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            event.event_id, event.product_id, event.event_type,
            event.timestamp, event.location, event.farm_id,
            event.quality_score, event.block_number, json.dumps(event.data)
        ))
        self.conn.commit()
        self.insert_count += 1

    def get_product_trace(self, product_id: str) -> List[TraceEvent]:
        start = time.time()

        cursor = self.conn.cursor()
        cursor.execute(
            'SELECT * FROM events WHERE product_id = ? ORDER BY timestamp',
            (product_id,)
        )
        rows = cursor.fetchall()

        result = []
        for row in rows:
            result.append(TraceEvent(
                event_id=row[0],
                product_id=row[1],
                event_type=row[2],
                timestamp=row[3],
                location=row[4],
                farm_id=row[5],
                quality_score=row[6],
                block_number=row[7],
                data=json.loads(row[8]) if row[8] else {}
            ))

        self.total_latency += time.time() - start
        self.query_count += 1
        return result

    def get_aggregate(self, agg_type: str, field: str = 'quality_score') -> float:
        start = time.time()

        cursor = self.conn.cursor()

        if agg_type == 'avg':
            cursor.execute(f'SELECT AVG({field}) FROM events')
        elif agg_type == 'sum':
            cursor.execute(f'SELECT SUM({field}) FROM events')
        elif agg_type == 'count':
            cursor.execute('SELECT COUNT(*) FROM events')
        elif agg_type == 'min':
            cursor.execute(f'SELECT MIN({field}) FROM events')
        elif agg_type == 'max':
            cursor.execute(f'SELECT MAX({field}) FROM events')
        else:
            return 0.0

        result = cursor.fetchone()[0] or 0.0

        self.total_latency += time.time() - start
        self.query_count += 1
        return float(result)

    def on_new_event(self, event: TraceEvent):
        """Handle new event."""
        self._insert_event(event)

    def sync_from_blockchain(self):
        """Sync database with blockchain."""
        events = self.blockchain.get_all_events()
        for event in events:
            self._insert_event(event)

    def get_stats(self) -> Dict:
        cursor = self.conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM events')
        event_count = cursor.fetchone()[0]

        return {
            'name': 'DatabaseMirror',
            'query_count': self.query_count,
            'insert_count': self.insert_count,
            'stored_events': event_count,
            'avg_latency_ms': (self.total_latency / self.query_count * 1000)
                              if self.query_count > 0 else 0
        }

    def close(self):
        """Close database connection."""
        self.conn.close()


class MCPCacheLayer(QuerySystem):
    """
    Our MCP-based caching layer for comparison.
    Implements the approach described in the paper.
    """

    def __init__(self, blockchain: BlockchainSimulator,
                 cache_capacity: int = 1000, ttl: float = 300.0):
        self.blockchain = blockchain
        self.cache_capacity = cache_capacity
        self.ttl = ttl

        # Simple LRU cache
        from collections import OrderedDict
        self.cache: OrderedDict = OrderedDict()
        self.cache_times: Dict[str, float] = {}

        # Stats
        self.query_count = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.total_latency = 0.0

    def _is_valid(self, key: str) -> bool:
        """Check if cache entry is valid."""
        if key not in self.cache:
            return False
        return (time.time() - self.cache_times[key]) < self.ttl

    def _cache_put(self, key: str, value: Any):
        """Put value in cache."""
        if len(self.cache) >= self.cache_capacity:
            self.cache.popitem(last=False)

        self.cache[key] = value
        self.cache_times[key] = time.time()
        self.cache.move_to_end(key)

    def _cache_get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if self._is_valid(key):
            self.cache.move_to_end(key)
            return self.cache[key]
        return None

    def get_product_trace(self, product_id: str) -> List[TraceEvent]:
        start = time.time()
        cache_key = f"trace:{product_id}"

        # Check cache
        cached = self._cache_get(cache_key)
        if cached is not None:
            self.cache_hits += 1
            time.sleep(0.0001)  # Cache access latency
        else:
            self.cache_misses += 1
            # Fetch from blockchain
            cached = self.blockchain.get_product_trace(product_id)
            self._cache_put(cache_key, cached)

        self.total_latency += time.time() - start
        self.query_count += 1
        return cached

    def get_aggregate(self, agg_type: str, field: str = 'quality_score') -> float:
        start = time.time()
        cache_key = f"agg:{agg_type}:{field}"

        # Check cache
        cached = self._cache_get(cache_key)
        if cached is not None:
            self.cache_hits += 1
            time.sleep(0.0001)
        else:
            self.cache_misses += 1
            cached = self.blockchain.compute_aggregate(agg_type, field)
            self._cache_put(cache_key, cached)

        self.total_latency += time.time() - start
        self.query_count += 1
        return cached

    def on_new_event(self, event: TraceEvent):
        """Invalidate affected cache entries."""
        # Invalidate product trace
        cache_key = f"trace:{event.product_id}"
        if cache_key in self.cache:
            del self.cache[cache_key]

        # Invalidate aggregates
        for key in list(self.cache.keys()):
            if key.startswith('agg:'):
                del self.cache[key]

    def get_stats(self) -> Dict:
        total = self.cache_hits + self.cache_misses
        return {
            'name': 'MCPCacheLayer',
            'query_count': self.query_count,
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'cache_hit_rate': self.cache_hits / total if total > 0 else 0,
            'blockchain_calls': self.blockchain.call_count,
            'avg_latency_ms': (self.total_latency / self.query_count * 1000)
                              if self.query_count > 0 else 0
        }


def run_baseline_comparison(num_products: int = 100,
                           num_queries: int = 500,
                           blockchain_latency_ms: float = 50.0):
    """
    Run comparison between all baseline systems.
    """
    print("=" * 70)
    print("BASELINE COMPARISON EXPERIMENT")
    print("=" * 70)
    print(f"Products: {num_products}, Queries: {num_queries}")
    print(f"Blockchain latency: {blockchain_latency_ms}ms")
    print()

    # Create blockchain
    blockchain = BlockchainSimulator(base_latency_ms=blockchain_latency_ms)

    # Generate test data
    print("Generating test data...")
    events = []
    for i in range(num_products):
        for event_type in ['harvest', 'process', 'ship', 'receive']:
            event = TraceEvent(
                event_id=f"EVT-{i}-{event_type}",
                product_id=f"PROD-{i:04d}",
                event_type=event_type,
                timestamp=time.time() + i * 3600,
                location=f"Location-{i % 10}",
                farm_id=f"FARM-{i % 20:02d}",
                quality_score=80 + random.random() * 20,
                data={'batch': f"BATCH-{i // 10}"}
            )
            events.append(event)
            blockchain.add_event(event)

    blockchain.reset_stats()
    print(f"Generated {len(events)} events")
    print()

    # Create systems
    systems = [
        DirectBlockchainAccess(blockchain),
        TheGraphStyleIndexer(blockchain),
        MaterializedViewSystem(blockchain),
        DatabaseMirror(blockchain),
        MCPCacheLayer(blockchain)
    ]

    # Initialize systems with existing data
    for system in systems:
        if hasattr(system, 'sync_from_blockchain'):
            system.sync_from_blockchain()
        for event in events:
            system.on_new_event(event)

    blockchain.reset_stats()

    # Generate query workload (Zipf distribution for realistic access pattern)
    def zipf_product_id(n, s=1.2):
        weights = [1.0 / (i ** s) for i in range(1, n + 1)]
        total = sum(weights)
        weights = [w / total for w in weights]
        idx = random.choices(range(n), weights=weights)[0]
        return f"PROD-{idx:04d}"

    # Run queries
    print("Running queries...")
    results = {}

    for system in systems:
        blockchain.reset_stats()
        start_time = time.time()

        # Point queries (80%)
        for _ in range(int(num_queries * 0.8)):
            product_id = zipf_product_id(num_products)
            system.get_product_trace(product_id)

        # Aggregation queries (20%)
        for _ in range(int(num_queries * 0.2)):
            agg_type = random.choice(['avg', 'count', 'min', 'max'])
            system.get_aggregate(agg_type)

        elapsed = time.time() - start_time
        stats = system.get_stats()
        stats['total_time'] = elapsed
        stats['throughput'] = num_queries / elapsed

        results[stats['name']] = stats

    # Print results
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)

    for name, stats in results.items():
        print(f"\n{name}:")
        print(f"  Avg Latency: {stats['avg_latency_ms']:.2f} ms")
        print(f"  Throughput: {stats['throughput']:.0f} queries/sec")
        if 'cache_hit_rate' in stats:
            print(f"  Cache Hit Rate: {stats['cache_hit_rate']:.1%}")
        if 'blockchain_calls' in stats:
            print(f"  Blockchain Calls: {stats['blockchain_calls']}")

    # Cleanup
    for system in systems:
        if hasattr(system, 'close'):
            system.close()

    return results


if __name__ == "__main__":
    results = run_baseline_comparison(
        num_products=100,
        num_queries=500,
        blockchain_latency_ms=50.0
    )
