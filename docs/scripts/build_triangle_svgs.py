#!/usr/bin/env python3
"""Build THAMES architecture triangle SVGs (dark + light themes).

Inlines both PNGs as base64 so the SVGs are self-contained and load
properly in any viewer (Affinity, Inkscape, Illustrator, browsers).

Run with the THAMES master venv:
    ~/Code/Python/Envs/Default/bin/python build_triangle_svgs.py
"""
import base64
import io
from pathlib import Path
from PIL import Image
import matplotlib.pyplot as plt

DOCS = Path("/Users/jwbullard/Code/THAMES/docs")
MICRO_PNG = Path(
    "/Users/jwbullard/Research/THAMES-Tests-2026/Figures/"
    "HY-ccr152-ws45/frames/frame_0004_0d_12h00m.png"
)
GIBBS_PNG = DOCS / "gibbs-surface.png"


def encode_png(path: Path, max_dim: int | None = None) -> str:
    img = Image.open(path)
    if max_dim and (img.width > max_dim or img.height > max_dim):
        img.thumbnail((max_dim, max_dim), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def render_equation_png() -> bytes:
    """Render the standard THAMES rate equation as a PNG via mathtext.

    Affinity Designer mishandles tspan baseline shifts and absolute-y
    positioning, so we ship the equation as a flat image to guarantee
    consistent superscript placement across viewers.
    """
    fig, ax = plt.subplots(figsize=(5.5, 1.0), facecolor="none")
    ax.axis("off")
    ax.text(
        0.5, 0.5,
        r"$R = k\,A\,(1 - \Omega^{p})^{q}$",
        fontsize=28,
        color="#EDE4D3",
        ha="center",
        va="center",
    )
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=220, transparent=True,
                bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)
    return buf.getvalue()


micro_b64 = encode_png(MICRO_PNG, max_dim=520)
gibbs_b64 = encode_png(GIBBS_PNG)
eq_b64    = base64.b64encode(render_equation_png()).decode("ascii")


# -----------------------------------------------------------------------------
# Curve geometry (kept consistent across both themes)
#
# The three panels are arranged as a triangle:
#   micro:    (450,130) - (750,390)    bottom edge y = 390
#   gems:     (150,560) - (450,820)    top edge y = 560 (right corner at 450,560)
#   kinetics: (750,560) - (1050,820)   top edge y = 560 (left corner at 750,560)
#
# Each edge of the triangle has a two-curve "lens" with one direction labelled
# on each curve.  The midpoints of the quadratic Bezier curves at t=0.5 are:
#   B(0.5) = 0.25*P0 + 0.5*P1 + 0.25*P2
# Tangent at midpoint = P2 - P0; angle of tangent (atan2(dy, dx)) is the
# rotation we apply to the label so it lies along the curve.
# -----------------------------------------------------------------------------

SRC_TEAL  = "#397B8A"   # GEMS source color
SRC_EMBER = "#E07A2C"   # microstructure source color
SRC_JADE  = "#5FAA82"   # kinetics source color

CURVES = [
    # (path d, label, sublabel, label x, label y, rotation deg, source-color hex)
    # Each label's color matches the panel the data leaves so a viewer can
    # trace any label back to its source without reading the arrowhead.
    # Colors are applied as inline `fill` attributes (Affinity does not
    # reliably honor SVG <style> rules for fill/font-family).
    # LEFT EDGE - micro <-> gems
    # outer: GEMS -> micro   (source = GEMS, teal)
    ("M 380 555 Q 360 470 490 395", "phase volumes",  "how much of each",      355, 445, -55, SRC_TEAL),
    # inner: micro -> GEMS   (source = micro, ember)
    ("M 530 395 Q 470 470 430 555", "surface areas",  "where reactions sit",   515, 500, -55, SRC_EMBER),

    # RIGHT EDGE - micro <-> kinetics  (mirror)
    # outer: kinetics -> micro   (source = kinetics, jade)
    ("M 820 555 Q 840 470 710 395", "rate → voxel update", "growth, dissolution", 845, 445, 55, SRC_JADE),
    # inner: micro -> kinetics   (source = micro, ember)
    ("M 670 395 Q 730 470 770 555", "interface area", "per phase per cycle",   685, 500, 55, SRC_EMBER),
]

# Bottom-edge curves get horizontal labels (no rotation)
BOTTOM_TOP_CURVE = "M 455 660 Q 600 625 745 660"      # GEMS -> kinetics (top of bottom edge)
BOTTOM_BOT_CURVE = "M 745 720 Q 600 755 455 720"      # kinetics -> GEMS (bottom of bottom edge)

# Top curve midpoint y = 0.25*660 + 0.5*625 + 0.25*660 = 642.5
# Bottom curve midpoint y = 0.25*720 + 0.5*755 + 0.25*720 = 737.5


