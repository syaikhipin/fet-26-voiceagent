#!/usr/bin/env python3
"""Generate combined high-quality architecture and flowchart figure for IEEE paper."""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle
import numpy as np

# Type 1/42 fonts only (no Type 3)
plt.rcParams['ps.fonttype'] = 42
plt.rcParams['pdf.fonttype'] = 42
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times', 'Times New Roman', 'DejaVu Serif']
plt.rcParams['ps.useafm'] = True

# Set up figure with two subplots side by side
fig = plt.figure(figsize=(14, 7))

# ============================================================================
# LEFT SIDE: Architecture Diagram
# ============================================================================
ax1 = plt.subplot(1, 2, 1)
ax1.set_xlim(0, 10)
ax1.set_ylim(0, 12)
ax1.set_aspect('equal')
ax1.axis('off')
ax1.set_title('(a) Three-Layer Architecture', fontsize=14, fontweight='bold', pad=15)

# Grayscale colors for B&W printing
colors_arch = {
    'client': '#D0D0D0',
    'mcp': '#B0B0B0',
    'blockchain': '#909090',
}

# CLIENT LAYER (top) - y=9.5 to y=11.5 (height=2)
client_y = 9.5
client_h = 2.0
client_box = FancyBboxPatch((0.5, client_y), 9, client_h, boxstyle="round,pad=0.1",
                             facecolor=colors_arch['client'], edgecolor='black', linewidth=3)
ax1.add_patch(client_box)
ax1.text(5, client_y + client_h - 0.35, 'Client Applications', ha='center', va='top',
         fontsize=14, fontweight='bold', color='black')

# Client components
client_comps = ['Query Interface', 'Verification Module']
comp_y = client_y + client_h - 0.9
for comp in client_comps:
    comp_box = FancyBboxPatch((1.0, comp_y - 0.35), 8, 0.45,
                              boxstyle="round,pad=0.05",
                              facecolor='white', edgecolor='black', linewidth=2)
    ax1.add_patch(comp_box)
    ax1.text(5, comp_y - 0.12, comp, ha='center', va='center', fontsize=10)
    comp_y -= 0.55

# MCP MIDDLEWARE LAYER (middle) - y=4.5 to y=8.0 (height=3.5)
mcp_y = 4.5
mcp_h = 3.5
mcp_box = FancyBboxPatch((0.5, mcp_y), 9, mcp_h, boxstyle="round,pad=0.1",
                          facecolor=colors_arch['mcp'], edgecolor='black', linewidth=3)
ax1.add_patch(mcp_box)
ax1.text(5, mcp_y + mcp_h - 0.35, 'MCP Middleware Layer', ha='center', va='top',
         fontsize=14, fontweight='bold', color='black')

# MCP components
mcp_comps = ['Cache Manager (LRU/LFU/ARC)', 'Merkle Proof Generator', 'Access Control (RBAC)']
comp_y = mcp_y + mcp_h - 1.0
for comp in mcp_comps:
    comp_box = FancyBboxPatch((1.0, comp_y - 0.35), 8, 0.45,
                              boxstyle="round,pad=0.05",
                              facecolor='white', edgecolor='black', linewidth=2)
    ax1.add_patch(comp_box)
    ax1.text(5, comp_y - 0.12, comp, ha='center', va='center', fontsize=10)
    comp_y -= 0.65

# BLOCKCHAIN LAYER (bottom) - y=0.5 to y=2.5 (height=2)
bc_y = 0.5
bc_h = 2.0
bc_box = FancyBboxPatch((0.5, bc_y), 9, bc_h, boxstyle="round,pad=0.1",
                         facecolor=colors_arch['blockchain'], edgecolor='black', linewidth=3)
ax1.add_patch(bc_box)
ax1.text(5, bc_y + bc_h - 0.35, 'Blockchain Layer', ha='center', va='top',
         fontsize=14, fontweight='bold', color='black')

# Blockchain components
bc_comps = ['Smart Contracts', 'Immutable Ledger']
comp_y = bc_y + bc_h - 0.9
for comp in bc_comps:
    comp_box = FancyBboxPatch((1.0, comp_y - 0.35), 8, 0.45,
                              boxstyle="round,pad=0.05",
                              facecolor='white', edgecolor='black', linewidth=2)
    ax1.add_patch(comp_box)
    ax1.text(5, comp_y - 0.12, comp, ha='center', va='center', fontsize=10)
    comp_y -= 0.55

