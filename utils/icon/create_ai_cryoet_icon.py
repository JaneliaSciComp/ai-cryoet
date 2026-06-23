#!/usr/bin/env python3
"""
AI-CryoET Slack Icon Generator
==============================

Generates a snowflake-neural network hybrid icon for the AI-CryoET Slack workspace.
The design merges the 6-fold crystalline symmetry of a snowflake with neural network
nodes and connections - the "cryo" (cold/ice) meets AI concept.

Requirements:
    pip install Pillow

Usage:
    python create_ai_cryoet_icon.py

Output:
    - ai_cryoet_snowflake_1024.png  (1024x1024, high-res)
    - ai_cryoet_snowflake.png       (512x512, standard)
    - ai_cryoet_snowflake_132.png   (132x132, minimum Slack size)

Author: Generated with Claude
Date: January 2025
"""

from PIL import Image, ImageDraw, ImageFilter
import math


# =============================================================================
# CONFIGURATION - Edit these values to customize the icon
# =============================================================================

# Output size (rendered natively, then downscaled for smaller versions)
SIZE = 1024

# Colors
SNOWFLAKE_COLOR = '#a8d4f0'       # Icy blue-white for nodes and branches
SNOWFLAKE_RGB = (168, 212, 240)   # Same color as RGB tuple (for alpha blending)
BACKGROUND_COLOR = '#145266'      # Dark petrol blue background

# Structure dimensions (at 512px base, will be scaled)
BASE_SIZE = 512
ARM_LENGTH = 155      # Primary arm length from center
MIDPOINT_DIST = 80    # Distance to midpoint nodes
BRANCH_LENGTH = 35    # Secondary branch length
TIP_EXTENSION = 22    # Tertiary branch extension at tips


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def polar_to_cartesian(radius, angle_degrees, center_x, center_y):
    """
    Convert polar coordinates to cartesian coordinates.
    
    Args:
        radius: Distance from center
        angle_degrees: Angle in degrees (0 = right, 90 = down)
        center_x, center_y: Center point coordinates
    
    Returns:
        Tuple (x, y) of cartesian coordinates
    """
    radians = math.radians(angle_degrees)
    x = center_x + radius * math.cos(radians)
    y = center_y + radius * math.sin(radians)
    return (x, y)


def draw_line(draw_context, point1, point2, color, width):
    """Draw a line between two points."""
    draw_context.line([point1, point2], fill=color, width=width)


def draw_node(draw_context, x, y, radius, color):
    """Draw a filled circle (node) at the given position."""
    draw_context.ellipse([x - radius, y - radius, x + radius, y + radius], fill=color)


# =============================================================================
# MAIN ICON GENERATION
# =============================================================================

