#!/usr/bin/env python3
"""Generate MCP caching flowchart as EPS for IEEE paper."""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

# Type 1/42 fonts only (no Type 3)
plt.rcParams['ps.fonttype'] = 42
plt.rcParams['pdf.fonttype'] = 42
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times', 'Times New Roman', 'DejaVu Serif']
plt.rcParams['ps.useafm'] = True

# Set up figure with white background
fig, ax = plt.subplots(1, 1, figsize=(8, 10))
ax.set_xlim(0, 10)
ax.set_ylim(0, 12)
ax.set_aspect('equal')
ax.axis('off')

# Colors
colors = {
    'start': '#2E7D32',      # Green
    'process': '#1565C0',    # Blue
    'decision': '#F57C00',   # Orange
    'cache': '#7B1FA2',      # Purple
    'blockchain': '#C62828', # Red
    'end': '#2E7D32',        # Green
}

def draw_box(ax, x, y, w, h, text, color, shape='rect'):
    """Draw a flowchart box."""
    if shape == 'diamond':
        # Diamond for decision
        diamond = plt.Polygon([(x, y+h/2), (x+w/2, y+h), (x+w, y+h/2), (x+w/2, y)],
                             facecolor='white', edgecolor=color, linewidth=2)
        ax.add_patch(diamond)
        ax.text(x+w/2, y+h/2, text, ha='center', va='center', fontsize=9, fontweight='bold')
    elif shape == 'rounded':
        # Rounded rectangle for start/end
        box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05,rounding_size=0.3",
                            facecolor=color, edgecolor='black', linewidth=2, alpha=0.8)
        ax.add_patch(box)
        ax.text(x+w/2, y+h/2, text, ha='center', va='center', fontsize=10,
                fontweight='bold', color='white')
    else:
        # Regular rectangle
        box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.1",
                            facecolor='white', edgecolor=color, linewidth=2)
        ax.add_patch(box)
        ax.text(x+w/2, y+h/2, text, ha='center', va='center', fontsize=9, fontweight='bold')

def draw_arrow(ax, start, end, color='black'):
    """Draw an arrow between two points."""
    ax.annotate('', xy=end, xytext=start,
                arrowprops=dict(arrowstyle='->', color=color, lw=1.5))

# Draw flowchart elements (NO TITLE)
# Start
draw_box(ax, 3.5, 10.5, 3, 0.7, 'Client Query', colors['start'], 'rounded')

# MCP Layer receives query
draw_box(ax, 3, 9.3, 4, 0.7, 'MCP Layer Receives Query', colors['process'])

# Cache lookup decision
draw_box(ax, 3.25, 7.6, 3.5, 1.2, 'Cache\nHit?', colors['decision'], 'diamond')

# Cache hit path (left)
draw_box(ax, 0.3, 7.8, 2.2, 0.7, 'Get Cached Data', colors['cache'])
draw_box(ax, 0.3, 6.6, 2.2, 0.7, 'Verify Merkle Proof', colors['cache'])

# Cache miss path (right)
draw_box(ax, 7.5, 7.8, 2.2, 0.7, 'Query Blockchain', colors['blockchain'])
draw_box(ax, 7.5, 6.6, 2.2, 0.7, 'Generate Proof', colors['blockchain'])
draw_box(ax, 7.5, 5.4, 2.2, 0.7, 'Store in Cache', colors['cache'])

# Verification decision
draw_box(ax, 0.05, 5.1, 2.7, 1.2, 'Proof\nValid?', colors['decision'], 'diamond')

# Invalid proof path
draw_box(ax, 0.3, 3.6, 2.2, 0.7, 'Fetch Fresh Data', colors['blockchain'])

# Merge point - Return response
draw_box(ax, 3, 2.3, 4, 0.7, 'Return Verified Response', colors['process'])

# End
draw_box(ax, 3.5, 1.1, 3, 0.7, 'Client Receives Data', colors['end'], 'rounded')

# Draw arrows
# Start to MCP
draw_arrow(ax, (5, 10.5), (5, 10.0))

# MCP to Cache decision
draw_arrow(ax, (5, 9.3), (5, 8.8))

# Cache hit (left branch)
draw_arrow(ax, (3.25, 8.2), (2.5, 8.2))
ax.text(2.8, 8.4, 'Yes', fontsize=8, fontweight='bold', color='green')

draw_arrow(ax, (1.4, 7.8), (1.4, 7.3))

# Cache miss (right branch)
draw_arrow(ax, (6.75, 8.2), (7.5, 8.2))
ax.text(6.9, 8.4, 'No', fontsize=8, fontweight='bold', color='red')

draw_arrow(ax, (8.6, 7.8), (8.6, 7.3))
draw_arrow(ax, (8.6, 6.6), (8.6, 6.1))
draw_arrow(ax, (8.6, 5.4), (8.6, 4.8))

# Verify proof
draw_arrow(ax, (1.4, 6.6), (1.4, 6.3))

# Proof valid decision
draw_arrow(ax, (1.4, 5.1), (1.4, 4.6))
ax.text(1.6, 4.8, 'Yes', fontsize=8, fontweight='bold', color='green')

# Invalid proof - fetch fresh
draw_arrow(ax, (0.05, 5.7), (-0.3, 5.7))
ax.text(-0.5, 5.9, 'No', fontsize=8, fontweight='bold', color='red')
# Curve down to fetch fresh
ax.annotate('', xy=(1.4, 4.3), xytext=(-0.3, 5.7),
            arrowprops=dict(arrowstyle='->', color='black', lw=1.5,
                          connectionstyle='arc3,rad=0.3'))

# Fresh data to return
draw_arrow(ax, (1.4, 3.6), (1.4, 3.0))

# Merge paths to return response
draw_arrow(ax, (1.4, 2.65), (3, 2.65))
draw_arrow(ax, (8.6, 4.8), (8.6, 2.65))
draw_arrow(ax, (8.6, 2.65), (7, 2.65))

# Return to end
draw_arrow(ax, (5, 2.3), (5, 1.8))

# Add legend
legend_elements = [
    mpatches.Patch(facecolor=colors['start'], edgecolor='black', label='Start/End'),
    mpatches.Patch(facecolor='white', edgecolor=colors['process'], label='Process'),
    mpatches.Patch(facecolor='white', edgecolor=colors['decision'], label='Decision'),
    mpatches.Patch(facecolor='white', edgecolor=colors['cache'], label='Cache Operation'),
    mpatches.Patch(facecolor='white', edgecolor=colors['blockchain'], label='Blockchain Operation'),
]
ax.legend(handles=legend_elements, loc='lower right', fontsize=8, framealpha=0.9)

plt.tight_layout()
plt.savefig('fig5_mcp_flowchart.eps',
            format='eps', dpi=300, bbox_inches='tight')
plt.savefig('fig5_mcp_flowchart.png',
            format='png', dpi=300, bbox_inches='tight')
print("Flowchart saved as EPS and PNG")
