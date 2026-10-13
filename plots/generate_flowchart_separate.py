#!/usr/bin/env python3
"""Generate query processing flowchart for IEEE paper."""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import numpy as np

# Type 1/42 fonts only (no Type 3)
plt.rcParams['ps.fonttype'] = 42
plt.rcParams['pdf.fonttype'] = 42
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times', 'Times New Roman', 'DejaVu Serif']
plt.rcParams['ps.useafm'] = True

# Set up figure
fig, ax = plt.subplots(1, 1, figsize=(7, 10))
ax.set_xlim(0, 10)
ax.set_ylim(0, 12)
ax.set_aspect('equal')
ax.axis('off')

# Grayscale colors for flowchart
colors_flow = {
    'start': '#404040',
    'process': '#606060',
    'decision': '#808080',
    'cache': '#707070',
    'blockchain': '#505050',
}

def draw_flow_box(ax, x, y, w, h, text, color, shape='rect'):
    """Draw a flowchart box."""
    if shape == 'diamond':
        diamond = plt.Polygon([(x, y+h/2), (x+w/2, y+h), (x+w, y+h/2), (x+w/2, y)],
                             facecolor='white', edgecolor=color, linewidth=2.5)
        ax.add_patch(diamond)
        ax.text(x+w/2, y+h/2, text, ha='center', va='center', fontsize=10, fontweight='bold')
    elif shape == 'rounded':
        box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.1",
                            facecolor=color, edgecolor='black', linewidth=2.5)
        ax.add_patch(box)
        ax.text(x+w/2, y+h/2, text, ha='center', va='center', fontsize=11,
                fontweight='bold', color='white')
    else:
        box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05",
                            facecolor='white', edgecolor=color, linewidth=2.5)
        ax.add_patch(box)
        ax.text(x+w/2, y+h/2, text, ha='center', va='center', fontsize=10, fontweight='bold')

def draw_flow_arrow(ax, start, end, color='black'):
    """Draw an arrow between two points."""
    ax.annotate('', xy=end, xytext=start,
                arrowprops=dict(arrowstyle='->', color=color, lw=2.5))

# Flowchart elements
# Start
draw_flow_box(ax, 3, 10.8, 4, 0.7, 'Client Query', colors_flow['start'], 'rounded')

# MCP receives
draw_flow_box(ax, 3, 9.2, 4, 0.7, 'MCP Layer', colors_flow['process'])

# Cache decision
draw_flow_box(ax, 3.5, 7.0, 3, 1.2, 'Cache\nHit?', colors_flow['decision'], 'diamond')

# Left path - Cache hit
draw_flow_box(ax, 0.3, 7.2, 2.2, 0.6, 'Get Cached', colors_flow['cache'])
draw_flow_box(ax, 0.3, 5.8, 2.2, 0.6, 'Verify Proof', colors_flow['cache'])

# Right path - Cache miss
draw_flow_box(ax, 7.5, 7.2, 2.2, 0.6, 'Query BC', colors_flow['blockchain'])
draw_flow_box(ax, 7.5, 5.8, 2.2, 0.6, 'Gen Proof', colors_flow['blockchain'])
draw_flow_box(ax, 7.5, 4.4, 2.2, 0.6, 'Cache It', colors_flow['cache'])

# Merge and return
draw_flow_box(ax, 3, 2.5, 4, 0.7, 'Return Response', colors_flow['process'])

# End
draw_flow_box(ax, 3, 1.0, 4, 0.7, 'Client Receives', colors_flow['start'], 'rounded')

# Draw arrows
draw_flow_arrow(ax, (5, 10.8), (5, 9.9))
draw_flow_arrow(ax, (5, 9.2), (5, 8.2))

# Cache hit path
draw_flow_arrow(ax, (3.5, 7.6), (2.5, 7.6))
ax.text(2.8, 7.95, 'Yes', fontsize=10, fontweight='bold', color='#006400')
draw_flow_arrow(ax, (1.4, 7.2), (1.4, 6.4))
draw_flow_arrow(ax, (1.4, 5.8), (1.4, 3.2))

# Cache miss path
draw_flow_arrow(ax, (6.5, 7.6), (7.5, 7.6))
ax.text(6.7, 7.95, 'No', fontsize=10, fontweight='bold', color='#8B0000')
draw_flow_arrow(ax, (8.6, 7.2), (8.6, 6.4))
draw_flow_arrow(ax, (8.6, 5.8), (8.6, 5.0))
draw_flow_arrow(ax, (8.6, 4.4), (8.6, 3.2))

# Merge paths
draw_flow_arrow(ax, (1.4, 3.2), (3, 3.2))
draw_flow_arrow(ax, (8.6, 3.2), (7, 3.2))

# Final arrow
draw_flow_arrow(ax, (5, 2.5), (5, 1.7))

plt.tight_layout()

# Save as high-resolution EPS and PNG
output_base = 'fig2_flowchart'
plt.savefig(f'{output_base}.eps', format='eps', dpi=600, bbox_inches='tight')
plt.savefig(f'{output_base}.png', format='png', dpi=600, bbox_inches='tight')
print(f"Flowchart figure saved as EPS and PNG (600 DPI)")
