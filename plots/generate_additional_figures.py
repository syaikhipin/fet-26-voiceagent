#!/usr/bin/env python3
"""
Generate additional figures for the enhanced IEEE paper
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

# Simple configuration — Type 1/42 fonts only (no Type 3)
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times', 'Times New Roman', 'DejaVu Serif']
plt.rcParams['font.size']  = 8
plt.rcParams['ps.fonttype'] = 42
plt.rcParams['pdf.fonttype'] = 42
plt.rcParams['ps.useafm'] = True

# Figure 5: MCP Caching Flowchart
fig, ax = plt.subplots(figsize=(3.5, 3.5))
ax.set_xlim(0, 10)
ax.set_ylim(0, 10)
ax.axis('off')

# Title
ax.text(5, 9.5, 'MCP Caching Flowchart', ha='center', fontsize=9, fontweight='bold')

# Client node
client_box = FancyBboxPatch((1, 7.5), 2, 0.8, boxstyle="round,pad=0.1", 
                            facecolor='#E7F3FF', edgecolor='black', linewidth=0.5)
ax.add_patch(client_box)
ax.text(2, 7.9, 'Client Query', ha='center', va='center', fontsize=7)

# MCP Middleware node
mcp_box = FancyBboxPatch((4, 7.5), 2, 0.8, boxstyle="round,pad=0.1",
                         facecolor='#FFF2CC', edgecolor='black', linewidth=0.5)
ax.add_patch(mcp_box)
ax.text(5, 7.9, 'MCP Middleware', ha='center', va='center', fontsize=7)

# Cache check
cache_box = FancyBboxPatch((4, 6.2), 2, 0.8, boxstyle="round,pad=0.1",
                           facecolor='#FFE6E6', edgecolor='black', linewidth=0.5)
ax.add_patch(cache_box)
ax.text(5, 6.6, 'Cache Check', ha='center', va='center', fontsize=7)

# Decision diamond
decision = mpatches.RegularPolygon((5, 5), numVertices=4, radius=0.4, 
                                   facecolor='#E6FFE6', edgecolor='black', linewidth=0.5)
ax.add_patch(decision)
ax.text(5, 5, 'Hit?', ha='center', va='center', fontsize=6)

# Cache hit path
hit_box = FancyBboxPatch((7, 4.2), 2, 0.8, boxstyle="round,pad=0.1",
                         facecolor='#E6FFE6', edgecolor='black', linewidth=0.5)
ax.add_patch(hit_box)
ax.text(8, 4.6, 'Return Cached\n+ Merkle Proof', ha='center', va='center', fontsize=6)

# Cache miss path
miss_box = FancyBboxPatch((1, 4.2), 2, 0.8, boxstyle="round,pad=0.1",
                          facecolor='#FFE6E6', edgecolor='black', linewidth=0.5)
ax.add_patch(miss_box)
ax.text(2, 4.6, 'Query Blockchain', ha='center', va='center', fontsize=7)

# Blockchain node
bc_box = FancyBboxPatch((1, 2.8), 2, 0.8, boxstyle="round,pad=0.1",
                        facecolor='#F8E1E1', edgecolor='black', linewidth=0.5)
ax.add_patch(bc_box)
ax.text(2, 3.2, 'Blockchain', ha='center', va='center', fontsize=7)

# Store in cache
store_box = FancyBboxPatch((4, 2.8), 2, 0.8, boxstyle="round,pad=0.1",
                           facecolor='#FFF2CC', edgecolor='black', linewidth=0.5)
ax.add_patch(store_box)
ax.text(5, 3.2, 'Store in Cache\n+ Generate Proof', ha='center', va='center', fontsize=6)

# Return to client
return_box = FancyBboxPatch((7, 2.8), 2, 0.8, boxstyle="round,pad=0.1",
                            facecolor='#E6FFE6', edgecolor='black', linewidth=0.5)
ax.add_patch(return_box)
ax.text(8, 3.2, 'Return to Client', ha='center', va='center', fontsize=7)

# Arrows
# Client to MCP
ax.arrow(3, 7.9, 0.9, 0, head_width=0.1, head_length=0.1, fc='black', ec='black', linewidth=0.5)

# MCP to Cache Check
ax.arrow(5, 7.5, 0, -1.2, head_width=0.1, head_length=0.1, fc='black', ec='black', linewidth=0.5)

# Cache Check to Decision
ax.arrow(5, 6.2, 0, -0.7, head_width=0.1, head_length=0.1, fc='black', ec='black', linewidth=0.5)

# Decision to Hit (YES)
ax.arrow(5.3, 4.7, 1.6, 0, head_width=0.1, head_length=0.1, fc='black', ec='black', linewidth=0.5)
ax.text(6, 4.9, 'YES', fontsize=5, ha='center')

# Decision to Miss (NO)
ax.arrow(4.7, 4.7, -1.6, 0, head_width=0.1, head_length=0.1, fc='black', ec='black', linewidth=0.5)
ax.text(4, 4.9, 'NO', fontsize=5, ha='center')

# Miss to Blockchain
ax.arrow(2, 4.2, 0, -0.5, head_width=0.1, head_length=0.1, fc='black', ec='black', linewidth=0.5)

# Blockchain to Store
ax.arrow(3, 3.2, 0.9, 0, head_width=0.1, head_length=0.1, fc='black', ec='black', linewidth=0.5)

# Store to Return
ax.arrow(6, 3.2, 0.9, 0, head_width=0.1, head_length=0.1, fc='black', ec='black', linewidth=0.5)

# Hit to Return
ax.arrow(8, 4.2, 0, -0.5, head_width=0.1, head_length=0.1, fc='black', ec='black', linewidth=0.5)

plt.savefig('fig5_mcp_flowchart.eps', format='eps')
plt.close()

# Figure 6: Contribution Diagram
fig, ax = plt.subplots(figsize=(3.5, 3.0))
ax.set_xlim(0, 10)
ax.set_ylim(0, 8)
ax.axis('off')

# Title
ax.text(5, 7.5, 'Key Contributions', ha='center', fontsize=9, fontweight='bold')

# Contribution 1: Verifiable Caching
contrib1_box = FancyBboxPatch((0.5, 5.5), 9, 0.9, boxstyle="round,pad=0.1",
                              facecolor='#E7F3FF', edgecolor='black', linewidth=0.5)
ax.add_patch(contrib1_box)
ax.text(5, 6.0, '1. Verifiable Caching: Merkle proof verification (5μs overhead)', 
         ha='center', va='center', fontsize=7)

# Contribution 2: Multi-Policy Caching
contrib2_box = FancyBboxPatch((0.5, 4.3), 9, 0.9, boxstyle="round,pad=0.1",
                              facecolor='#FFF2CC', edgecolor='black', linewidth=0.5)
ax.add_patch(contrib2_box)
ax.text(5, 4.8, '2. Multi-Policy Caching: LRU, LFU, ARC, Adaptive TTL (85.9% hit rate)', 
         ha='center', va='center', fontsize=7)

# Contribution 3: Write-Triggered Invalidation
contrib3_box = FancyBboxPatch((0.5, 3.1), 9, 0.9, boxstyle="round,pad=0.1",
                              facecolor='#FFE6E6', edgecolor='black', linewidth=0.5)
ax.add_patch(contrib3_box)
ax.text(5, 3.6, '3. Write-Triggered Invalidation: Zero stale reads vs 50 with TTL', 
         ha='center', va='center', fontsize=7)

# Contribution 4: Multi-Tenant Access Control
contrib4_box = FancyBboxPatch((0.5, 1.9), 9, 0.9, boxstyle="round,pad=0.1",
                              facecolor='#E6FFE6', edgecolor='black', linewidth=0.5)
ax.add_patch(contrib4_box)
ax.text(5, 2.4, '4. Multi-Tenant Access Control: RBAC, field filtering, audit logging', 
         ha='center', va='center', fontsize=7)

# Contribution 5: Comprehensive Evaluation
contrib5_box = FancyBboxPatch((0.5, 0.7), 9, 0.9, boxstyle="round,pad=0.1",
                              facecolor='#F8E1E1', edgecolor='black', linewidth=0.5)
ax.add_patch(contrib5_box)
ax.text(5, 1.2, '5. Comprehensive Evaluation: 4.09x speedup, 2,870 QPS, baseline comparisons', 
         ha='center', va='center', fontsize=7)

plt.savefig('fig6_contributions.eps', format='eps')
plt.close()

print("Additional figures generated successfully!")
print("Files created:")
print("- fig5_mcp_flowchart.eps")
print("- fig6_contributions.eps")