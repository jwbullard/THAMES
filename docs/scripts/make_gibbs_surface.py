#!/usr/bin/env python3
"""Gibbs-energy-surface schematic for the THAMES architecture triangle.

Generates a transparent-background PNG showing a 3D free-energy landscape
with the equilibrium minimum marked in ember orange.  Designed to be
dropped into the GEMS panel of `thames-architecture-triangle.svg`.

Run with the THAMES master venv:
    ~/Code/Python/Envs/Default/bin/python make_gibbs_surface.py
"""
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401  (registers projection)

# THAMES palette
EMBER = "#E07A2C"
CREAM = "#EDE4D3"
TEAL  = "#397B8A"

n = 90
x = np.linspace(-1.7, 1.7, n)
y = np.linspace(-1.7, 1.7, n)
X, Y = np.meshgrid(x, y)

# Quadratic bowl plus a Gaussian well -> single clear minimum slightly off-center
G = 0.45 * (X**2 + Y**2) - 1.35 * np.exp(-((X - 0.25) ** 2 + (Y - 0.10) ** 2) / 0.55)

# Locate the minimum
i, j = np.unravel_index(np.argmin(G), G.shape)
xmin, ymin, gmin = X[i, j], Y[i, j], G[i, j]
gfloor = G.min() - 0.45

fig = plt.figure(figsize=(6.4, 4.8), facecolor="none")
ax = fig.add_subplot(111, projection="3d", facecolor="none", computed_zorder=False)

# Surface
ax.plot_surface(
    X, Y, G,
    cmap="magma",
    alpha=0.93,
    linewidth=0,
    antialiased=True,
    rstride=2, cstride=2,
    zorder=1,
)

# Contour projection on the "floor"
ax.contour(X, Y, G, zdir="z", offset=gfloor, cmap="magma", alpha=0.55, levels=14, zorder=0)

# Drop line from minimum to floor
ax.plot(
    [xmin, xmin], [ymin, ymin], [gfloor, gmin],
    color=EMBER, linewidth=2.2, linestyle="--", alpha=0.85, zorder=5,
)
# Floor marker (projected minimum)
ax.scatter([xmin], [ymin], [gfloor], color=EMBER, s=60, edgecolor=CREAM, linewidth=1.2, zorder=6)
# Surface marker (true minimum)
ax.scatter([xmin], [ymin], [gmin], color=EMBER, s=180, edgecolor=CREAM, linewidth=2.0, zorder=10)

# Equilibrium annotation
ax.text(
    xmin + 0.55, ymin + 0.30, gmin + 0.35,
    r"$G_{\min}$  (equilibrium)",
    color=CREAM, fontsize=12, ha="left", zorder=20,
)

# Axes
ax.set_xlabel(r"$\xi_1$", color=CREAM, fontsize=13, labelpad=-8)
ax.set_ylabel(r"$\xi_2$", color=CREAM, fontsize=13, labelpad=-8)
ax.set_zlabel(r"$G$",      color=CREAM, fontsize=14, labelpad=-8)
ax.set_xticks([]); ax.set_yticks([]); ax.set_zticks([])

# Transparent panes with faint edges so the box reads as a 3D volume
for pane in (ax.xaxis.pane, ax.yaxis.pane, ax.zaxis.pane):
    pane.fill = False
    pane.set_edgecolor((1.0, 1.0, 1.0, 0.15))
ax.grid(False)

# Camera
ax.view_init(elev=24, azim=-58)

# Trim figure margins
plt.subplots_adjust(left=0.02, right=0.98, top=0.98, bottom=0.02)

out = "/Users/jwbullard/Code/THAMES/docs/gibbs-surface.png"
plt.savefig(out, dpi=220, transparent=True, bbox_inches="tight", pad_inches=0.05)
print(f"Wrote {out}")
