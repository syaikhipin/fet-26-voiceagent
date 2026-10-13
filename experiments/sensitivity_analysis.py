"""
Comprehensive Experiment Runner with Sensitivity Analysis

Implements sensitivity analyses for:
1. TTL values (10s to 3600s)
2. Cache capacity (100 to 10000 entries)
3. Request skew (Zipf exponents 0.5 to 2.0)
4. Cold-start behavior and hit-rate ramp-up
5. Blockchain latency sweep (5ms to 500ms)

Also includes concurrency benchmarks with p50/p95/p99 latencies.

This addresses reviewer concerns about missing sensitivity analyses.
"""

import time
import random
import statistics
import threading
import concurrent.futures
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict
import json
import math

# Import our modules
from cache_policies import LRUCache, LFUCache, ARCCache, AdaptiveTTLCache, create_cache
from baseline_comparisons import (
    BlockchainSimulator, TraceEvent, DirectBlockchainAccess,
    TheGraphStyleIndexer, MaterializedViewSystem, MCPCacheLayer
)


@dataclass
class LatencyStats:
    """Statistics for latency measurements."""
    samples: List[float] = field(default_factory=list)

    def add(self, latency_ms: float):
        self.samples.append(latency_ms)

    def percentile(self, p: float) -> float:
        if not self.samples:
            return 0.0
        sorted_samples = sorted(self.samples)
        idx = int(len(sorted_samples) * p / 100)
        return sorted_samples[min(idx, len(sorted_samples) - 1)]

    @property
    def p50(self) -> float:
        return self.percentile(50)

    @property
    def p95(self) -> float:
        return self.percentile(95)

    @property
    def p99(self) -> float:
        return self.percentile(99)

    @property
    def mean(self) -> float:
        return statistics.mean(self.samples) if self.samples else 0.0

    @property
    def std(self) -> float:
        return statistics.stdev(self.samples) if len(self.samples) > 1 else 0.0

    def to_dict(self) -> Dict:
        return {
            'count': len(self.samples),
            'mean': self.mean,
            'std': self.std,
            'p50': self.p50,
            'p95': self.p95,
            'p99': self.p99,
            'min': min(self.samples) if self.samples else 0,
            'max': max(self.samples) if self.samples else 0
        }


