"""Shared figure style for the paper figures."""

import matplotlib.pyplot as plt

ET_LABELS = ["0.55 (ET-1)", "1.10 (ET-2)", "1.65 (ET-3)", "2.20 (ET-4)", "2.75 (ET-5)"]
MARKERS = ["o", "s", "^", "D", "v", "P", "*", "X", "<", ">"]
COLORS = ["r", "g", "b", "c", "m", "y", "orange", "purple", "teal", "brown"]


def paper_axes(ax, xlabel, ylabel, ylim=(0.0, 3.5)):
    """Axis styling used in Figs. ex21-ex23."""
    ax.set_xlabel(xlabel, fontsize=14, fontweight="bold")
    ax.set_ylabel(ylabel, fontsize=14, fontweight="bold")
    ax.set_xticks(range(5), ET_LABELS, fontsize=12, fontweight="bold")
    ax.tick_params(axis="y", labelsize=12)
    ax.set_xlim(-0.4, 4.4)
    ax.set_ylim(*ylim)
    ax.grid(True, which="major", color="gray", linestyle="-", linewidth=0.5, alpha=0.5)
    leg = ax.legend(loc="best", fontsize=11, handlelength=4.0)
    for t in leg.get_texts():
        t.set_fontweight("bold")
    plt.tight_layout()
