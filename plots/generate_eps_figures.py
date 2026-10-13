#!/usr/bin/env python3
"""
Generate EPS figures for the enhanced IEEE paper - Simplified version
"""

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
import json
import os

# Simple configuration — Type 1/42 fonts only (no Type 3)
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times', 'Times New Roman', 'DejaVu Serif']
plt.rcParams['font.size'] = 8
plt.rcParams['axes.linewidth'] = 0.5
plt.rcParams['ps.fonttype'] = 42       # TrueType outlines in EPS
plt.rcParams['pdf.fonttype'] = 42      # TrueType outlines in PDF
plt.rcParams['ps.useafm'] = True       # Use AFM (Type 1) font metrics
plt.rcParams['text.usetex'] = False    # Avoid bitmap CM fonts

# Load results (path resolved relative to this script: plots/../experiments/results/)
_RESULTS_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    '..', 'experiments', 'results', 'comprehensive_results.json')
with open(_RESULTS_PATH, 'r') as f:
    results = json.load(f)

# Figure 1: Latency Comparison
fig, ax = plt.subplots(figsize=(3.5, 2.2))

methods = ['Direct\nBlockchain', 'MCP Cached']
point_latencies = [51.48, 22.89]
agg_latencies = [501.36, 50.13]

x = np.arange(len(methods))
width = 0.35

bars1 = ax.bar(x - width/2, point_latencies, width, label='Point Queries', 
               color='#4472C4', edgecolor='black', linewidth=0.5)
bars2 = ax.bar(x + width/2, agg_latencies, width, label='Aggregation Queries', 
               color='#ED7D31', edgecolor='black', linewidth=0.5)

ax.set_ylabel('Latency (ms)')
ax.set_title('Query Latency Comparison')
ax.set_xticks(x)
ax.set_xticklabels(methods)
ax.legend(loc='upper left', frameon=True, fancybox=False, shadow=False)
ax.grid(True, alpha=0.3, axis='y')
ax.set_ylim(0, 550)

# Add value labels on bars
for bar in bars1:
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height + 10,
            f'{height:.1f}', ha='center', va='bottom', fontsize=6)

for bar in bars2:
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height + 10,
            f'{height:.1f}', ha='center', va='bottom', fontsize=6)

plt.savefig('fig1_latency_comparison.eps', format='eps')
plt.close()

# Figure 2: Blockchain Calls Reduction
fig, ax = plt.subplots(figsize=(3.5, 2.2))

query_types = ['Point Queries', 'Aggregation Queries']
direct_calls = [150, 1000]
cached_calls = [66, 100]

x = np.arange(len(query_types))
width = 0.35

bars1 = ax.bar(x - width/2, direct_calls, width, label='Direct Blockchain',
               color='#C55A5A', edgecolor='black', linewidth=0.5)
bars2 = ax.bar(x + width/2, cached_calls, width, label='MCP Cached',
               color='#70AD47', edgecolor='black', linewidth=0.5)

ax.set_ylabel('Number of Calls')
ax.set_title('Blockchain RPC Call Reduction')
ax.set_xticks(x)
ax.set_xticklabels(query_types)
ax.legend(loc='upper right', frameon=True, fancybox=False, shadow=False)
ax.grid(True, alpha=0.3, axis='y')

# Add value labels
for bar in bars1:
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height + 15,
            f'{int(height)}', ha='center', va='bottom', fontsize=6)

for bar in bars2:
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height + 5,
            f'{int(height)}', ha='center', va='bottom', fontsize=6)

plt.savefig('fig2_blockchain_calls.eps', format='eps')
plt.close()

# Figure 3: Cache Performance
fig, ax = plt.subplots(figsize=(3.5, 2.2))

policies = ['LRU', 'LFU', 'ARC', 'Adaptive']
hit_rates = [83.7, 85.9, 85.5, 84.8]
colors = ['#4472C4', '#ED7D31', '#70AD47', '#FFC000']

