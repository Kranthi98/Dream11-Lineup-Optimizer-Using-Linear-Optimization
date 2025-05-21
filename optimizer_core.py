# -*- coding: utf-8 -*-
"""
Created on Thu May 22 00:39:46 2025

@author: SHIVA
"""

# optimizer_core.py

from ortools.linear_solver import pywraplp
import pandas as pd
from constraints import position_constraints, team_constraints, squad_constraints, lineup_pos_order
from utils import adjust_projection, sort_players
import numpy as np
import statistics

# Paste in: generate_diverse_lineups, optimize_lineups, optimize_single_lineup
# from your original codebase here, using the modular constraints above

# Settings you can tweak
drop_mu, drop_sigma = 0.95, 0.05
boost_mu, boost_sigma = 1.1, 0.075
unpicked_mu, unpicked_sigma = 1.4, 0.075
selected_boost_weight = 0.2  # Strength of boost for low ownership

def adjust_projection(row, selected, player_counts, n, exposure_limit, drop_mu, drop_sigma, boost_mu, boost_sigma, unpicked_mu, unpicked_sigma, selected_boost_weight):
    # Base randomness
    if row["Player"] in selected:
        return row["AdjProjection"] * np.random.normal(drop_mu, drop_sigma)

    # Never picked yet
    if player_counts[row.name] == 0:
        base = np.random.normal(unpicked_mu, unpicked_sigma)
    elif (player_counts[row.name] / (n + 1)) < exposure_limit:
        base = np.random.normal(boost_mu, boost_sigma)
    else:
        base = 1.0

    # Add Selection% boost if available
    if "Selection%" in row:
        selection_boost = 1 + ((1 - row["Selection%"]) * selected_boost_weight)
        base *= selection_boost

    return row["AdjProjection"] * base


def optimize_single_lineup(df, sport, stack_min=None,locked_players=None):
    salary = df.Credits.to_list()
    projection = df.AdjProjection.to_list()
    teams = df.Team.unique()

    solver = pywraplp.Solver.CreateSolver('CBC')
    if not solver:
        raise Exception("Solver not created.")

    # Decision variables
    choices = {i: solver.BoolVar(f'choice_{i}') for i in range(len(df))}

    # Objective: Maximize adjusted projection
    solver.Maximize(solver.Sum(choices[i] * projection[i] for i in range(len(df))))

    # Squad size
    solver.Add(solver.Sum(choices[i] for i in range(len(df))) == squad_constraints[sport])

    # Salary cap
    solver.Add(solver.Sum(choices[i] * salary[i] for i in range(len(df))) <= 100)

    # Team constraints (team[0] only)
    team_filter = list(df.Team == teams[0])
    solver.Add(solver.Sum(choices[i] * team_filter[i] for i in range(len(df))) >= team_constraints[sport][0])
    solver.Add(solver.Sum(choices[i] * team_filter[i] for i in range(len(df))) <= team_constraints[sport][1])

    # Position constraints
    for pos, (min_p, max_p) in position_constraints[sport].items():
        pos_filter = list(df.Pos == pos)
        solver.Add(solver.Sum(choices[i] * pos_filter[i] for i in range(len(df))) >= min_p)
        solver.Add(solver.Sum(choices[i] * pos_filter[i] for i in range(len(df))) <= max_p)

    # ✅ Stack constraints
    if stack_min:
        for stack_type, min_players in stack_min.items():
            stack_filter = list(df.Stack == stack_type)
            solver.Add(solver.Sum(choices[i] * stack_filter[i] for i in range(len(df))) >= min_players)

    # ✅ LOCKED PLAYER CONSTRAINTS
    if locked_players:
        for i, row in df.iterrows():
            if row["Player"] in locked_players:
                solver.Add(choices[i] == 1)

    # Solve
    status = solver.Solve()
    if status in [pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE]:
        selected_players = df.loc[[i for i in range(len(df)) if choices[i].solution_value() > 0.5], "Player"].tolist()
        return selected_players
    else:
        return None


def generate_diverse_lineups(df, sport, num_lineups, exposure_limit=0.5, stack_min=None, locked_players = None):
    
    lineups = []
    player_counts = pd.Series(0, index=df.index)

    df = df.copy()
    df["AdjProjection"] = df.Projection.copy()  # Initialize adjusted projections

    for n in range(num_lineups):
        selected = optimize_single_lineup(df, sport, stack_min=stack_min, locked_players = locked_players)
        if selected is None:
            break

        # Record the lineup
        lineups.append(selected)

        # Update player counts
        mask = df["Player"].isin(selected)
        player_counts[mask] += 1
        df["AdjProjection"] = df.apply(
            lambda row: adjust_projection(row, selected, player_counts, n, exposure_limit, drop_mu, drop_sigma, boost_mu, boost_sigma, unpicked_mu, unpicked_sigma, selected_boost_weight),
            axis=1
        )

    if not lineups:
        return None

    # Prepare results
    all_results = []
    total_proj = []
    total_credits = []

    for lineup in lineups:
        players_df = df[df["Player"].isin(lineup)].copy()

        # Add symbols
        stack_symbols = players_df.Stack.map({1: "**", 2: "*", 0: ""})
        display_names = "(" + players_df.Pos + ")-" + players_df.Player + stack_symbols

        # Sort lineup by position
        ordered = []
        for pos in lineup_pos_order[sport]:
            ordered += [p for p in display_names if f"({pos})" in p]

        all_results.append(ordered)
        total_proj.append(players_df.Projection.sum())   # Or use AdjProjection.sum()
        total_credits.append(players_df.Credits.sum())

    # Final lineup DataFrame
    results = pd.DataFrame(all_results)
    results["TotalProjection"] = total_proj
    results["TotalCredits"] = total_credits
    top_projection = results["TotalProjection"].max()
    results["ProjectionDiff(%)"] = ((top_projection - results["TotalProjection"]) / top_projection * 100).round(2)

    return results

