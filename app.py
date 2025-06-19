import streamlit as st

import time
import datetime

from mock_data import create_mock_data
from simulations import simulate_experiment
from plot import plot_rope

# main header
st.title("Bayesian Framework A/B Testing")

# secondary header
st.header("Sample Size Simulation for Conclusive Experiments")

st.markdown(
    """
    <div style="background-color: #7594f5; padding: 10px; border-radius: 10px; margin-bottom: 20px;">
        <strong>Disclaimer:</strong> This simulation generates mock data for two variants (control and treatment) over 30 days where means' difference are around practical significance with some noise.
        It simulates a worst-case scenario with daily updated priors to determine if a 
        Bayesian MCMC Sampling in an A/B test can reach a conclusive result within the specified practical significance level.
    </div>
    """, 
    unsafe_allow_html=True
)

st.markdown(
    """
    <div style="background-color: #7594f5; padding: 10px; border-radius: 10px; margin-bottom: 20px;">
        Each simulation will populate a single posterior distribution chart, and results will be populated at the bottom.
    </div>
    """, 
    unsafe_allow_html=True
)

with st.sidebar:
    baseline_cr = st.slider("Baseline Conversion Rate (%)", 1., 99., 10., step=0.1)
    mde = st.slider("Practical Significance (%)", 1., 50., 1., step=0.1)
    daily_traffic = st.number_input("Experiment Daily Traffic per Variant", min_value=1, value=100)
    start_date = st.date_input("Experiment Start Date", datetime.date.today())

    # Button to trigger calculation
    calculate_button = st.button('Calculate')

placeholder = st.empty()

if calculate_button:
    rope_bounds = (-1 * mde/100, mde/100)
    experiment_data_list = []

    with st.spinner("Simulations are running..."):
        num_sims = 10
        for _ in range(1, num_sims + 1):
            placeholder.text(f"Running simulation {_} out of {num_sims}...")

            mock_data = create_mock_data(baseline_cr=baseline_cr/100, mde=mde/100, daily_sample_size=daily_traffic, start_date=start_date)
            df = simulate_experiment(mock_data, rope_bounds=rope_bounds)
            experiment_data_list.append(df)
        plot_rope(experiment_data_list)
        
    st.success("Calculation completed!")
    st.cache_data.clear()