bars = ax.bar(policies, hit_rates, color=colors, edgecolor='black', linewidth=0.5)

ax.set_ylabel('Hit Rate (%)')
ax.set_title('Cache Policy Performance (Zipf s=1.2)')
ax.grid(True, alpha=0.3, axis='y')
ax.set_ylim(80, 90)

# Add value labels
for bar, rate in zip(bars, hit_rates):
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
            f'{rate:.1f}%', ha='center', va='bottom', fontsize=7, fontweight='bold')

plt.savefig('fig3_cache_performance.eps', format='eps')
plt.close()

# Figure 4: Architecture Diagram (conceptual)
fig, ax = plt.subplots(figsize=(3.5, 2.5))

# Create a simple block diagram
ax.set_xlim(0, 10)
ax.set_ylim(0, 8)
ax.axis('off')

# Client layer
ax.text(5, 7.5, 'Client Applications', ha='center', fontsize=9, fontweight='bold')
ax.add_patch(plt.Rectangle((1, 6.5), 2, 0.8, facecolor='#E7F3FF', 
                          edgecolor='black', linewidth=0.5))
ax.text(2, 6.9, 'Mobile App', ha='center', fontsize=7)
ax.add_patch(plt.Rectangle((4, 6.5), 2, 0.8, facecolor='#E7F3FF',
                          edgecolor='black', linewidth=0.5))
ax.text(5, 6.9, 'Web Portal', ha='center', fontsize=7)
ax.add_patch(plt.Rectangle((7, 6.5), 2, 0.8, facecolor='#E7F3FF',
                          edgecolor='black', linewidth=0.5))
ax.text(8, 6.9, 'API Client', ha='center', fontsize=7)

# MCP Middleware layer
ax.text(5, 5.5, 'MCP Middleware Layer', ha='center', fontsize=9, fontweight='bold')
ax.add_patch(plt.Rectangle((2, 4), 6, 1.2, facecolor='#FFF2CC',
                          edgecolor='black', linewidth=0.5))
ax.text(5, 4.8, 'Verifiable Cache with Merkle Proofs', ha='center', fontsize=8)

# Arrows
ax.arrow(2, 6.5, 0, -1.2, head_width=0.1, head_length=0.1, 
         fc='black', ec='black', linewidth=0.5)
ax.arrow(5, 6.5, 0, -1.2, head_width=0.1, head_length=0.1,
         fc='black', ec='black', linewidth=0.5)
ax.arrow(8, 6.5, 0, -1.2, head_width=0.1, head_length=0.1,
         fc='black', ec='black', linewidth=0.5)

# Blockchain layer
ax.text(5, 3.2, 'Blockchain Layer', ha='center', fontsize=9, fontweight='bold')
ax.add_patch(plt.Rectangle((2.5, 1.5), 5, 1.2, facecolor='#F8E1E1',
                          edgecolor='black', linewidth=0.5))
ax.text(5, 2.3, 'Smart Contracts & Trace Events', ha='center', fontsize=8)

# Arrow down
ax.arrow(5, 4, 0, -1.3, head_width=0.1, head_length=0.1,
         fc='black', ec='black', linewidth=0.5)

# Labels
ax.text(0.5, 5.5, 'Fast Path\n(< 1ms)', ha='center', fontsize=6,
        bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.5))
ax.text(9.5, 5.5, 'Slow Path\n(50-500ms)', ha='center', fontsize=6,
        bbox=dict(boxstyle='round', facecolor='lightcoral', alpha=0.5))

ax.set_title('Three-Layer Hybrid Architecture', fontsize=9, pad=10)

plt.savefig('fig4_architecture.eps', format='eps')
plt.close()

print("All EPS figures generated successfully!")
print("Files created:")
print("- fig1_latency_comparison.eps")
print("- fig2_blockchain_calls.eps") 
print("- fig3_cache_performance.eps")
print("- fig4_architecture.eps")
