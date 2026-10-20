#!/bin/bash

# Job name
#SBATCH --job-name=dd-dry-run-submit
#SBATCH --output=/home1/%u/compact-dd-suite-results/salidas/dry_run_submit_output.txt
#SBATCH --partition=gpus
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=5
#SBATCH --mail-user=
#SBATCH --mail-type=ALL

# Create the top-level folder
mkdir -p "$HOME/compact-dd-suite-results"

# Create the folder where the outputs are stored
mkdir -p "$HOME/compact-dd-suite-results/salidas"
mkdir -p "$HOME/compact-dd-suite-results/salidas/python"
mkdir -p "$HOME/compact-dd-suite-results/salidas/cpp"
mkdir -p "$HOME/compact-dd-suite-results/salidas/rust"

# Activate the conda environment
source ~/.bashrc
conda activate py3.12.9 || { echo "❌ Failed to activate the conda env"; exit 1; }

echo "Current working directory at start:"
pwd

### PYTHON DRY RUN SCRIPT ###

# Create the folders if they do not exist
mkdir -p "$HOME/compact-dd-suite-results/results/python"
mkdir -p "$HOME/compact-dd-suite-results/timeout_log/python"

cd "$HOME/compact-dd-suite/DD_python"  || { echo "❌ Directory not found"; exit 1; }

echo "Changed to directory:"
pwd
sleep 1

problem="Knapsack"

mapfile -t FILES < <(ls $HOME/compact-dd-suite/DataInstances/$problem/Standard/*.txt | sort -V)

LOG_TIMEOUT="$HOME/compact-dd-suite-results/timeout_log/python/timeout_log_python_$(date '+%d_%m_%Y_%H-%M-%S').txt"
MAX_TIMEOUT=5m # Maximum wait time per process (s: seconds, m: minutes, h: hours)
file="${FILES[15]#../}"
OUTPUT_FILE="$HOME/compact-dd-suite-results/results/python/results_all_$(date '+%d_%m_%Y_%H-%M-%S').csv"

timeout "$MAX_TIMEOUT" python main.py "$file" -$problem -RelaxPriority -Reduce -Max -Width_100 -Output_"$OUTPUT_FILE"

if [[ $? -eq 124 ]]; then
    echo "❌ Timeout reached for $file" >> "$LOG_TIMEOUT"
else
    echo "✅ Process completed successfully for $file"
fi

cd "$HOME" || { echo "❌ Could not return to the HOME directory"; exit 1; }