def create_snowflake_network_icon():
    """
    Generate the snowflake-network icon.
    
    The design uses 6-fold rotational symmetry (like a real snowflake) with:
    - 6 primary arms radiating from center
    - 6 midpoint nodes with secondary branches
    - 12 branch tip nodes
    - Tertiary decorative branches at arm tips
    - Glowing effect on all nodes
    """
    
    # Calculate scale factor for rendering at higher resolution
    scale = SIZE / BASE_SIZE
    cx, cy = SIZE // 2, SIZE // 2  # Center coordinates
    
    # Scale all distances
    r_tip = int(ARM_LENGTH * scale)
    r_mid = int(MIDPOINT_DIST * scale)
    r_branch = int(BRANCH_LENGTH * scale)
    r_tip_ext = int(TIP_EXTENSION * scale)
    
    # 6-fold symmetry: angles at 60° intervals, starting from top (-90°)
    angles = [i * 60 - 90 for i in range(6)]  # [-90, -30, 30, 90, 150, 210]
    
    # Calculate node positions
    # Primary tip nodes (end of each main arm)
    tip_nodes = [polar_to_cartesian(r_tip, a, cx, cy) for a in angles]
    
    # Midpoint nodes (halfway along each arm)
    mid_nodes = [polar_to_cartesian(r_mid, a, cx, cy) for a in angles]
    
    # Branch nodes (two per midpoint, angled ±35° from arm direction)
    branch_nodes = []
    for a in angles:
        branch_nodes.append(polar_to_cartesian(r_mid + r_branch, a - 35, cx, cy))
        branch_nodes.append(polar_to_cartesian(r_mid + r_branch, a + 35, cx, cy))
    
    # -------------------------------------------------------------------------
    # Create image layers
    # -------------------------------------------------------------------------
    
    # Main image with background
    img = Image.new('RGBA', (SIZE, SIZE), BACKGROUND_COLOR)
    draw = ImageDraw.Draw(img)
    
    # Separate layer for glow effect (will be blurred)
    glow_layer = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_layer)
    
    # -------------------------------------------------------------------------
    # Draw connections (lines) - these go behind the nodes
    # -------------------------------------------------------------------------
    
    # Primary arms: center to tip nodes
    for tip in tip_nodes:
        draw_line(draw, (cx, cy), tip, SNOWFLAKE_COLOR, int(4 * scale))
    
    # Secondary branches: midpoint to branch nodes
    for i, mid in enumerate(mid_nodes):
        b1 = branch_nodes[i * 2]
        b2 = branch_nodes[i * 2 + 1]
        # Slightly transparent for visual hierarchy
        draw_line(draw, mid, b1, SNOWFLAKE_RGB + (180,), int(3 * scale))
        draw_line(draw, mid, b2, SNOWFLAKE_RGB + (180,), int(3 * scale))
    
    # Tertiary branches: small decorative lines at arm tips
    for i, tip in enumerate(tip_nodes):
        a = angles[i]
        t1 = polar_to_cartesian(r_tip + r_tip_ext, a - 25, cx, cy)
        t2 = polar_to_cartesian(r_tip + r_tip_ext, a + 25, cx, cy)
        # More transparent for subtlety
        draw_line(draw, tip, t1, SNOWFLAKE_RGB + (130,), int(2 * scale))
        draw_line(draw, tip, t2, SNOWFLAKE_RGB + (130,), int(2 * scale))
    
    # -------------------------------------------------------------------------
    # Draw glow layer (will be blurred and composited)
    # -------------------------------------------------------------------------
    
    # Tip node glows
    for tip in tip_nodes:
        x, y = tip
        r = int(16 * scale)
        draw_node(glow_draw, x, y, r, SNOWFLAKE_RGB + (200,))
    
    # Midpoint node glows
    for mid in mid_nodes:
        x, y = mid
        r = int(11 * scale)
        draw_node(glow_draw, x, y, r, SNOWFLAKE_RGB + (200,))
    
    # Branch node glows
    for bn in branch_nodes:
        x, y = bn
        r = int(8 * scale)
        draw_node(glow_draw, x, y, r, SNOWFLAKE_RGB + (180,))
    
    # Center node glow (larger and brighter)
    r = int(28 * scale)
    draw_node(glow_draw, cx, cy, r, SNOWFLAKE_RGB + (255,))
    
    # Apply gaussian blur to create glow effect
    glow_blurred = glow_layer.filter(ImageFilter.GaussianBlur(radius=int(8 * scale)))
    
    # Composite glow layer onto main image
    img = Image.alpha_composite(img, glow_blurred)
    draw = ImageDraw.Draw(img)
    
    # -------------------------------------------------------------------------
    # Draw solid nodes on top of glow
    # -------------------------------------------------------------------------
    
    # Tip nodes (largest peripheral nodes)
    for tip in tip_nodes:
        x, y = tip
        r = int(14 * scale)
        draw_node(draw, x, y, r, SNOWFLAKE_COLOR)
    
    # Midpoint nodes (medium size)
    for mid in mid_nodes:
        x, y = mid
        r = int(9 * scale)
        draw_node(draw, x, y, r, SNOWFLAKE_COLOR)
    
    # Branch nodes (smallest)
    for bn in branch_nodes:
        x, y = bn
        r = int(6 * scale)
        draw_node(draw, x, y, r, SNOWFLAKE_COLOR)
    
    # Center node with ring effect (creates "AI core" appearance)
    r1, r2, r3 = int(22 * scale), int(14 * scale), int(8 * scale)
    draw_node(draw, cx, cy, r1, SNOWFLAKE_COLOR)      # Outer ring
    draw_node(draw, cx, cy, r2, BACKGROUND_COLOR)     # Dark middle
    draw_node(draw, cx, cy, r3, SNOWFLAKE_COLOR)      # Inner dot
    
    # -------------------------------------------------------------------------
    # Convert to RGB and save multiple sizes
    # -------------------------------------------------------------------------
    
    # Convert RGBA to RGB (flatten alpha)
    final = Image.new('RGB', (SIZE, SIZE), BACKGROUND_COLOR)
    final.paste(img, mask=img.split()[3] if img.mode == 'RGBA' else None)
    
    # Save high-res version (native resolution)
    final.save('ai_cryoet_snowflake_1024.png', 'PNG')
    print(f"Created ai_cryoet_snowflake_1024.png ({SIZE}x{SIZE})")
    
    # Save standard version (512x512)
    medium = final.resize((512, 512), Image.Resampling.LANCZOS)
    medium.save('ai_cryoet_snowflake.png', 'PNG')
    print("Created ai_cryoet_snowflake.png (512x512)")
    
    # Save minimum Slack size (132x132)
    small = final.resize((132, 132), Image.Resampling.LANCZOS)
    small.save('ai_cryoet_snowflake_132.png', 'PNG')
    print("Created ai_cryoet_snowflake_132.png (132x132)")
    
    print("\nDone! Upload ai_cryoet_snowflake.png to Slack workspace settings.")


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == '__main__':
    create_snowflake_network_icon()
