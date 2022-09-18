import os
import time
import argparse
import pandas as pd
from evojax.train_masking import run_train_masking
from google.cloud import storage
from evojax.datasets import full_data_loader
from evojax.util import create_logger


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument('--number-of-seeds', type=int, default=5, help='How many seeds to test.')
    parser.add_argument('--epochs', type=int, default=20, help='Number of epochs.')

    parsed_config, _ = parser.parse_known_args()
    return parsed_config


def run_and_format_results(config_dict, run_name):
    results = {}
    for s in range(number_of_seeds):
        results[s] = run_train_masking(**config_dict, config_dict=config_dict, seed=s)
    return {(run_name, k2, k1): v2 for k1, v1 in results.items() for k2, v2 in v1.items()}


if __name__ == "__main__":
    config = parse_args()

    log_dir = './log/results'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    logger = create_logger(name='RESULTS', log_dir=log_dir, debug=False)

    client = storage.Client()
    bucket = client.get_bucket("evojax-bucket")
    file_name = f'results_run_{time.strftime("%m%d_%H%M")}.csv'
    file_path = os.path.join(log_dir, file_name)

    number_of_seeds = config.number_of_seeds
    datasets_tuple = full_data_loader()

    baseline_dict = dict(
        pop_size=16,
        batch_size=1024,
        cnn_epochs=config.epochs,
        cnn_lr=1e-3,
        early_stopping=False,
        datasets_tuple=datasets_tuple,
        logger=logger
    )

    baseline_results = run_and_format_results(baseline_dict, 'baseline')

    task_labels_dict = dict(**baseline_dict, use_task_labels=True)
    task_labels_results = run_and_format_results(task_labels_dict, 'task_labels')

    dropout_dict = dict(**baseline_dict, dropout_rate=0.5)
    dropout_results = run_and_format_results(dropout_dict, 'dropout')

    l1_reg_dict = dict(**baseline_dict, l1_reg_lambda=3e-5)
    l1_reg_results = run_and_format_results(l1_reg_dict, 'l1_reg')

    l1_pruning_dict = dict(**baseline_dict, l1_pruning_proportion=0.05)
    l1_pruning_results = run_and_format_results(l1_pruning_dict, 'l1_pruning')

    masking_params = dict(algo="PGPE",
                          pop_size=32,
                          mask_threshold=0.60,
                          max_iter=48,
                          evo_epochs=9,
                          test_interval=16,
                          log_interval=1000,
                          center_lr=0.0018,
                          std_lr=0.15,
                          init_std=0.039)
    masking_dict = dict(**baseline_dict, **masking_params)
    masking_dict["cnn_epochs"] = 3
    masking_results = run_and_format_results(masking_dict, 'masking')

    all_baselines = dict(**baseline_results,
                         **task_labels_results,
                         **dropout_results,
                         **l1_reg_results,
                         **l1_pruning_results,
                         **masking_results)

    df = pd.DataFrame(all_baselines).T
    df.to_csv(file_path)

    blob = bucket.blob(file_name)
    blob.upload_from_filename(file_path)