class ExperimentRunner:
    """Runs comprehensive experiments with various configurations."""

    def __init__(self, num_products: int = 100, base_blockchain_latency: float = 50.0):
        self.num_products = num_products
        self.base_blockchain_latency = base_blockchain_latency
        self.results: Dict[str, Any] = {}

    def _generate_events(self, blockchain: BlockchainSimulator) -> List[TraceEvent]:
        """Generate test events."""
        events = []
        for i in range(self.num_products):
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
        return events

    def _zipf_product_id(self, n: int, s: float = 1.2) -> str:
        """Generate product ID with Zipf distribution."""
        weights = [1.0 / (i ** s) for i in range(1, n + 1)]
        total = sum(weights)
        weights = [w / total for w in weights]
        idx = random.choices(range(n), weights=weights)[0]
        return f"PROD-{idx:04d}"

    def run_ttl_sensitivity(self, ttl_values: List[float] = None) -> Dict:
        """
        Test sensitivity to TTL values.
        """
        if ttl_values is None:
            ttl_values = [10, 30, 60, 120, 300, 600, 1800, 3600]

        print("\n" + "=" * 60)
        print("TTL SENSITIVITY ANALYSIS")
        print("=" * 60)

        results = {}

        for ttl in ttl_values:
            print(f"\nTesting TTL = {ttl}s...")

            blockchain = BlockchainSimulator(base_latency_ms=self.base_blockchain_latency)
            events = self._generate_events(blockchain)
            blockchain.reset_stats()

            cache = MCPCacheLayer(blockchain, cache_capacity=1000, ttl=ttl)
            for event in events:
                cache.on_new_event(event)

            # Run queries
            latencies = LatencyStats()
            num_queries = 500

            for _ in range(num_queries):
                product_id = self._zipf_product_id(self.num_products)
                start = time.time()
                cache.get_product_trace(product_id)
                latencies.add((time.time() - start) * 1000)

            stats = cache.get_stats()
            results[ttl] = {
                'ttl': ttl,
                'hit_rate': stats['cache_hit_rate'],
                'avg_latency_ms': stats['avg_latency_ms'],
                'latency_stats': latencies.to_dict(),
                'blockchain_calls': stats['blockchain_calls']
            }

            print(f"  Hit rate: {stats['cache_hit_rate']:.1%}")
            print(f"  Avg latency: {stats['avg_latency_ms']:.2f}ms")

        self.results['ttl_sensitivity'] = results
        return results

    def run_cache_size_sensitivity(self, sizes: List[int] = None) -> Dict:
        """
        Test sensitivity to cache capacity.
        """
        if sizes is None:
            sizes = [50, 100, 250, 500, 1000, 2500, 5000, 10000]

        print("\n" + "=" * 60)
        print("CACHE SIZE SENSITIVITY ANALYSIS")
        print("=" * 60)

        results = {}

        for size in sizes:
            print(f"\nTesting cache size = {size}...")

            blockchain = BlockchainSimulator(base_latency_ms=self.base_blockchain_latency)
            events = self._generate_events(blockchain)
            blockchain.reset_stats()

            cache = MCPCacheLayer(blockchain, cache_capacity=size, ttl=300)
            for event in events:
                cache.on_new_event(event)

            # Run queries
            num_queries = 500
            for _ in range(num_queries):
                product_id = self._zipf_product_id(self.num_products)
                cache.get_product_trace(product_id)

            stats = cache.get_stats()
            results[size] = {
                'cache_size': size,
                'hit_rate': stats['cache_hit_rate'],
                'avg_latency_ms': stats['avg_latency_ms'],
                'blockchain_calls': stats['blockchain_calls']
            }

            print(f"  Hit rate: {stats['cache_hit_rate']:.1%}")
            print(f"  Avg latency: {stats['avg_latency_ms']:.2f}ms")

        self.results['cache_size_sensitivity'] = results
        return results

    def run_zipf_skew_sensitivity(self, skew_values: List[float] = None) -> Dict:
        """
        Test sensitivity to request skew (Zipf exponent).
        Higher values = more skewed (popular items get more requests).
        """
        if skew_values is None:
            skew_values = [0.5, 0.8, 1.0, 1.2, 1.5, 1.8, 2.0]

        print("\n" + "=" * 60)
        print("ZIPF SKEW SENSITIVITY ANALYSIS")
        print("=" * 60)

        results = {}

        for skew in skew_values:
            print(f"\nTesting Zipf skew = {skew}...")

            blockchain = BlockchainSimulator(base_latency_ms=self.base_blockchain_latency)
            events = self._generate_events(blockchain)
            blockchain.reset_stats()

            cache = MCPCacheLayer(blockchain, cache_capacity=1000, ttl=300)
            for event in events:
                cache.on_new_event(event)

            # Run queries with specified skew
            num_queries = 500
            for _ in range(num_queries):
                product_id = self._zipf_product_id(self.num_products, s=skew)
                cache.get_product_trace(product_id)

            stats = cache.get_stats()
            results[skew] = {
                'zipf_skew': skew,
                'hit_rate': stats['cache_hit_rate'],
                'avg_latency_ms': stats['avg_latency_ms'],
                'blockchain_calls': stats['blockchain_calls']
            }

            print(f"  Hit rate: {stats['cache_hit_rate']:.1%}")
            print(f"  Avg latency: {stats['avg_latency_ms']:.2f}ms")

        self.results['zipf_skew_sensitivity'] = results
        return results

    def run_cold_start_analysis(self, num_queries: int = 1000) -> Dict:
        """
        Analyze cold-start behavior and hit-rate ramp-up.
        """
        print("\n" + "=" * 60)
        print("COLD START ANALYSIS")
        print("=" * 60)

        blockchain = BlockchainSimulator(base_latency_ms=self.base_blockchain_latency)
        events = self._generate_events(blockchain)
        blockchain.reset_stats()

        cache = MCPCacheLayer(blockchain, cache_capacity=1000, ttl=300)
        # Don't pre-populate - start cold

        # Track hit rate over time
        window_size = 50
        hit_rates = []
        latencies = []
        hits_in_window = 0
        queries_in_window = 0

        for i in range(num_queries):
            product_id = self._zipf_product_id(self.num_products)

            # Check if this will be a hit
            cache_key = f"trace:{product_id}"
            is_hit = cache._is_valid(cache_key)

            start = time.time()
            cache.get_product_trace(product_id)
            latency = (time.time() - start) * 1000

            if is_hit:
                hits_in_window += 1
            queries_in_window += 1

            # Record window stats
            if (i + 1) % window_size == 0:
                hit_rates.append({
                    'query_number': i + 1,
                    'hit_rate': hits_in_window / queries_in_window
                })
                latencies.append({
                    'query_number': i + 1,
                    'avg_latency_ms': latency
                })
                hits_in_window = 0
                queries_in_window = 0

        results = {
            'hit_rate_progression': hit_rates,
            'latency_progression': latencies,
            'final_stats': cache.get_stats()
        }

        print(f"Initial hit rate (first {window_size}): {hit_rates[0]['hit_rate']:.1%}")
        print(f"Final hit rate (last {window_size}): {hit_rates[-1]['hit_rate']:.1%}")
        print(f"Queries to reach 50% hit rate: ", end="")

        for hr in hit_rates:
            if hr['hit_rate'] >= 0.5:
                print(f"{hr['query_number']}")
                break
        else:
            print("Never reached")

        self.results['cold_start'] = results
        return results

    def run_latency_sweep(self, latencies: List[float] = None) -> Dict:
        """
        Test with different blockchain latencies.
        """
        if latencies is None:
            latencies = [5, 15, 25, 50, 100, 200, 500]

        print("\n" + "=" * 60)
        print("BLOCKCHAIN LATENCY SWEEP")
        print("=" * 60)

        results = {}

        for latency in latencies:
            print(f"\nTesting blockchain latency = {latency}ms...")

            blockchain = BlockchainSimulator(base_latency_ms=latency)
            events = self._generate_events(blockchain)
            blockchain.reset_stats()

            # Test both direct and cached
            direct = DirectBlockchainAccess(blockchain)
            blockchain.reset_stats()

            cache = MCPCacheLayer(blockchain, cache_capacity=1000, ttl=300)
            for event in events:
                cache.on_new_event(event)
            blockchain.reset_stats()

            num_queries = 200

            # Direct queries
            direct_latencies = LatencyStats()
            for _ in range(num_queries):
                product_id = self._zipf_product_id(self.num_products)
                start = time.time()
                direct.get_product_trace(product_id)
                direct_latencies.add((time.time() - start) * 1000)

            blockchain.reset_stats()

            # Cached queries
            cached_latencies = LatencyStats()
            for _ in range(num_queries):
                product_id = self._zipf_product_id(self.num_products)
                start = time.time()
                cache.get_product_trace(product_id)
                cached_latencies.add((time.time() - start) * 1000)

            cache_stats = cache.get_stats()

            results[latency] = {
                'blockchain_latency_ms': latency,
                'direct_latency': direct_latencies.to_dict(),
                'cached_latency': cached_latencies.to_dict(),
                'speedup': direct_latencies.mean / cached_latencies.mean if cached_latencies.mean > 0 else 0,
                'cache_hit_rate': cache_stats['cache_hit_rate']
            }

            print(f"  Direct avg: {direct_latencies.mean:.2f}ms")
            print(f"  Cached avg: {cached_latencies.mean:.2f}ms")
            print(f"  Speedup: {results[latency]['speedup']:.2f}x")

        self.results['latency_sweep'] = results
        return results

    def run_cache_policy_comparison(self) -> Dict:
        """
        Compare different cache eviction policies.
        """
        print("\n" + "=" * 60)
        print("CACHE POLICY COMPARISON")
        print("=" * 60)

        policies = ['lru', 'lfu', 'arc', 'adaptive']
        results = {}

        for policy_name in policies:
            print(f"\nTesting {policy_name.upper()} policy...")

            cache = create_cache(policy_name, capacity=500)

            # Warm up with some data
            for i in range(100):
                cache.put(f"key:{i}", f"value:{i}")

            # Run workload
            num_queries = 2000
            hits = 0

            for _ in range(num_queries):
                key_id = self._zipf_product_id(self.num_products, s=1.2).replace('PROD-', '')
                key = f"key:{key_id}"

                result = cache.get(key)
                if result is not None:
                    hits += 1
                else:
                    cache.put(key, f"value:{key_id}")

            stats = cache.get_stats()
            results[policy_name] = {
                'policy': policy_name,
                'hit_rate': stats['hit_rate'],
                'evictions': stats['evictions'],
                'expirations': stats.get('expirations', 0)
            }

            print(f"  Hit rate: {stats['hit_rate']:.1%}")
            print(f"  Evictions: {stats['evictions']}")

        self.results['policy_comparison'] = results
        return results

    def run_concurrency_benchmark(self, num_threads: List[int] = None) -> Dict:
        """
        Benchmark concurrent access with p50/p95/p99 latencies.
        """
        if num_threads is None:
            num_threads = [1, 2, 4, 8, 16, 32]

        print("\n" + "=" * 60)
        print("CONCURRENCY BENCHMARK")
        print("=" * 60)

        results = {}

        for threads in num_threads:
            print(f"\nTesting with {threads} concurrent threads...")

            blockchain = BlockchainSimulator(base_latency_ms=self.base_blockchain_latency)
            events = self._generate_events(blockchain)
            blockchain.reset_stats()

            cache = MCPCacheLayer(blockchain, cache_capacity=1000, ttl=300)
            for event in events:
                cache.on_new_event(event)

            latencies = LatencyStats()
            queries_per_thread = 100
            lock = threading.Lock()

            def worker():
                local_latencies = []
                for _ in range(queries_per_thread):
                    product_id = self._zipf_product_id(self.num_products)
                    start = time.time()
                    cache.get_product_trace(product_id)
                    local_latencies.append((time.time() - start) * 1000)

                with lock:
                    for lat in local_latencies:
                        latencies.add(lat)

            # Run concurrent queries
            start_time = time.time()
            with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
                futures = [executor.submit(worker) for _ in range(threads)]
                concurrent.futures.wait(futures)
            elapsed = time.time() - start_time

            total_queries = threads * queries_per_thread
            throughput = total_queries / elapsed

            results[threads] = {
                'threads': threads,
                'total_queries': total_queries,
                'elapsed_seconds': elapsed,
                'throughput_qps': throughput,
                'latency': latencies.to_dict()
            }

            print(f"  Throughput: {throughput:.0f} queries/sec")
            print(f"  p50: {latencies.p50:.2f}ms, p95: {latencies.p95:.2f}ms, p99: {latencies.p99:.2f}ms")

        self.results['concurrency'] = results
        return results

    def run_all_experiments(self) -> Dict:
        """Run all sensitivity analyses and benchmarks."""
        print("\n" + "=" * 70)
        print("RUNNING COMPREHENSIVE EXPERIMENT SUITE")
        print("=" * 70)

        self.run_ttl_sensitivity()
        self.run_cache_size_sensitivity()
        self.run_zipf_skew_sensitivity()
        self.run_cold_start_analysis()
        self.run_latency_sweep()
        self.run_cache_policy_comparison()
        self.run_concurrency_benchmark()

        return self.results

    def save_results(self, filepath: str):
        """Save results to JSON file."""
        with open(filepath, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        print(f"\nResults saved to {filepath}")


if __name__ == "__main__":
    runner = ExperimentRunner(num_products=100, base_blockchain_latency=50.0)
    results = runner.run_all_experiments()
    runner.save_results('experiment_results.json')

    print("\n" + "=" * 70)
    print("EXPERIMENT SUMMARY")
    print("=" * 70)

    # Print key findings
    if 'ttl_sensitivity' in results:
        best_ttl = max(results['ttl_sensitivity'].items(),
                      key=lambda x: x[1]['hit_rate'])
        print(f"\nBest TTL: {best_ttl[0]}s (hit rate: {best_ttl[1]['hit_rate']:.1%})")

    if 'cache_size_sensitivity' in results:
        # Find knee point
        sizes = sorted(results['cache_size_sensitivity'].keys())
        for i, size in enumerate(sizes[:-1]):
            curr_hr = results['cache_size_sensitivity'][size]['hit_rate']
            next_hr = results['cache_size_sensitivity'][sizes[i+1]]['hit_rate']
            if next_hr - curr_hr < 0.02:  # Less than 2% improvement
                print(f"Cache size knee point: {size} entries")
                break

    if 'policy_comparison' in results:
        best_policy = max(results['policy_comparison'].items(),
                         key=lambda x: x[1]['hit_rate'])
        print(f"Best cache policy: {best_policy[0]} (hit rate: {best_policy[1]['hit_rate']:.1%})")

    if 'concurrency' in results:
        max_throughput = max(results['concurrency'].items(),
                            key=lambda x: x[1]['throughput_qps'])
        print(f"Max throughput: {max_throughput[1]['throughput_qps']:.0f} QPS at {max_throughput[0]} threads")
