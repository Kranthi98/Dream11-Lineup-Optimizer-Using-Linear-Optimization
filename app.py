# -*- coding: utf-8 -*-
"""
Created on Thu May 22 00:40:36 2025

@author: KRANTHI
"""

from optimizer_core import generate_diverse_lineups, optimize_lineups
from constraints import lineup_pos_order
import streamlit as st
import pandas as pd
from datetime import datetime

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # For Python < 3.9

# --- Import optimizer functions and dictionaries ---
# Ensure `generate_diverse_lineups`, `optimize_lineups`, etc., are in this file or imported

st.set_page_config(layout="wide", page_title="Fantasy Lineup Optimizer")

st.title("🏀 Fantasy Lineup Optimizer")
st.markdown("Build optimized fantasy basketball lineups for small and grand leagues.")

# --- Upload CSV ---
uploaded_file = st.file_uploader("Upload CSV", type=["csv"])
if uploaded_file:
    df = pd.read_csv(uploaded_file)
    df.rename(columns={"GP": "Projection", "Name": "Player"}, inplace=True)
    df["Exclude"] = df.get("Exclude", 0)
    df = df.query("Exclude == 0").reset_index(drop=True)

    st.success(f"{len(df)} players loaded!")

    # --- Parameter Inputs ---
    col1, col2, col3 = st.columns(3)
    with col1:
        sport = st.selectbox("Select Sport", ["Basketball", "Football", "Kabaddi", "Baseball"])
    with col2:
        opt_type = st.selectbox("Optimization Type", ["GL (Grand League)", "SL (Small League)"])
    with col3:
        num_lineups = st.slider("Number of Lineups", 1, 20, 10)

    min_proj = st.slider("Minimum Projection", 0.0, 20.0, 5.0)
    stack1 = st.slider("Min Players for Stack 1", 0, 5, 3)
    stack2 = st.slider("Min Players for Stack 2", 0, 5, 2)

    # --- Run Optimizer ---
    if st.button("🚀 Generate Lineups"):
        st.info("Running optimizer...")

        df = df.query(f"Projection >= {min_proj}").reset_index(drop=True)
        locked = df.query("Locked == 1")["Player"].tolist() if "Locked" in df.columns else []

        if opt_type.startswith("GL"):
            results1 = generate_diverse_lineups(
                df=df,
                sport=sport,
                num_lineups=num_lineups,
                exposure_limit=0.5,
                stack_min={1: stack1, 2: stack2},
                locked_players=locked
            )
            results2 = optimize_lineups(
                df=df,
                x=stack1,
                y=stack2,
                num_lineups=num_lineups,
                exp_diff=0.5
            ) 
            results = pd.concat([results1, results2], axis = 0).drop_duplicates([0,1,2,3,4,5,6,7]).sort_values("TotalProjection", ascending = False)
        else:
            results = optimize_lineups(
                df=df,
                x=stack1,
                y=stack2,
                num_lineups=num_lineups,
                exp_diff=0.5
            )

        if isinstance(results, pd.DataFrame):
            st.success(f"{len(results)} lineups generated!")
            st.dataframe(results)

            # Download CSV
            csv = results.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Download CSV", csv, "lineups.csv", "text/csv")
        else:
            st.error("Could not generate valid lineups. Try relaxing some constraints.")
