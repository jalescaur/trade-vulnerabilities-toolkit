"""
src/viz/style_bw.py
===================
Print-friendly black and white / grayscale styling for matplotlib.
"""

import matplotlib.pyplot as plt
from cycler import cycler

def set_bw_style():
    """Applies a strict black, white, and grayscale style to all plots."""
    
    bw_cycler = (
        cycler(color=['#000000', '#444444', '#777777'] * 3) +
        cycler(linestyle=['-', '--', '-.'] * 3) +
        cycler(marker=['o', 's', '^', 'D', 'v', 'p', '*', 'X', '>'])
    )
    
    plt.rcParams.update({
        "figure.facecolor": "none",   # <-- Fundo da figura transparente
        "axes.facecolor": "none",     # <-- Fundo do gráfico transparente
        "axes.edgecolor": "black",
        "axes.labelcolor": "black",
        "axes.linewidth": 1.0,
        "axes.prop_cycle": bw_cycler,
        
        "axes.grid": True,
        "grid.color": "#DDDDDD",
        "grid.linestyle": "--",
        "grid.linewidth": 0.5,
        "axes.axisbelow": True,
        
        "xtick.color": "black",
        "ytick.color": "black",
        "xtick.direction": "out",
        "ytick.direction": "out",
        
        "font.family": "serif",
        "font.size": 11,
        "axes.titlesize": 13,
        "axes.labelsize": 11,
        
        "legend.frameon": False,
        "legend.edgecolor": "black",
        "legend.facecolor": "none",   # <-- Fundo da legenda transparente
        "legend.fontsize": 10,
        
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "savefig.format": "png",
        "savefig.transparent": True,  # <-- Força o canal alpha (transparência) na hora de salvar o PNG
    })

HATCHES = ['', '////', '....', 'xxx', '\\\\\\\\']
# Mantemos o #FFFFFF nas barras para que o fundo fique transparente, 
# mas as barras brancas continuem "sólidas" bloqueando as linhas de grade atrás delas.
GRAY_COLORS = ['#333333', '#888888', '#CCCCCC', '#FFFFFF']