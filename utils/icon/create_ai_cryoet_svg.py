#!/usr/bin/env python3
"""
AI-CryoET SVG Icon Generator
============================

Companion to ``create_ai_cryoet_icon.py``. Emits crisp, scalable SVG versions
of the snowflake-neural-network icon for use in the web frontend:

    - frontend/public/favicon.svg            (petrol background, for browser tabs)
    - frontend/src/assets/snowflake-logo.svg (transparent, for the petrol navbar)

The geometry is identical to the PNG generator (6-fold symmetry, primary arms,
midpoint nodes, secondary/tertiary branches, ringed AI core) so the SVG and the
raster renders stay visually in sync.

Usage:
    python create_ai_cryoet_svg.py
"""

import math
import os

# --- Colors (match create_ai_cryoet_icon.py) -------------------------------
SNOWFLAKE_COLOR = "#a8d4f0"   # Icy blue-white for nodes and branches
BACKGROUND_COLOR = "#145266"  # Dark petrol blue background

# --- Geometry (512px base, same constants as the PNG generator) ------------
SIZE = 512
CX = CY = SIZE / 2
ARM_LENGTH = 155
MIDPOINT_DIST = 80
BRANCH_LENGTH = 35
TIP_EXTENSION = 22

ANGLES = [i * 60 - 90 for i in range(6)]  # [-90, -30, 30, 90, 150, 210]


def polar(radius, angle_deg):
    rad = math.radians(angle_deg)
    return (CX + radius * math.cos(rad), CY + radius * math.sin(rad))


def fmt(x):
    return f"{x:.2f}".rstrip("0").rstrip(".")


def pt(p):
    return f"{fmt(p[0])} {fmt(p[1])}"


def line(p1, p2, width, opacity=1.0):
    return (
        f'<line x1="{fmt(p1[0])}" y1="{fmt(p1[1])}" '
        f'x2="{fmt(p2[0])}" y2="{fmt(p2[1])}" '
        f'stroke="{SNOWFLAKE_COLOR}" stroke-width="{width}" '
        f'stroke-linecap="round" stroke-opacity="{opacity}"/>'
    )


def node(p, r, fill=SNOWFLAKE_COLOR, opacity=1.0):
    return (
        f'<circle cx="{fmt(p[0])}" cy="{fmt(p[1])}" r="{r}" '
        f'fill="{fill}" fill-opacity="{opacity}"/>'
    )


def build_network():
    """Return the SVG markup for the snowflake network (no background)."""
    tip_nodes = [polar(ARM_LENGTH, a) for a in ANGLES]
    mid_nodes = [polar(MIDPOINT_DIST, a) for a in ANGLES]

    branch_nodes = []
    for a in ANGLES:
        branch_nodes.append(polar(MIDPOINT_DIST + BRANCH_LENGTH, a - 35))
        branch_nodes.append(polar(MIDPOINT_DIST + BRANCH_LENGTH, a + 35))

    parts = []

    # --- Connections (behind nodes) ---
    for tip in tip_nodes:
        parts.append(line((CX, CY), tip, 4))

    for i, mid in enumerate(mid_nodes):
        parts.append(line(mid, branch_nodes[i * 2], 3, 0.70))
        parts.append(line(mid, branch_nodes[i * 2 + 1], 3, 0.70))

    for i, tip in enumerate(tip_nodes):
        a = ANGLES[i]
        parts.append(line(tip, polar(ARM_LENGTH + TIP_EXTENSION, a - 25), 2, 0.51))
        parts.append(line(tip, polar(ARM_LENGTH + TIP_EXTENSION, a + 25), 2, 0.51))

    # --- Glow group (blurred copy of the nodes) ---
    glow = ['<g filter="url(#glow)">']
    for tip in tip_nodes:
        glow.append(node(tip, 16, opacity=0.78))
    for mid in mid_nodes:
        glow.append(node(mid, 11, opacity=0.78))
    for bn in branch_nodes:
        glow.append(node(bn, 8, opacity=0.70))
    glow.append(node((CX, CY), 28, opacity=1.0))
    glow.append("</g>")
    parts.extend(glow)

    # --- Solid nodes on top ---
    for tip in tip_nodes:
        parts.append(node(tip, 14))
    for mid in mid_nodes:
        parts.append(node(mid, 9))
    for bn in branch_nodes:
        parts.append(node(bn, 6))

    # Center ringed "AI core": outer ring, dark gap, inner dot.
    parts.append(node((CX, CY), 22))
    parts.append(node((CX, CY), 14, fill=BACKGROUND_COLOR))
    parts.append(node((CX, CY), 8))

    return "\n    ".join(parts)


def svg_document(network, with_background, rounded=False):
    defs = (
        '  <defs>\n'
        '    <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">\n'
        '      <feGaussianBlur stdDeviation="8"/>\n'
        '    </filter>\n'
        '  </defs>\n'
    )
    bg = ""
    if with_background:
        if rounded:
            bg = (
                f'  <rect width="{SIZE}" height="{SIZE}" rx="96" ry="96" '
                f'fill="{BACKGROUND_COLOR}"/>\n'
            )
        else:
            bg = f'  <rect width="{SIZE}" height="{SIZE}" fill="{BACKGROUND_COLOR}"/>\n'

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {SIZE} {SIZE}" role="img" '
        f'aria-label="AI+CryoET snowflake network">\n'
        f'{defs}'
        f'{bg}'
        f'  <g>\n    {network}\n  </g>\n'
        f'</svg>\n'
    )


def main():
    # This script lives in utils/icon/; the repo root is two levels up.
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    network = build_network()

    favicon_path = os.path.join(repo_root, "frontend", "public", "favicon.svg")
    logo_path = os.path.join(repo_root, "frontend", "src", "assets", "snowflake-logo.svg")

    os.makedirs(os.path.dirname(favicon_path), exist_ok=True)
    os.makedirs(os.path.dirname(logo_path), exist_ok=True)

    with open(favicon_path, "w") as f:
        f.write(svg_document(network, with_background=True, rounded=True))
    print(f"Wrote {favicon_path}")

    with open(logo_path, "w") as f:
        f.write(svg_document(network, with_background=False))
    print(f"Wrote {logo_path}")


if __name__ == "__main__":
    main()