# ARROWS between layers
# Arrow 1: Client <-> MCP (from bottom of client to top of MCP)
arrow1_start = (5, client_y)
arrow1_end = (5, mcp_y + mcp_h)
ax1.annotate('', xy=arrow1_end, xytext=arrow1_start,
             arrowprops=dict(arrowstyle='<->', color='black', lw=4))
ax1.text(6.5, (client_y + mcp_y + mcp_h) / 2, 'Query/Response', fontsize=11, style='italic',
         fontweight='bold', bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='black', linewidth=1.5))

# Arrow 2: MCP <-> Blockchain (from bottom of MCP to top of blockchain)
arrow2_start = (5, mcp_y)
arrow2_end = (5, bc_y + bc_h)
ax1.annotate('', xy=arrow2_end, xytext=arrow2_start,
             arrowprops=dict(arrowstyle='<->', color='black', lw=4))
ax1.text(6.5, (mcp_y + bc_y + bc_h) / 2, 'Cache Miss', fontsize=11, style='italic',
         fontweight='bold', bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='black', linewidth=1.5))

# ============================================================================
# RIGHT SIDE: Flowchart
# ============================================================================
ax2 = plt.subplot(1, 2, 2)
ax2.set_xlim(0, 10)
ax2.set_ylim(0, 12)
ax2.set_aspect('equal')
ax2.axis('off')
ax2.set_title('(b) Query Processing Flow', fontsize=14, fontweight='bold', pad=15)

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
draw_flow_box(ax2, 3, 10.8, 4, 0.7, 'Client Query', colors_flow['start'], 'rounded')

# MCP receives
draw_flow_box(ax2, 3, 9.2, 4, 0.7, 'MCP Layer', colors_flow['process'])

# Cache decision
draw_flow_box(ax2, 3.5, 7.0, 3, 1.2, 'Cache\nHit?', colors_flow['decision'], 'diamond')

# Left path - Cache hit
draw_flow_box(ax2, 0.3, 7.2, 2.2, 0.6, 'Get Cached', colors_flow['cache'])
draw_flow_box(ax2, 0.3, 5.8, 2.2, 0.6, 'Verify Proof', colors_flow['cache'])

# Right path - Cache miss
draw_flow_box(ax2, 7.5, 7.2, 2.2, 0.6, 'Query BC', colors_flow['blockchain'])
draw_flow_box(ax2, 7.5, 5.8, 2.2, 0.6, 'Gen Proof', colors_flow['blockchain'])
draw_flow_box(ax2, 7.5, 4.4, 2.2, 0.6, 'Cache It', colors_flow['cache'])

# Merge and return
draw_flow_box(ax2, 3, 2.5, 4, 0.7, 'Return Response', colors_flow['process'])

# End
draw_flow_box(ax2, 3, 1.0, 4, 0.7, 'Client Receives', colors_flow['start'], 'rounded')

# Draw arrows
draw_flow_arrow(ax2, (5, 10.8), (5, 9.9))
draw_flow_arrow(ax2, (5, 9.2), (5, 8.2))

# Cache hit path
draw_flow_arrow(ax2, (3.5, 7.6), (2.5, 7.6))
ax2.text(2.8, 7.95, 'Yes', fontsize=10, fontweight='bold', color='#006400')
draw_flow_arrow(ax2, (1.4, 7.2), (1.4, 6.4))
draw_flow_arrow(ax2, (1.4, 5.8), (1.4, 3.2))

# Cache miss path
draw_flow_arrow(ax2, (6.5, 7.6), (7.5, 7.6))
ax2.text(6.7, 7.95, 'No', fontsize=10, fontweight='bold', color='#8B0000')
draw_flow_arrow(ax2, (8.6, 7.2), (8.6, 6.4))
draw_flow_arrow(ax2, (8.6, 5.8), (8.6, 5.0))
draw_flow_arrow(ax2, (8.6, 4.4), (8.6, 3.2))

# Merge paths
draw_flow_arrow(ax2, (1.4, 3.2), (3, 3.2))
draw_flow_arrow(ax2, (8.6, 3.2), (7, 3.2))

# Final arrow
draw_flow_arrow(ax2, (5, 2.5), (5, 1.7))

plt.tight_layout()

# Save as high-resolution EPS and PNG
output_base = 'fig_combined_architecture'
plt.savefig(f'{output_base}.eps', format='eps', dpi=600, bbox_inches='tight')
plt.savefig(f'{output_base}.png', format='png', dpi=600, bbox_inches='tight')
print(f"Combined architecture figure saved as EPS and PNG (600 DPI)")
