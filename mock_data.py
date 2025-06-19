import pandas as pd
import numpy as np

def create_mock_data(baseline_cr=.1, mde=.01, daily_sample_size=100, num_days=30, noise_level=5, start_date='2025-01-01'):
    # lists to hold the data
    groups = []
    conversions = []
    observations = []
    dates = []
    
    # covnert to datetime
    current_date = pd.to_datetime(start_date)
    
    # generate data series
    for day in range(num_days):
        for group in ['control', 'treatment']:
            # add random noise
            observation_count = np.random.normal(daily_sample_size, noise_level)
            observation_count = max(1, int(round(observation_count)))  # Ensure a positive integer
            
            # conversion rarte for each group
            if group == 'control':
                conversion_rate = baseline_cr
            else:
                # apply practical significance itself to treatment
                conversion_rate = baseline_cr * (1 + mde)
            
            # simulate conversion using binom distribution
            conversion = np.random.binomial(observation_count, conversion_rate)
            
            # append data
            groups.append(group)
            conversions.append(conversion)
            observations.append(observation_count)
            dates.append(current_date)
        
        # increment date by day
        current_date += pd.Timedelta(days=1)
    
    df = pd.DataFrame({
        'group': groups,
        'conversion': conversions,
        'observation': observations,
        'date': dates
    })
    
    return df