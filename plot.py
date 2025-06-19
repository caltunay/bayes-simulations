import matplotlib.pyplot as plt
import numpy as np
import streamlit as st

def plot_rope(d_list, rope_thresholds=(.05, .95)):

    stat_sig_stats = {} 
    for d in d_list: 
        if float(d['in_rope_percentage'].values[-1]) >= .95 or float(d['in_rope_percentage'].values[-1]) <= .05: 
            num_days_for_stat_sig = (d['date'].iloc[-1] - d['date'].iloc[0]).days
            if 'reached_stat_sig_sample_size' not in stat_sig_stats:
                stat_sig_stats['reached_stat_sig_sample_size'] = [d['total_sample_size'].values[-1]] 
                stat_sig_stats['reached_stat_sig_num_days'] = [num_days_for_stat_sig]
            else:
                stat_sig_stats['reached_stat_sig_sample_size'].append(d['total_sample_size'].values[-1])
                stat_sig_stats['reached_stat_sig_num_days'].append(num_days_for_stat_sig)
        else:
            if 'didnot_reached_stat_sig_sample_size' not in stat_sig_stats:
                stat_sig_stats['didnot_reached_stat_sig_sample_size'] = [d['total_sample_size'].values[-1]] 
            else:
                stat_sig_stats['didnot_reached_stat_sig_sample_size'].append(d['total_sample_size'].values[-1]) 

    if 'reached_stat_sig_sample_size' in stat_sig_stats:
        avg_sample_size = np.mean(stat_sig_stats['reached_stat_sig_sample_size'])
        avg_num_days = np.mean(stat_sig_stats['reached_stat_sig_num_days'])
    else:
        avg_sample_size = "No experiment reached statistical significance within the given parameters."

    # start fig and ax
    fig, ax1 = plt.subplots(figsize=(12, 6))

    # loop through and plot
    color_map = plt.cm.get_cmap("tab10", len(d_list))  # Generate different colors for each line
    for idx, d in enumerate(d_list):
        color = color_map(idx)
        ax1.plot(d['date'], d['in_rope_percentage'], marker='s', linestyle='--', color=color)

    # rope thresholds
    ax1.axhline(y=rope_thresholds[1], color='darkred', linestyle=':', linewidth=1.5, label="ROPE Threshold (95%)")
    ax1.axhline(y=rope_thresholds[0], color='darkred', linestyle=':', linewidth=1.5, label="ROPE Threshold (5%)")
    
    # titles
    fig.suptitle("Posterior ROPE Percentage Over Sample Sizes")
    fig.tight_layout()
    fig.legend(loc="lower left", bbox_to_anchor=(0.1, 0.95))
    plt.xticks(rotation=45)
    st.pyplot(fig)
    
    st.write(f"Average sample size to conclusive experiment: {avg_sample_size}")
    st.write(f"Average number of days to conclusive experiment: {avg_num_days}")