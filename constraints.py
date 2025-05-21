# -*- coding: utf-8 -*-
"""
Created on Thu May 22 00:38:44 2025

@author: SHIVA
"""

# constraints.py

position_constraints = {
    "Basketball": {"PG": [1, 4], "SF": [1, 4], "PF": [1, 4], "SG": [1, 4], "C": [1, 4]},
    "Football": {"GK": [1, 1], "DEF": [3, 5], "MID": [3, 5], "STR": [1, 3]},
    "Kabaddi": {"DEF": [1, 5], "ALL": [1, 5], "RAI": [1, 5]},
    "Baseball": {"OF": [2, 5], "IF": [2, 5], "C": [1, 1], "P": [1, 1]}
}

team_constraints = {
    "Basketball": [3, 5],
    "Football": [4, 7],
    "Kabaddi": [1, 6],
    "Baseball": [3, 6]
}

squad_constraints = {
    "Basketball": 8,
    "Football": 11,
    "Kabaddi": 7,
    "Baseball": 9
}

lineup_pos_order = {
    "Basketball": ["PG", "SG", "SF", "PF", "C"],
    "Football": ["GK", "DEF", "MID", "STR"],
    "Kabaddi": ["DEF", "ALL", "RAI"],
    "Baseball": ["OF", "IF", "P", "C"]
}
