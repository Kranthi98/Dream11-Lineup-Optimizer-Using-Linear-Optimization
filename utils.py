# -*- coding: utf-8 -*-
"""
Created on Thu May 22 00:39:22 2025

@author: SHIVA
"""

# utils.py
import numpy as np

def adjust_projection(row, selected, player_counts, n, exposure_limit,
                      drop_mu=0.9, drop_sigma=0.05, boost_mu=1.1, boost_sigma=0.075,
                      unpicked_mu=1.4, unpicked_sigma=0.075, selected_boost_weight=0.2):
    
    if row["Player"] in selected:
        return row["AdjProjection"] * np.random.normal(drop_mu, drop_sigma)

    if player_counts[row.name] == 0:
        base = np.random.normal(unpicked_mu, unpicked_sigma)
    elif (player_counts[row.name] / (n + 1)) < exposure_limit:
        base = np.random.normal(boost_mu, boost_sigma)
    else:
        base = 1.0

    if "Selection%" in row:
        base *= 1 + ((1 - row["Selection%"]) * selected_boost_weight)

    return row["AdjProjection"] * base


def sort_players(players, position_order):
    ordered = []
    for pos in position_order:
        ordered += [p for p in players if f"({pos})" in p]
    return ordered
