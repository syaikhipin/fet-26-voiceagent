#!/usr/bin/env python3
"""
Generate a comprehensive, high-quality figure for the enhanced IEEE paper
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, Rectangle, FancyArrowPatch
import numpy as np

# High-quality configuration
plt.rcParams.update({
    'font.family': 'serif',
    'font.serif': ['Times', 'Times New Roman', 'DejaVu Serif'],
    'font.size': 9,
    'axes.titlesize': 10,
    'axes.labelsize': 9,
    'xtick.labelsize': 8,
    'ytick.labelsize': 8,
    'legend.fontsize': 8,
    'figure.titlesize': 11,
    'axes.linewidth': 1.0,
    'grid.linewidth': 0.5,
    'lines.linewidth': 1.5,
    'patch.linewidth': 1.0,
    'text.usetex': False,
    'ps.fonttype': 42,
    'pdf.fonttype': 42,
    'ps.useafm': True,
})

fig, ax = plt.subplots(figsize=(7, 5))
ax.set_xlim(0, 14)
ax.set_ylim(0, 10)
ax.axis('off')

# Title
ax.text(7, 9.5, 'MCP-Enhanced Verifiable Caching Architecture', 
        ha='center', fontsize=11, fontweight='bold')

# Layer 1: Client Applications
ax.text(7, 8.8, 'Client Applications', ha='center', fontsize=9, fontweight='bold')

client1 = FancyBboxPatch((1, 7.8), 3.5, 0.6, boxstyle="round,pad=0.05",
                         facecolor='#E3F2FD', edgecolor='#1976D2', linewidth=1.0)
ax.add_patch(client1)
ax.text(2.75, 8.1, 'Mobile App', ha='center', va='center', fontsize=8)

client2 = FancyBboxPatch((5.25, 7.8), 3.5, 0.6, boxstyle="round,pad=0.05",
                         facecolor='#E3F2FD', edgecolor='#1976D2', linewidth=1.0)
ax.add_patch(client2)
ax.text(7, 8.1, 'Web Portal', ha='center', va='center', fontsize=8)

client3 = FancyBboxPatch((9.5, 7.8), 3.5, 0.6, boxstyle="round,pad=0.05",
                         facecolor='#E3F2FD', edgecolor='#1976D2', linewidth=1.0)
ax.add_patch(client3)
ax.text(11.25, 8.1, 'API Client', ha='center', va='center', fontsize=8)

# Arrow down
ax.arrow(7, 7.8, 0, -0.3, head_width=0.15, head_length=0.1, 
         fc='#333333', ec='#333333', linewidth=1.5)

# Layer 2: MCP Middleware
ax.text(7, 7.2, 'MCP Middleware Layer', ha='center', fontsize=9, fontweight='bold')

# Cache component
cache_box = FancyBboxPatch((1, 5.5), 5.5, 1.3, boxstyle="round,pad=0.08",
                           facecolor='#FFF3E0', edgecolor='#F57C00', linewidth=1.0)
ax.add_patch(cache_box)
ax.text(3.75, 6.5, 'Verifiable Cache', ha='center', fontsize=9, fontweight='bold')
ax.text(3.75, 6.2, '• Merkle Proof Generation', ha='center', fontsize=7)
ax.text(3.75, 6.0, '• Multi-Policy (LRU/LFU/ARC/Adaptive)', ha='center', fontsize=7)
ax.text(3.75, 5.8, '• Write-Triggered Invalidation', ha='center', fontsize=7)

# Access Control component
access_box = FancyBboxPatch((7.5, 5.5), 5.5, 1.3, boxstyle="round,pad=0.08",
                            facecolor='#E8F5E9', edgecolor='#388E3C', linewidth=1.0)
ax.add_patch(access_box)
ax.text(10.25, 6.5, 'Access Control', ha='center', fontsize=9, fontweight='bold')
ax.text(10.25, 6.2, '• RBAC (Farmer/Processor/Distributor)', ha='center', fontsize=7)
ax.text(10.25, 6.0, '• Field-Level Filtering', ha='center', fontsize=7)
ax.text(10.25, 5.8, '• Audit Logging', ha='center', fontsize=7)

# Arrow down
ax.arrow(7, 5.5, 0, -0.3, head_width=0.15, head_length=0.1, 
         fc='#333333', ec='#333333', linewidth=1.5)

# Layer 3: Blockchain
ax.text(7, 4.8, 'Blockchain Layer', ha='center', fontsize=9, fontweight='bold')

bc_box = FancyBboxPatch((2, 3.5), 10, 1.0, boxstyle="round,pad=0.08",
                        facecolor='#FFEBEE', edgecolor='#D32F2F', linewidth=1.0)
ax.add_patch(bc_box)
ax.text(7, 4.1, 'Smart Contracts & Trace Events (Harvest/Process/Ship/Receive)', 
         ha='center', va='center', fontsize=8)

# Arrow down
ax.arrow(7, 3.5, 0, -0.3, head_width=0.15, head_length=0.1, 
         fc='#333333', ec='#333333', linewidth=1.5)

# Key Features Section
ax.text(7, 2.8, 'Key Features & Performance', ha='center', fontsize=9, fontweight='bold')

feature1 = FancyBboxPatch((0.5, 1.5), 4, 1.0, boxstyle="round,pad=0.05",
                          facecolor='#F3E5F5', edgecolor='#7B1FA2', linewidth=1.0)
ax.add_patch(feature1)
ax.text(2.5, 2.05, 'Verifiable Caching', ha='center', fontsize=8, fontweight='bold')
ax.text(2.5, 1.8, '5μs overhead', ha='center', fontsize=7)

feature2 = FancyBboxPatch((5, 1.5), 4, 1.0, boxstyle="round,pad=0.05",
                          facecolor='#E0F7FA', edgecolor='#0097A7', linewidth=1.0)
ax.add_patch(feature2)
ax.text(7, 2.05, 'High Performance', ha='center', fontsize=8, fontweight='bold')
ax.text(7, 1.8, '4.09x speedup, 2,870 QPS', ha='center', fontsize=7)

feature3 = FancyBboxPatch((9.5, 1.5), 4, 1.0, boxstyle="round,pad=0.05",
                          facecolor='#FFF8E1', edgecolor='#FFA000', linewidth=1.0)
ax.add_patch(feature3)
ax.text(11.25, 2.05, 'Zero Stale Reads', ha='center', fontsize=8, fontweight='bold')
ax.text(11.25, 1.8, 'Write-triggered invalidation', ha='center', fontsize=7)

# Flow arrows
# Client to MCP
for i in [2.75, 7, 11.25]:
    ax.arrow(i, 7.8, 0, -0.2, head_width=0.08, head_length=0.05, 
             fc='#666666', ec='#666666', linewidth=0.8)

# Cache to Blockchain
ax.arrow(3.75, 5.5, 0, -0.2, head_width=0.08, head_length=0.05, 
         fc='#666666', ec='#666666', linewidth=0.8)

# Access Control to Blockchain
ax.arrow(10.25, 5.5, 0, -0.2, head_width=0.08, head_length=0.05, 
         fc='#666666', ec='#666666', linewidth=0.8)

# Labels for data flow
ax.text(0.3, 6.6, 'Fast Path\n(< 1ms)', ha='center', fontsize=6, 
        bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.7))
ax.text(13.7, 6.6, 'Slow Path\n(50-500ms)', ha='center', fontsize=6,
        bbox=dict(boxstyle='round', facecolor='lightcoral', alpha=0.7))

plt.savefig('fig_comprehensive_architecture.eps', format='eps', dpi=300, bbox_inches='tight')
plt.savefig('fig_comprehensive_architecture.png', format='png', dpi=300, bbox_inches='tight')
plt.close()

print("Comprehensive figure generated successfully!")
print("Files created:")
print("- fig_comprehensive_architecture.eps")
print("- fig_comprehensive_architecture.png")