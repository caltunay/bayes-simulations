from flask import Flask, render_template, request, jsonify, send_file
import datetime
import json
import io
import base64
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import tempfile
import os

from mock_data import create_mock_data
from simulations_flask import simulate_experiment

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/calculate', methods=['POST'])
def calculate():
    try:
        # Get form data
        data = request.get_json()
        baseline_cr = float(data.get('baseline_cr', 10))
        mde = float(data.get('mde', 1))
        daily_traffic = int(data.get('daily_traffic', 100))
        start_date_str = data.get('start_date', datetime.date.today().isoformat())
        
        # Parse start date
        start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
        
        rope_bounds = (-1 * mde/100, mde/100)
        experiment_data_list = []
        
        num_sims = 10
        results = []
        all_daily_plots = []
        
        for sim_num in range(1, num_sims + 1):
            # Create mock data and simulate experiment
            mock_data = create_mock_data(
                baseline_cr=baseline_cr/100, 
                mde=mde/100, 
                daily_sample_size=daily_traffic, 
                start_date=start_date.isoformat()
            )
            df = simulate_experiment(mock_data, rope_bounds=rope_bounds)
            experiment_data_list.append(df)
            
            # Collect daily plots from this simulation
            if hasattr(df, 'daily_plots'):
                for plot_data in df.daily_plots:
                    plot_data['simulation'] = sim_num
                    all_daily_plots.append(plot_data)
            
            # Send progress update
            progress = {
                'simulation': sim_num,
                'total': num_sims,
                'status': f'Running simulation {sim_num} out of {num_sims}...'
            }
            results.append(progress)
        
        # Generate the final plot
        plot_data = generate_plot_data(experiment_data_list)
        
        return jsonify({
            'success': True,
            'plot_data': plot_data,
            'daily_plots': all_daily_plots,
            'message': 'Calculation completed!'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def generate_plot_data(d_list, rope_thresholds=(.05, .95)):
    """Generate plot data similar to plot_rope function"""
    import numpy as np
    
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
        avg_num_days = "N/A"

    # Create plot
    fig, ax1 = plt.subplots(figsize=(12, 6))

    # Plot data for each simulation
    color_map = plt.cm.get_cmap("tab10", len(d_list))
    for idx, d in enumerate(d_list):
        color = color_map(idx)
        dates = [date.strftime('%Y-%m-%d') for date in d['date']]
        ax1.plot(dates, d['in_rope_percentage'], marker='s', linestyle='--', color=color)

    # Add ROPE thresholds
    ax1.axhline(y=rope_thresholds[1], color='darkred', linestyle=':', linewidth=1.5, label="ROPE Threshold (95%)")
    ax1.axhline(y=rope_thresholds[0], color='darkred', linestyle=':', linewidth=1.5, label="ROPE Threshold (5%)")
    
    # Set titles and formatting
    fig.suptitle("Posterior ROPE Percentage Over Sample Sizes")
    fig.tight_layout()
    fig.legend(loc="lower left", bbox_to_anchor=(0.1, 0.95))
    plt.xticks(rotation=45)
    
    # Convert plot to base64 string
    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
    img_buffer.seek(0)
    img_str = base64.b64encode(img_buffer.getvalue()).decode()
    plt.close(fig)
    
    return {
        'plot_image': img_str,
        'avg_sample_size': float(avg_sample_size) if isinstance(avg_sample_size, (int, float)) else str(avg_sample_size),
        'avg_num_days': float(avg_num_days) if isinstance(avg_num_days, (int, float)) else str(avg_num_days)
    }

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
