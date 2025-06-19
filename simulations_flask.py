import pymc as pm
import pandas as pd
import numpy as np

import arviz as az
import matplotlib.pyplot as plt
import seaborn as sns

def calculate_expected_loss(control_simulation, treatment_simulation, treatment_won, min_difference_delta=0):
    # calculate loss for control and treatment based on the simulation values
    loss_control = [max((j - min_difference_delta) - i, 0) for i,j in zip(control_simulation, treatment_simulation)]
    loss_treatment = [max(i - (j - min_difference_delta), 0) for i,j in zip(control_simulation, treatment_simulation)]

    all_loss_control = [int(i)*j for i,j in zip(treatment_won, loss_control)]
    all_loss_treatment = [(1 - int(i))*j for i,j in zip(treatment_won, loss_treatment)]

    expected_loss_control = np.mean(all_loss_control)
    expected_loss_treatment = np.mean(all_loss_treatment)
    return expected_loss_control, expected_loss_treatment


def calculate_ab_test_expected_loss(samples_A, samples_B, epsilon=0.05, min_difference_delta=0):
    # calculate treatment_won based on whether B has higher conversion rates than A
    treatment_won = [int(i < j) for i,j in zip(samples_A, samples_B)]
    
    # calculate expected loss for both control (A) and treatment (B)
    expected_loss_A, expected_loss_B = calculate_expected_loss(samples_A, samples_B, treatment_won, min_difference_delta)
    
    return expected_loss_A, expected_loss_B