### OPTIMIZER 2 ###
def optimize_lineups(df, x, y, num_lineups, exp_diff):

    start = datetime.now(tz=ZoneInfo('Asia/Kolkata'))
    df["MinExposure"] = [x-exp_diff if x-exp_diff > 0 else 0 for x in df.Exposure]
    # Filter by projection threshold
    df = df.query(f"Projection >= {min_projection}").reset_index(drop=True)
    teams = df.Team.unique()

    # Create stack dummy variables (for each stack type: 0, 1, 2)
    stack_dummy = {
        0: (df["Stack"] == 1).astype(int).tolist(),
        1: (df["Stack"] == 2).astype(int).tolist(),
    }

    ms = 90*1000
    n_stack_i = {}
    n_stack_i[0] = x
    n_stack_i[1] = y
    # Add stack indicators to player names
    stack_symbols = df.Stack.map({1: "**", 2: "*", 0: ""})
    df.Player = df.Player + stack_symbols

    salary = df.Credits.to_list()
    projection = df.Projection.to_list()

    props = round((df.Exposure * num_lineups), 0).to_dict()
    min_props = round((df.MinExposure * num_lineups), 0).to_dict()
    props = {k: v for k, v in props.items() if v > 0}
    min_props = {k: v for k, v in min_props.items() if v > 0}

    solver = pywraplp.Solver.CreateSolver('CBC')
    if not solver:
        raise Exception("Solver not created.")

    # Decision variables
    choices = {}
    for i in range(len(df)):
        for j in range(num_lineups):
            choices[(i, j)] = solver.BoolVar(f'choice_{i}_{j}')

    # Objective: Maximize projection
    solver.Maximize(solver.Sum(choices[i, j] * projection[i] for i in range(len(df)) for j in range(num_lineups)))

    # Constraints
    for j in range(num_lineups):
        # Squad size
        solver.Add(solver.Sum(choices[i, j] for i in range(len(df))) == squad_constraints[sport])

        # Credit cap
        solver.Add(solver.Sum(choices[i, j] * salary[i] for i in range(len(df))) <= 100)

        # Team constraint (first team only)
        team_filter = list(df.Team == teams[0])
        solver.Add(solver.Sum(choices[i, j] * team_filter[i] for i in range(len(df))) >= team_constraints[sport][0])
        solver.Add(solver.Sum(choices[i, j] * team_filter[i] for i in range(len(df))) <= team_constraints[sport][1])

        # Position constraints
        for pos, (min_p, max_p) in position_constraints[sport].items():
            pos_filter = list(df.Pos == pos)
            solver.Add(solver.Sum(choices[i, j] * pos_filter[i] for i in range(len(df))) >= min_p)
            solver.Add(solver.Sum(choices[i, j] * pos_filter[i] for i in range(len(df))) <= max_p)

        # Avoid identical lineups
        if j > 0:
            prev_proj = [choices[i, j-1] * projection[i] for i in range(len(df))]
            curr_proj = [choices[i, j] * projection[i] for i in range(len(df))]
            solver.Add(solver.Sum(curr_proj) - solver.Sum(prev_proj) >= 0.001)

    # Exposure constraints
    for i in props:
        solver.Add(solver.Sum(choices[i, j] for j in range(num_lineups)) <= props[i])
    for i in min_props:
        solver.Add(solver.Sum(choices[i, j] for j in range(num_lineups)) >= min_props[i])

    # Stack constraints
    for k in range(len(n_stack_i)):
        for j in range(num_lineups):
            solver.Add(solver.Sum(choices[i, j] * stack_dummy[k][i] for i in range(len(df))) >= n_stack_i[k])

    solver.set_time_limit(ms)
    
    status = solver.Solve()
    if status == 0:
        print("Solver status: Optimal",)
    elif status == 1:
        print("Solver status : Feasible")


    if status in [pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE]:
        
        print(x,y,num_lineups)
        
        print(start)
        
        print(f"Solving for {num_lineups} Lineups with {x} of stack1 and {y} stack 2 players")
        print("Solution found!")
        print("Time Taken:", datetime.now(tz=ZoneInfo('Asia/Kolkata')) - start)

        selections = np.zeros((len(df), num_lineups))
        for i in range(len(df)):
            for j in range(num_lineups):
                if choices[i, j].solution_value() > 0.5:
                    selections[i, j] = 1

        d0 = pd.DataFrame(selections, columns=[f"lineup_{i+1}" for i in range(num_lineups)])
        d0["Player"] = "(" + df.Pos + ")-" + df.Player

        def sort_players(x):
            ordered = []
            for i in lineup_pos_order[sport]:
                ordered += [y for y in x if i + ")" in y]
            return ordered

        lineup_list = []
        for i in range(num_lineups):
            lineup = d0.query(f"lineup_{i+1} == 1").Player.to_list()
            lineup_list.append(sort_players(lineup))

        results = pd.DataFrame(lineup_list).assign(
            Projection=[sum(selections[:, i] * projection) for i in range(num_lineups)],
            Stdev = [statistics.variance(selections[:, i] * projection) for i in range(num_lineups)],
            Credits=[sum(selections[:, i] * salary) for i in range(num_lineups)]
        )
        print("Time Taken:", datetime.now(tz=ZoneInfo('Asia/Kolkata')) - start)
        print("\n")
        return results
    else:
        return 1