def build_svg(*, theme: str) -> str:
    if theme == "dark":
        text_color   = "#EDE4D3"   # cream everywhere
        panel_text   = "#EDE4D3"
        arrow_color  = "#EDE4D3"
        hub_stroke   = "#EDE4D3"
        hub_text     = "#EDE4D3"
        shadow_opacity = "0.45"    # more visible on dark to read as elevation
    elif theme == "light":
        text_color   = "#1A1A1A"   # dark charcoal for exterior text/arrows
        panel_text   = "#EDE4D3"   # cream inside the colored panels
        arrow_color  = "#1A1A1A"
        hub_stroke   = "#1A1A1A"
        hub_text     = "#1A1A1A"
        shadow_opacity = "0.22"    # subtle on white page
    else:
        raise ValueError(theme)

    # Rotated label group - single <text> with two <tspan> children is the
    # canonical SVG multi-line idiom and renders consistently across viewers
    # (Affinity, Inkscape, browsers).  Each tspan resets x to 0 so the line
    # break doesn't run on horizontally.  The main label carries an extra
    # source-color class so labels are visually bound to their origin panel.
    rot_labels = []
    for _path, label, sub, mx, my, rot, fill in CURVES:
        rot_labels.append(
            f'  <g transform="translate({mx},{my}) rotate({rot})">\n'
            f'    <text font-family="Inter" text-anchor="middle">\n'
            f'      <tspan x="0" y="0"  class="flow-label" fill="{fill}">{label}</tspan>\n'
            f'      <tspan x="0" dy="20" class="flow-sub">{sub}</tspan>\n'
            f'    </text>\n'
            f'  </g>'
        )
    rot_labels_xml = "\n".join(rot_labels)

    diagonal_paths_xml = "\n    ".join(
        f'<path d="{p}" marker-end="url(#arrow)"/>' for (p, *_rest) in CURVES
    )

    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
     viewBox="0 0 1200 1000"
     font-family="Inter, 'Helvetica Neue', Helvetica, system-ui, sans-serif">
  <!-- THAMES architecture triangle - {theme.upper()} theme.
       Generated by docs/scripts/build_triangle_svgs.py - edit there, not here. -->
  <defs>
    <style><![CDATA[
      text {{ font-family: 'Inter', 'Helvetica Neue', 'Helvetica', system-ui, sans-serif; fill: {text_color}; }}
      .title       {{ font-size: 42px; font-weight: 700; letter-spacing: 0.02em; }}
      .subtitle    {{ font-size: 19px; font-weight: 400; opacity: 0.80; }}
      .flow-label  {{ font-size: 18px; font-weight: 600; }}
      .flow-sub    {{ font-size: 15px; font-weight: 400; opacity: 0.72; }}
      .wordmark    {{ font-size: 22px; font-weight: 700; letter-spacing: 0.14em; fill: {hub_text}; }}
      .footer      {{ font-size: 16px; font-weight: 400; opacity: 0.78; font-style: italic; }}
      .panel-title {{ font-size: 22px; font-weight: 700; fill: {panel_text}; }}
      .panel-cap   {{ font-size: 14px; font-weight: 500; opacity: 0.95;  fill: {panel_text}; }}
      .eq          {{ font-size: 22px; font-weight: 500; fill: {panel_text}; font-style: italic; }}
      /* Source-panel color binding for flow labels lives on inline
         `fill=` attributes on the tspans -- Affinity Designer does not
         reliably honor CSS fill rules from a <style> block. */
    ]]></style>
    <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5"
            markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="{arrow_color}"/>
    </marker>
    <marker id="arrow-w" viewBox="0 0 10 10" refX="9" refY="5"
            markerWidth="5" markerHeight="5" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#EDE4D3"/>
    </marker>
    <!-- Subtle drop shadow to lift the panels off the background.
         x/y/width/height extended so the shadow isn't clipped. -->
    <filter id="panel-elevation" x="-10%" y="-10%" width="120%" height="125%">
      <feDropShadow dx="0" dy="4" stdDeviation="6"
                    flood-color="#000000" flood-opacity="{shadow_opacity}"/>
    </filter>
  </defs>

  <!-- Title -->
  <text font-family="Inter" x="600" y="58" text-anchor="middle" class="title">THAMES</text>
  <text font-family="Inter" x="600" y="89" text-anchor="middle" class="subtitle">Coupled cement-hydration modeling: thermodynamics, kinetics, and microstructure</text>

  <!-- PANEL 1 (top): 3D MICROSTRUCTURE - ember -->
  <g id="panel-microstructure" transform="translate(450, 130)">
    <rect width="300" height="260" rx="14" fill="#E07A2C" filter="url(#panel-elevation)"/>
    <text font-family="Inter" x="150" y="36" text-anchor="middle" class="panel-title">3D Microstructure</text>
    <image x="20" y="55" width="260" height="180" preserveAspectRatio="xMidYMid meet"
           xlink:href="data:image/png;base64,{micro_b64}"/>
    <text font-family="Inter" x="150" y="248" text-anchor="middle" class="panel-cap">voxel lattice • phase identity per cell</text>
  </g>

  <!-- PANEL 2 (bottom-left): GEMS THERMODYNAMICS - teal -->
  <g id="panel-gems" transform="translate(150, 560)">
    <rect width="300" height="260" rx="14" fill="#397B8A" filter="url(#panel-elevation)"/>
    <text font-family="Inter" x="150" y="36" text-anchor="middle" class="panel-title">GEMS3K Thermodynamics</text>
    <image x="35" y="50" width="230" height="180" preserveAspectRatio="xMidYMid meet"
           xlink:href="data:image/png;base64,{gibbs_b64}"/>
    <text font-family="Inter" x="150" y="248" text-anchor="middle" class="panel-cap">minimize <tspan font-style="italic">G</tspan> • equilibrium phase assemblage</text>
  </g>

  <!-- PANEL 3 (bottom-right): KINETIC CONSTRAINTS - jade -->
  <g id="panel-kinetics" transform="translate(750, 560)">
    <rect width="300" height="260" rx="14" fill="#5FAA82" filter="url(#panel-elevation)"/>
    <text font-family="Inter" x="150" y="36" text-anchor="middle" class="panel-title">Kinetic Constraints</text>
    <g transform="translate(150, 120)">
      <circle r="62" fill="none" stroke="#EDE4D3" stroke-dasharray="4 4" stroke-width="1.4" opacity="0.6"/>
      <circle r="38" fill="#EDE4D3" fill-opacity="0.92" stroke="#EDE4D3" stroke-width="2"/>
      <text font-family="Inter" y="6" text-anchor="middle" fill="#5A2A0E" font-size="14" font-weight="700">C₃S</text>
      <g stroke="#EDE4D3" stroke-width="1.6" fill="none">
        <path d="M 0 -72 L 0 -45"   marker-end="url(#arrow-w)"/>
        <path d="M 51 -51 L 32 -32" marker-end="url(#arrow-w)"/>
        <path d="M 72 0 L 45 0"     marker-end="url(#arrow-w)"/>
        <path d="M 51 51 L 32 32"   marker-end="url(#arrow-w)"/>
        <path d="M 0 72 L 0 45"     marker-end="url(#arrow-w)"/>
        <path d="M -51 51 L -32 32" marker-end="url(#arrow-w)"/>
        <path d="M -72 0 L -45 0"   marker-end="url(#arrow-w)"/>
        <path d="M -51 -51 L -32 -32" marker-end="url(#arrow-w)"/>
      </g>
    </g>
    <image x="40" y="190" width="220" height="44" preserveAspectRatio="xMidYMid meet"
           xlink:href="data:image/png;base64,{eq_b64}"/>
    <text font-family="Inter" x="150" y="248" text-anchor="middle" class="panel-cap">rate-limited dissolution • gating equilibrium</text>
  </g>

  <!-- FLOW ARROWS (diagonals + bottom edge) -->
  <g fill="none" stroke="{arrow_color}" stroke-width="2.2" opacity="0.88">
    {diagonal_paths_xml}
    <path d="{BOTTOM_TOP_CURVE}" marker-end="url(#arrow)"/>
    <path d="{BOTTOM_BOT_CURVE}" marker-end="url(#arrow)"/>
  </g>

  <!-- Rotated diagonal labels -->
{rot_labels_xml}

  <!-- Bottom-edge horizontal labels (single <text> with two <tspan> lines) -->
  <!-- Top label is sourced from GEMS (teal); bottom from kinetics (jade) -->
  <text font-family="Inter" x="600" y="612" text-anchor="middle">
    <tspan class="flow-label" fill="{SRC_TEAL}">saturation index Ω</tspan>
    <tspan x="600" dy="20" class="flow-sub">driving force for kinetics</tspan>
  </text>
  <text font-family="Inter" x="600" y="772" text-anchor="middle">
    <tspan class="flow-label" fill="{SRC_JADE}">DC upper limits</tspan>
    <tspan x="600" dy="20" class="flow-sub">kinetic cap on equilibrium</tspan>
  </text>

  <!-- Footer -->
  <text font-family="Inter" x="600" y="965" text-anchor="middle" class="footer">GEMS sets the equilibrium target • kinetics gates how fast it is approached • the lattice records where it happens</text>
</svg>
'''
    return svg


for theme in ("dark", "light"):
    out = DOCS / f"thames-architecture-triangle-{theme}.svg"
    out.write_text(build_svg(theme=theme), encoding="utf-8")
    print(f"Wrote {out}  ({out.stat().st_size/1024:.1f} KB)")