def simulate_experiment(g, date_col='date', group_col='group', rope_bounds=(-0.02, 0.02)):

    # init priors
    alpha_prior_control, beta_prior_control = 1, 1
    alpha_prior_treatment, beta_prior_treatment = 1, 1
    
    # log dataframe
    log_columns = [
        "date", "mean_sample_size",
        "posterior_mean_control", "posterior_mean_treatment", "posterior_mean_difference",
        "hdi_94_lower_control", "hdi_94_upper_control",
        "hdi_94_lower_treatment", "hdi_94_upper_treatment",
        "hdi_94_lower_difference", "hdi_94_upper_difference",
        "probability_treatment_better", "in_rope_percentage",
        "expected_loss_A", "expected_loss_B"
    ]
    log_df = pd.DataFrame(columns=log_columns)

    log_df = log_df.astype({
        "mean_sample_size": 'float64',
        "posterior_mean_control": 'float64',
        "posterior_mean_treatment": 'float64',
        "posterior_mean_difference": 'float64',
        "hdi_94_lower_control": 'float64',
        "hdi_94_upper_control": 'float64',
        "hdi_94_lower_treatment": 'float64',
        "hdi_94_upper_treatment": 'float64',
        "hdi_94_lower_difference": 'float64',
        "hdi_94_upper_difference": 'float64',
        "probability_treatment_better": 'float64',
        "in_rope_percentage": 'float64',
        "expected_loss_A": 'float64',
        "expected_loss_B": 'float64'
    })
    
    # date order
    dates = sorted(g[date_col].unique())

    cumulative_control_conversions, cumulative_control_observations = 0, 0
    cumulative_treatment_conversions, cumulative_treatment_observations = 0, 0
    
    # rope boundaries
    rope_bounds = rope_bounds  
    
    # Store daily plots
    daily_plots = []  

    # main loop
    for i, date in enumerate(dates):
        print(f"Processing date: {date}")
    
        # slice for date
        control_data = g[(g[date_col] == date) & (g[group_col] == 'control')]
        treatment_data = g[(g[date_col] == date) & (g[group_col] == 'treatment')]
    
        if control_data.empty or treatment_data.empty:
            print(f"Skipping {date} due to missing data.")
            continue
    
        control_conversions = control_data['conversion'].values[0]
        control_observations = control_data['observation'].values[0]
        treatment_conversions = treatment_data['conversion'].values[0]
        treatment_observations = treatment_data['observation'].values[0]

        cumulative_control_conversions += control_conversions
        cumulative_control_observations += control_observations
        cumulative_treatment_conversions += treatment_conversions
        cumulative_treatment_observations += treatment_observations

        mean_sample_size = np.mean([control_observations, treatment_observations])
    
        # pymc model
        with pm.Model() as model:
            p_control = pm.Beta('p_control', alpha=alpha_prior_control, beta=beta_prior_control)
            p_treatment = pm.Beta('p_treatment', alpha=alpha_prior_treatment, beta=beta_prior_treatment)
            
            obs_control = pm.Binomial('obs_control', n=cumulative_control_observations, p=p_control, observed=cumulative_control_conversions)
            obs_treatment = pm.Binomial('obs_treatment', n=cumulative_treatment_observations, p=p_treatment, observed=cumulative_treatment_conversions)
            
            difference = pm.Deterministic('difference', p_treatment - p_control)
            
            trace = pm.sample(500, tune=100, return_inferencedata=True, progressbar=False, chains=2)
    
        # extract posteriors
        summary = az.summary(trace, var_names=["p_control", "p_treatment", "difference"], hdi_prob=0.94)
    
        posterior_mean_control = summary.at["p_control", "mean"]
        posterior_mean_treatment = summary.at["p_treatment", "mean"]
        posterior_mean_difference = summary.at["difference", "mean"]
    
        hdi_94_lower_control, hdi_94_upper_control = summary.at["p_control", "hdi_3%"], summary.at["p_control", "hdi_97%"]
        hdi_94_lower_treatment, hdi_94_upper_treatment = summary.at["p_treatment", "hdi_3%"], summary.at["p_treatment", "hdi_97%"]
        hdi_94_lower_difference, hdi_94_upper_difference = summary.at["difference", "hdi_3%"], summary.at["difference", "hdi_97%"]
    
        # P(B > A)
        difference_samples = trace['posterior']['difference']
        probability_treatment_better = (difference_samples > 0).mean().values
    
        # in ROPE %
        in_rope_percentage = ((difference_samples > rope_bounds[0]) & (difference_samples < rope_bounds[1])).mean()
    
        # extract posterior samples
        samples_control = trace['posterior']['p_control'].values.flatten()
        samples_treatment = trace['posterior']['p_treatment'].values.flatten()
        
        # expected loss cal
        expected_loss_A, expected_loss_B = calculate_ab_test_expected_loss(samples_control, samples_treatment)
    
        # append to log
        log_entry = pd.DataFrame([[
            date, mean_sample_size,
            posterior_mean_control, posterior_mean_treatment, posterior_mean_difference,
            hdi_94_lower_control, hdi_94_upper_control,
            hdi_94_lower_treatment, hdi_94_upper_treatment,
            hdi_94_lower_difference, hdi_94_upper_difference,
            probability_treatment_better, in_rope_percentage,
            expected_loss_A, expected_loss_B
        ]], columns=log_columns)
    
        log_df = pd.concat([log_df, log_entry], ignore_index=True)
    
        # update priors
        alpha_prior_control += control_conversions
        beta_prior_control += (control_observations - control_conversions)
        alpha_prior_treatment += treatment_conversions
        beta_prior_treatment += (treatment_observations - treatment_conversions)
        
        # plot posterior difference and capture as base64
        fig, ax = plt.subplots(figsize=(4, 2))
        az.plot_posterior(
            trace,
            var_names=["difference"],
            hdi_prob=0.94,
            rope=rope_bounds,
            ref_val=0,
            ax=ax,
            textsize=5
        )
        ax.set_title(f'Posterior Difference on {date.strftime("%Y-%m-%d")}', fontsize=5)
        
        # Convert plot to base64 string
        import io
        import base64
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=100, bbox_inches='tight')
        img_buffer.seek(0)
        img_str = base64.b64encode(img_buffer.getvalue()).decode()
        daily_plots.append({
            'date': date.strftime("%Y-%m-%d"),
            'day': i + 1,
            'plot': img_str
        })
        plt.close(fig)
        
        if i >14 and (in_rope_percentage >= .95 or in_rope_percentage <= .05):
            break

    log_df['total_sample_size'] = log_df['mean_sample_size'].cumsum()
    log_df.daily_plots = daily_plots  # Attach daily plots to the dataframe
    return log_df
