#!/usr/bin/env python3
"""Generate three-layer architecture diagram for IEEE paper."""

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
fig, ax = plt.subplots(1, 1, figsize=(7, 9))
ax.set_xlim(0, 10)
ax.set_ylim(0, 12)
ax.set_aspect('equal')
ax.axis('off')

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
ax.add_patch(client_box)
ax.text(5, client_y + client_h - 0.35, 'Client Applications', ha='center', va='top',
         fontsize=14, fontweight='bold', color='black')

# Client components
client_comps = ['Query Interface', 'Verification Module']
comp_y = client_y + client_h - 0.9
for comp in client_comps:
    comp_box = FancyBboxPatch((1.0, comp_y - 0.35), 8, 0.45,
                              boxstyle="round,pad=0.05",
                              facecolor='white', edgecolor='black', linewidth=2)
    ax.add_patch(comp_box)
    ax.text(5, comp_y - 0.12, comp, ha='center', va='center', fontsize=10)
    comp_y -= 0.55

# MCP MIDDLEWARE LAYER (middle) - y=4.5 to y=8.0 (height=3.5)
mcp_y = 4.5
mcp_h = 3.5
mcp_box = FancyBboxPatch((0.5, mcp_y), 9, mcp_h, boxstyle="round,pad=0.1",
                          facecolor=colors_arch['mcp'], edgecolor='black', linewidth=3)
ax.add_patch(mcp_box)
ax.text(5, mcp_y + mcp_h - 0.35, 'MCP Middleware Layer', ha='center', va='top',
         fontsize=14, fontweight='bold', color='black')

# MCP components
mcp_comps = ['Cache Manager (CM)', 'Merkle Proof Generator (MPG)', 'Access Control (AC)']
comp_y = mcp_y + mcp_h - 1.0
for comp in mcp_comps:
    comp_box = FancyBboxPatch((1.0, comp_y - 0.35), 8, 0.45,
                              boxstyle="round,pad=0.05",
                              facecolor='white', edgecolor='black', linewidth=2)
    ax.add_patch(comp_box)
    ax.text(5, comp_y - 0.12, comp, ha='center', va='center', fontsize=10)
    comp_y -= 0.65

# BLOCKCHAIN LAYER (bottom) - y=0.5 to y=2.5 (height=2)
bc_y = 0.5
bc_h = 2.0
bc_box = FancyBboxPatch((0.5, bc_y), 9, bc_h, boxstyle="round,pad=0.1",
                         facecolor=colors_arch['blockchain'], edgecolor='black', linewidth=3)
ax.add_patch(bc_box)
ax.text(5, bc_y + bc_h - 0.35, 'Blockchain Layer', ha='center', va='top',
         fontsize=14, fontweight='bold', color='black')

# Blockchain components
bc_comps = ['Smart Contracts', 'Immutable Ledger']
comp_y = bc_y + bc_h - 0.9
for comp in bc_comps:
    comp_box = FancyBboxPatch((1.0, comp_y - 0.35), 8, 0.45,
                              boxstyle="round,pad=0.05",
                              facecolor='white', edgecolor='black', linewidth=2)
    ax.add_patch(comp_box)
    ax.text(5, comp_y - 0.12, comp, ha='center', va='center', fontsize=10)
    comp_y -= 0.55

# ARROWS between layers
# Arrow 1: Client <-> MCP (from bottom of client to top of MCP)
arrow1_start = (5, client_y)
arrow1_end = (5, mcp_y + mcp_h)
ax.annotate('', xy=arrow1_end, xytext=arrow1_start,
             arrowprops=dict(arrowstyle='<->', color='black', lw=4))
ax.text(6.5, (client_y + mcp_y + mcp_h) / 2, 'Query/Response', fontsize=11, style='italic',
         fontweight='bold', bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='black', linewidth=1.5))

# Arrow 2: MCP <-> Blockchain (from bottom of MCP to top of blockchain)
arrow2_start = (5, mcp_y)
arrow2_end = (5, bc_y + bc_h)
ax.annotate('', xy=arrow2_end, xytext=arrow2_start,
             arrowprops=dict(arrowstyle='<->', color='black', lw=4))
ax.text(6.5, (mcp_y + bc_y + bc_h) / 2, 'Cache Miss', fontsize=11, style='italic',
         fontweight='bold', bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='black', linewidth=1.5))

plt.tight_layout()

# Save as high-resolution EPS and PNG
output_base = 'fig1_architecture'
plt.savefig(f'{output_base}.eps', format='eps', dpi=600, bbox_inches='tight')
plt.savefig(f'{output_base}.png', format='png', dpi=600, bbox_inches='tight')
print(f"Architecture figure saved as EPS and PNG (600 DPI)")
