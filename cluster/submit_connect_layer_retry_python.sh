#!/bin/bash

# Retry of submit_connect_layer_missing_python.sh (run of 31/10/2026, removed in 8118cd9). That job was
# still running when the repo was updated to 8af6630, which imports numpy, and the conda env had no numpy:
# from 02/11 20:28 on every process failed on import. Of its 261 instances, 19 got k*, 39 hit the 4h
# timeout or the out-of-memory handler (not retried: they would fail again), and 203 failed with the
# import error (162 Set Cover, 35 Sequencing, 6 Independent Set). This script runs step 1 for those 203
# and step 2 for them plus the 19 whose k* is in PREVIOUS_CONNECT_LAYERS_FILE (all their step 2 failed).
# Same timeouts and memory as the original, so its rows can be merged with the previous runs.
# Requires numpy in the conda env (pip install numpy).

#SBATCH --job-name=dd-connect-layer-retry-python
#SBATCH --output=/home1/%u/compact-dd-suite-results/salidas/python/salida_connect_layer_retry_python.txt
#SBATCH --partition=gpus
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=3
#SBATCH --mem=96G
#SBATCH --mail-user=antonia.blanco@uc.cl
#SBATCH --mail-type=ALL

source ~/.bashrc
conda activate py3.12.9 || { echo "❌ Failed to activate the conda env"; exit 1; }

mkdir -p "$HOME/compact-dd-suite-results/results/python"
mkdir -p "$HOME/compact-dd-suite-results/timeout_log/python"

cd "$HOME/compact-dd-suite/DD_python" || { echo "❌ Directory not found"; exit 1; }
echo "Directory: $(pwd)"
echo "Commit: $(git -C "$HOME/compact-dd-suite" rev-parse --short HEAD)"

DATE="$(date '+%d_%m_%Y_%H-%M-%S')"
INSTANCES_DIR="$HOME/compact-dd-suite/DataInstances"
LOG_TIMEOUT="$HOME/compact-dd-suite-results/timeout_log/python/timeout_log_connect_layer_retry_python_$DATE.txt"
CONNECT_LAYERS_FILE="$HOME/compact-dd-suite-results/results/python/connect_layers_retry_python_$DATE.csv"
OUTPUT_FILE="$HOME/compact-dd-suite-results/results/python/results_semi_kopt_retry_python_$DATE.csv"
PREVIOUS_CONNECT_LAYERS_FILE="$HOME/compact-dd-suite-results/results/python/connect_layers_missing_python_31_10_2026_17-27-47.csv"
MAX_PARALLEL=3      # Must equal --cpus-per-task: ~32G of --mem per process
TIMEOUT_K=4h        # Step 1: was 60m
TIMEOUT_EXACT=60m   # Step 2, Exact (same as submit_connect_layer_python.sh)
TIMEOUT_WIDTH=5m    # Step 2, Restricted / RelaxPriority (same as submit_connect_layer_python.sh)
pids=()
metadata=()

declare -A OBJECTIVE=(
    [Knapsack]="Max"
    [IndependentSet]="Max"
    [SetCover]="Min"
    [SOCKnapsack]="Max"
    [Sequencing]="Min"
)

TYPES=("Exact" "Restricted" "RelaxPriority") # There is no grouping sMDD
MODES=("Reduce" "NoReduce")
WIDTHS=(500 1000 2000 5000 10000 20000)

# Instances whose k* failed with the numpy import error in the run of 31/10/2026, relative to DataInstances/. The first folder is the
# problem flag. Ordered by how likely they are to finish, so the useful ones come out first.
INSTANCES=(
    # 3) Timeout at 60m
    "IndependentSet/Standard/san400_0.7_3.txt"
    "IndependentSet/Standard/san400_0.9_1.txt"
    "IndependentSet/Standard/san1000.txt"
    "IndependentSet/Standard/sanr200_0.7.txt"
    "IndependentSet/Standard/sanr200_0.9.txt"
    "IndependentSet/Standard/sanr400_0.7.txt"
    "SetCover/Standard/set_cover_n100_m63_d0.1_b_w38_seed1.txt"
    "SetCover/Standard/set_cover_n100_m63_d0.1_b_w38_seed2.txt"
    "SetCover/Standard/set_cover_n100_m63_d0.1_b_w38_seed3.txt"
    "SetCover/Standard/set_cover_n100_m63_d0.1_b_w38_seed4.txt"
    "SetCover/Standard/set_cover_n100_m63_d0.2_b_w38_seed1.txt"
    "SetCover/Standard/set_cover_n100_m63_d0.2_b_w38_seed2.txt"
    "SetCover/Standard/set_cover_n100_m63_d0.2_b_w38_seed3.txt"
    "SetCover/Standard/set_cover_n100_m63_d0.2_b_w38_seed4.txt"
    "SetCover/Standard/set_cover_n100_m63_d0.05_b_w38_seed2.txt"
    "SetCover/Standard/set_cover_n100_m63_d0.05_b_w38_seed3.txt"
    "SetCover/Standard/set_cover_n100_m63_d0.05_b_w38_seed4.txt"
    "SetCover/Standard/set_cover_n100_m63_d0.15_b_w38_seed1.txt"
    "SetCover/Standard/set_cover_n100_m63_d0.15_b_w38_seed2.txt"
    "SetCover/Standard/set_cover_n100_m63_d0.15_b_w38_seed3.txt"
    "SetCover/Standard/set_cover_n100_m63_d0.15_b_w38_seed4.txt"
    "SetCover/Standard/set_cover_n100_m66_d0.1_b_w35_seed2.txt"
    "SetCover/Standard/set_cover_n100_m66_d0.1_b_w35_seed3.txt"
    "SetCover/Standard/set_cover_n100_m66_d0.1_b_w35_seed4.txt"
    "SetCover/Standard/set_cover_n100_m66_d0.2_b_w35_seed1.txt"
    "SetCover/Standard/set_cover_n100_m66_d0.2_b_w35_seed2.txt"
    "SetCover/Standard/set_cover_n100_m66_d0.2_b_w35_seed3.txt"
    "SetCover/Standard/set_cover_n100_m66_d0.2_b_w35_seed4.txt"
    "SetCover/Standard/set_cover_n100_m66_d0.05_b_w35_seed3.txt"
    "SetCover/Standard/set_cover_n100_m66_d0.05_b_w35_seed4.txt"
    "SetCover/Standard/set_cover_n100_m66_d0.15_b_w35_seed1.txt"
    "SetCover/Standard/set_cover_n100_m66_d0.15_b_w35_seed2.txt"
    "SetCover/Standard/set_cover_n100_m66_d0.15_b_w35_seed3.txt"
    "SetCover/Standard/set_cover_n100_m66_d0.15_b_w35_seed4.txt"
    "SetCover/Standard/set_cover_n100_m69_d0.1_b_w32_seed1.txt"
    "SetCover/Standard/set_cover_n100_m69_d0.1_b_w32_seed2.txt"
    "SetCover/Standard/set_cover_n100_m69_d0.1_b_w32_seed3.txt"
    "SetCover/Standard/set_cover_n100_m69_d0.1_b_w32_seed4.txt"
    "SetCover/Standard/set_cover_n100_m69_d0.2_b_w32_seed2.txt"
    "SetCover/Standard/set_cover_n100_m69_d0.2_b_w32_seed3.txt"
    "SetCover/Standard/set_cover_n100_m69_d0.05_b_w32_seed1.txt"
    "SetCover/Standard/set_cover_n100_m69_d0.05_b_w32_seed2.txt"
    "SetCover/Standard/set_cover_n100_m69_d0.05_b_w32_seed3.txt"
    "SetCover/Standard/set_cover_n100_m69_d0.05_b_w32_seed4.txt"
    "SetCover/Standard/set_cover_n100_m69_d0.15_b_w32_seed1.txt"
    "SetCover/Standard/set_cover_n100_m69_d0.15_b_w32_seed2.txt"
    "SetCover/Standard/set_cover_n100_m69_d0.15_b_w32_seed3.txt"
    "SetCover/Standard/set_cover_n100_m69_d0.15_b_w32_seed4.txt"
    "SetCover/Standard/set_cover_n100_m72_d0.1_b_w29_seed1.txt"
    "SetCover/Standard/set_cover_n100_m72_d0.1_b_w29_seed2.txt"
    "SetCover/Standard/set_cover_n100_m72_d0.1_b_w29_seed3.txt"
    "SetCover/Standard/set_cover_n100_m72_d0.1_b_w29_seed4.txt"
    "SetCover/Standard/set_cover_n100_m72_d0.2_b_w29_seed3.txt"
    "SetCover/Standard/set_cover_n100_m72_d0.05_b_w29_seed1.txt"
    "SetCover/Standard/set_cover_n100_m72_d0.05_b_w29_seed2.txt"
    "SetCover/Standard/set_cover_n100_m72_d0.05_b_w29_seed3.txt"
    "SetCover/Standard/set_cover_n100_m72_d0.05_b_w29_seed4.txt"
    "SetCover/Standard/set_cover_n100_m72_d0.15_b_w29_seed1.txt"
    "SetCover/Standard/set_cover_n100_m72_d0.15_b_w29_seed2.txt"
    "SetCover/Standard/set_cover_n100_m72_d0.15_b_w29_seed3.txt"
    "SetCover/Standard/set_cover_n100_m72_d0.15_b_w29_seed4.txt"
    "SetCover/Standard/set_cover_n100_m75_d0.1_b_w26_seed1.txt"
    "SetCover/Standard/set_cover_n100_m75_d0.1_b_w26_seed2.txt"
    "SetCover/Standard/set_cover_n100_m75_d0.1_b_w26_seed3.txt"
    "SetCover/Standard/set_cover_n100_m75_d0.1_b_w26_seed4.txt"
    "SetCover/Standard/set_cover_n100_m75_d0.05_b_w26_seed1.txt"
    "SetCover/Standard/set_cover_n100_m75_d0.05_b_w26_seed2.txt"
    "SetCover/Standard/set_cover_n100_m75_d0.05_b_w26_seed3.txt"
    "SetCover/Standard/set_cover_n100_m75_d0.05_b_w26_seed4.txt"
    "SetCover/Standard/set_cover_n100_m75_d0.15_b_w26_seed1.txt"
    "SetCover/Standard/set_cover_n100_m75_d0.15_b_w26_seed2.txt"
    "SetCover/Standard/set_cover_n100_m75_d0.15_b_w26_seed3.txt"
    "SetCover/Standard/set_cover_n100_m75_d0.15_b_w26_seed4.txt"
    "SetCover/Standard/set_cover_n100_m78_d0.1_b_w23_seed1.txt"
    "SetCover/Standard/set_cover_n100_m78_d0.1_b_w23_seed2.txt"
    "SetCover/Standard/set_cover_n100_m78_d0.1_b_w23_seed3.txt"
    "SetCover/Standard/set_cover_n100_m78_d0.1_b_w23_seed4.txt"
    "SetCover/Standard/set_cover_n100_m78_d0.05_b_w23_seed1.txt"
    "SetCover/Standard/set_cover_n100_m78_d0.05_b_w23_seed2.txt"
    "SetCover/Standard/set_cover_n100_m78_d0.05_b_w23_seed3.txt"
    "SetCover/Standard/set_cover_n100_m78_d0.05_b_w23_seed4.txt"
    "SetCover/Standard/set_cover_n100_m78_d0.15_b_w23_seed1.txt"
    "SetCover/Standard/set_cover_n100_m78_d0.15_b_w23_seed2.txt"
    "SetCover/Standard/set_cover_n100_m78_d0.15_b_w23_seed3.txt"
    "SetCover/Standard/set_cover_n100_m78_d0.15_b_w23_seed4.txt"
    "SetCover/Standard/set_cover_n100_m81_d0.1_b_w20_seed1.txt"
    "SetCover/Standard/set_cover_n100_m81_d0.1_b_w20_seed2.txt"
    "SetCover/Standard/set_cover_n100_m81_d0.1_b_w20_seed3.txt"
    "SetCover/Standard/set_cover_n100_m81_d0.1_b_w20_seed4.txt"
    "SetCover/Standard/set_cover_n100_m81_d0.05_b_w20_seed1.txt"
    "SetCover/Standard/set_cover_n100_m81_d0.05_b_w20_seed2.txt"
    "SetCover/Standard/set_cover_n100_m81_d0.05_b_w20_seed3.txt"
    "SetCover/Standard/set_cover_n100_m81_d0.05_b_w20_seed4.txt"
    "SetCover/Standard/set_cover_n100_m81_d0.15_b_w20_seed1.txt"
    "SetCover/Standard/set_cover_n100_m81_d0.15_b_w20_seed2.txt"
    "SetCover/Standard/set_cover_n100_m81_d0.15_b_w20_seed3.txt"
    "SetCover/Standard/set_cover_n100_m81_d0.15_b_w20_seed4.txt"
    "SetCover/Standard/set_cover_n100_m84_d0.1_b_w17_seed1.txt"
    "SetCover/Standard/set_cover_n100_m84_d0.1_b_w17_seed2.txt"
    "SetCover/Standard/set_cover_n100_m84_d0.1_b_w17_seed3.txt"
    "SetCover/Standard/set_cover_n100_m84_d0.1_b_w17_seed4.txt"
    "SetCover/Standard/set_cover_n100_m84_d0.05_b_w17_seed1.txt"
    "SetCover/Standard/set_cover_n100_m84_d0.05_b_w17_seed2.txt"
    "SetCover/Standard/set_cover_n100_m84_d0.05_b_w17_seed3.txt"
    "SetCover/Standard/set_cover_n100_m84_d0.05_b_w17_seed4.txt"
    "SetCover/Standard/set_cover_n100_m84_d0.15_b_w17_seed1.txt"
    "SetCover/Standard/set_cover_n100_m84_d0.15_b_w17_seed2.txt"
    "SetCover/Standard/set_cover_n100_m84_d0.15_b_w17_seed3.txt"
    "SetCover/Standard/set_cover_n100_m84_d0.15_b_w17_seed4.txt"
    "SetCover/Standard/set_cover_n250_m86_d0.3_b_w165_seed1.txt"
    "SetCover/Standard/set_cover_n250_m86_d0.3_b_w165_seed2.txt"
    "SetCover/Standard/set_cover_n250_m86_d0.3_b_w165_seed3.txt"
    "SetCover/Standard/set_cover_n250_m86_d0.3_b_w165_seed4.txt"
    "SetCover/Standard/set_cover_n500_m336_d0.15_b_w165_seed1.txt"
    "SetCover/Standard/set_cover_n500_m336_d0.15_b_w165_seed2.txt"
    "SetCover/Standard/set_cover_n500_m336_d0.15_b_w165_seed3.txt"
    "SetCover/Standard/set_cover_n500_m336_d0.15_b_w165_seed4.txt"
    "SetCover/Standard/set_cover_n750_m586_d0.1_b_w165_seed1.txt"
    "SetCover/Standard/set_cover_n750_m586_d0.1_b_w165_seed2.txt"
    "SetCover/Standard/set_cover_n750_m586_d0.1_b_w165_seed3.txt"
    "SetCover/Standard/set_cover_n750_m586_d0.1_b_w165_seed4.txt"
    "SetCover/Standard/set_cover_n1000_m836_d0.07_b_w165_seed1.txt"
    "SetCover/Standard/set_cover_n1000_m836_d0.07_b_w165_seed2.txt"
    "SetCover/Standard/set_cover_n1000_m836_d0.07_b_w165_seed3.txt"
    "SetCover/Standard/set_cover_n1000_m836_d0.07_b_w165_seed4.txt"
    "SetCover/Standard/set_cover_n1250_m1086_d0.06_b_w165_seed1.txt"
    "SetCover/Standard/set_cover_n1250_m1086_d0.06_b_w165_seed2.txt"
    "SetCover/Standard/set_cover_n1250_m1086_d0.06_b_w165_seed3.txt"
    "SetCover/Standard/set_cover_n1250_m1086_d0.06_b_w165_seed4.txt"
    "SetCover/Standard/set_cover_n1500_m1336_d0.05_b_w165_seed1.txt"
    "SetCover/Standard/set_cover_n1500_m1336_d0.05_b_w165_seed2.txt"
    "SetCover/Standard/set_cover_n1500_m1336_d0.05_b_w165_seed3.txt"
    "SetCover/Standard/set_cover_n1500_m1336_d0.05_b_w165_seed4.txt"
    "SetCover/Standard/set_cover_n1750_m1586_d0.04_b_w165_seed1.txt"
    "SetCover/Standard/set_cover_n1750_m1586_d0.04_b_w165_seed3.txt"
    "SetCover/Standard/set_cover_n1750_m1586_d0.04_b_w165_seed4.txt"
    "SetCover/Standard/set_cover_n2000_m1836_d0.04_b_w165_seed2.txt"
    "SetCover/Standard/set_cover_n2000_m1836_d0.04_b_w165_seed3.txt"
    "SetCover/Standard/set_cover_n2000_m1836_d0.04_b_w165_seed4.txt"
    "SetCover/Standard/set_cover_n2250_m2086_d0.03_b_w165_seed1.txt"
    "SetCover/Standard/set_cover_n2250_m2086_d0.03_b_w165_seed3.txt"
    "SetCover/Standard/set_cover_n2250_m2086_d0.03_b_w165_seed4.txt"
    "SetCover/Standard/set_cover_n2500_m2336_d0.03_b_w165_seed1.txt"
    "SetCover/Standard/set_cover_n2500_m2336_d0.03_b_w165_seed2.txt"
    "SetCover/Standard/set_cover_n2500_m2336_d0.03_b_w165_seed3.txt"
    "SetCover/Standard/set_cover_n2500_m2336_d0.03_b_w165_seed4.txt"
    "SetCover/Standard/set_cover_n2750_m2586_d0.03_b_w165_seed1.txt"
    "SetCover/Standard/set_cover_n2750_m2586_d0.03_b_w165_seed2.txt"
    "SetCover/Standard/set_cover_n2750_m2586_d0.03_b_w165_seed3.txt"
    "SetCover/Standard/set_cover_n2750_m2586_d0.03_b_w165_seed4.txt"
    "SetCover/Standard/set_cover_n3000_m2836_d0.03_b_w165_seed2.txt"
    "SetCover/Standard/set_cover_n3000_m2836_d0.03_b_w165_seed4.txt"
    "SetCover/Standard/set_cover_n3250_m3086_d0.02_b_w165_seed1.txt"
    "SetCover/Standard/set_cover_n3250_m3086_d0.02_b_w165_seed2.txt"
    "SetCover/Standard/set_cover_n3250_m3086_d0.02_b_w165_seed3.txt"
    "SetCover/Standard/set_cover_n3250_m3086_d0.02_b_w165_seed4.txt"
    "SetCover/Standard/set_cover_n3500_m3336_d0.02_b_w165_seed1.txt"
    "SetCover/Standard/set_cover_n3500_m3336_d0.02_b_w165_seed2.txt"
    "SetCover/Standard/set_cover_n3500_m3336_d0.02_b_w165_seed3.txt"
    "SetCover/Standard/set_cover_n3500_m3336_d0.02_b_w165_seed4.txt"
    "SetCover/Standard/set_cover_n3750_m3586_d0.02_b_w165_seed1.txt"
    "SetCover/Standard/set_cover_n3750_m3586_d0.02_b_w165_seed2.txt"
    "SetCover/Standard/set_cover_n3750_m3586_d0.02_b_w165_seed3.txt"
    "SetCover/Standard/set_cover_n3750_m3586_d0.02_b_w165_seed4.txt"
    "SetCover/Standard/set_cover_n4000_m3836_d0.02_b_w165_seed1.txt"
    "SetCover/Standard/set_cover_n4000_m3836_d0.02_b_w165_seed2.txt"
    "SetCover/Standard/set_cover_n4000_m3836_d0.02_b_w165_seed3.txt"
    "SetCover/Standard/set_cover_n4000_m3836_d0.02_b_w165_seed4.txt"
    # 4) Sequencing n >= 33: the exact DD has ~n·2^n states, almost surely out of reach
    "Sequencing/Standard/sequencing_atsp_ftv33_n33_seed1.txt"
    "Sequencing/Standard/sequencing_atsp_ftv33_n33_seed2.txt"
    "Sequencing/Standard/sequencing_atsp_ftv33_n33_seed3.txt"
    "Sequencing/Standard/sequencing_atsp_ftv33_n33_seed4.txt"
    "Sequencing/Standard/sequencing_atsp_ftv33_n33_seed5.txt"
    "Sequencing/Standard/sequencing_atsp_ftv35_n35_seed1.txt"
    "Sequencing/Standard/sequencing_atsp_ftv35_n35_seed2.txt"
    "Sequencing/Standard/sequencing_atsp_ftv35_n35_seed3.txt"
    "Sequencing/Standard/sequencing_atsp_ftv35_n35_seed4.txt"
    "Sequencing/Standard/sequencing_atsp_ftv35_n35_seed5.txt"
    "Sequencing/Standard/sequencing_atsp_ftv38_n38_seed1.txt"
    "Sequencing/Standard/sequencing_atsp_ftv38_n38_seed2.txt"
    "Sequencing/Standard/sequencing_atsp_ftv38_n38_seed3.txt"
    "Sequencing/Standard/sequencing_atsp_ftv38_n38_seed4.txt"
    "Sequencing/Standard/sequencing_atsp_ftv38_n38_seed5.txt"
    "Sequencing/Standard/sequencing_atsp_ftv44_n44_seed1.txt"
    "Sequencing/Standard/sequencing_atsp_ftv44_n44_seed2.txt"
    "Sequencing/Standard/sequencing_atsp_ftv44_n44_seed3.txt"
    "Sequencing/Standard/sequencing_atsp_ftv44_n44_seed4.txt"
    "Sequencing/Standard/sequencing_atsp_ftv44_n44_seed5.txt"
    "Sequencing/Standard/sequencing_atsp_ftv47_n47_seed1.txt"
    "Sequencing/Standard/sequencing_atsp_ftv47_n47_seed2.txt"
    "Sequencing/Standard/sequencing_atsp_ftv47_n47_seed3.txt"
    "Sequencing/Standard/sequencing_atsp_ftv47_n47_seed4.txt"
    "Sequencing/Standard/sequencing_atsp_ftv47_n47_seed5.txt"
    "Sequencing/Standard/sequencing_atsp_p43_n42_seed1.txt"
    "Sequencing/Standard/sequencing_atsp_p43_n42_seed2.txt"
    "Sequencing/Standard/sequencing_atsp_p43_n42_seed3.txt"
    "Sequencing/Standard/sequencing_atsp_p43_n42_seed4.txt"
    "Sequencing/Standard/sequencing_atsp_p43_n42_seed5.txt"
    "Sequencing/Standard/sequencing_atsp_ry48p_n47_seed1.txt"
    "Sequencing/Standard/sequencing_atsp_ry48p_n47_seed2.txt"
    "Sequencing/Standard/sequencing_atsp_ry48p_n47_seed3.txt"
    "Sequencing/Standard/sequencing_atsp_ry48p_n47_seed4.txt"
    "Sequencing/Standard/sequencing_atsp_ry48p_n47_seed5.txt"
)

# Instances that already got k* in the run of 31/10/2026 (PREVIOUS_CONNECT_LAYERS_FILE) but whose step 2
# failed with the numpy import error: step 1 skips them, step 2 runs them with that k*.
DONE_INSTANCES=(
    "SetCover/Standard/set_cover_n100_m72_d0.2_b_w29_seed1.txt"
    "SetCover/Standard/set_cover_n100_m75_d0.2_b_w26_seed3.txt"
    "SetCover/Standard/set_cover_n100_m75_d0.2_b_w26_seed1.txt"
    "SetCover/Standard/set_cover_n100_m72_d0.2_b_w29_seed2.txt"
    "SetCover/Standard/set_cover_n100_m72_d0.2_b_w29_seed4.txt"
    "SetCover/Standard/set_cover_n100_m69_d0.2_b_w32_seed1.txt"
    "SetCover/Standard/set_cover_n100_m69_d0.2_b_w32_seed4.txt"
    "SetCover/Standard/set_cover_n100_m75_d0.2_b_w26_seed2.txt"
    "SetCover/Standard/set_cover_n100_m75_d0.2_b_w26_seed4.txt"
    "IndependentSet/Standard/sanr400_0.5.txt"
    "SetCover/Standard/set_cover_n100_m66_d0.1_b_w35_seed1.txt"
    "Knapsack/Standard/knapPI_1_10000_1000_1.txt"
    "Knapsack/Standard/knapPI_2_10000_1000_1.txt"
    "Knapsack/Standard/knapPI_3_10000_1000_1.txt"
    "IndependentSet/Standard/brock200_4.txt"
    "IndependentSet/Standard/hamming8-4.txt"
    "IndependentSet/Standard/p_hat300-2.txt"
    "IndependentSet/Standard/p_hat1000-1.txt"
    "IndependentSet/Standard/san200_0.7_1.txt"
)

# Unlike submit_connect_layer_python.sh, every failure is logged, not only the timeouts: an
# out-of-memory kill exits with 137 (SIGKILL) and would otherwise only show up as "Killed" in salidas/.
wait_if_full() {
    local max_running="$1" status
    while (( ${#pids[@]} > max_running )); do
        for i in "${!pids[@]}"; do
            if ! kill -0 "${pids[$i]}" 2>/dev/null; then
                wait "${pids[$i]}"
                status=$?
                case $status in
                    0)   ;;
                    124) echo "$(date '+%F %T') ❌ Timeout: ${metadata[$i]#*|}" >> "$LOG_TIMEOUT" ;;
                    137) echo "$(date '+%F %T') ❌ Out of memory: ${metadata[$i]#*|} | exit code: $status" >> "$LOG_TIMEOUT" ;;
                    *)   echo "$(date '+%F %T') ❌ Error: ${metadata[$i]#*|} | exit code: $status" >> "$LOG_TIMEOUT" ;;
                esac
                unset "pids[$i]"
                unset "metadata[$i]"
            fi
        done
        (( ${#pids[@]} > max_running )) && sleep 1
    done
}

# launch <timeout> <description> <args of the python script...>
launch() {
    local max_timeout="$1" description="$2"
    shift 2
    echo "==== $description ===="
    timeout "$max_timeout" python "$@" &

    pid=$!
    pids+=($pid)
    metadata+=("$pid|$description")
    wait_if_full $((MAX_PARALLEL - 1))
}

# Parallel runs may write the header more than once when the CSV is created; keeps only the first.
dedupe_header() {
    [ -f "$1" ] || return
    awk 'NR == 1 { header = $0; print; next } $0 != header' "$1" > "$1.tmp" && mv "$1.tmp" "$1"
}

# Prints the k* of the instance file name given, or nothing if it was not computed. Looks in this
# run's file first and then in PREVIOUS_CONNECT_LAYERS_FILE.
get_connect_layer() {
    local layers_file k
    for layers_file in "$CONNECT_LAYERS_FILE" "$PREVIOUS_CONNECT_LAYERS_FILE"; do
        [ -f "$layers_file" ] || continue
        k=$(awk -F, -v f="$1" 'NR == 1 { for (i = 1; i <= NF; i++) if ($i == "K Opt") c = i; next }
                               $1 == f { print $c; exit }' "$layers_file")
        [ -n "$k" ] && { echo "$k"; return; }
    done
}

# ── Step 1: k* per instance ──────────────────────────────────────────────────
echo "######## Step 1: connection layer k* (${#INSTANCES[@]} instances) -> $CONNECT_LAYERS_FILE ########"
for instance in "${INSTANCES[@]}"; do
    file="$INSTANCES_DIR/$instance"
    if [ ! -f "$file" ]; then
        echo "❌ $file not found, skipped"
        continue
    fi
    problem="${instance%%/*}"
    launch "$TIMEOUT_K" "k* | $file" compute_connect_layer.py "$file" -$problem -Output_"$CONNECT_LAYERS_FILE"
done
wait_if_full 0
dedupe_header "$CONNECT_LAYERS_FILE"

if [ ! -f "$PREVIOUS_CONNECT_LAYERS_FILE" ]; then
    echo "⚠️  $PREVIOUS_CONNECT_LAYERS_FILE not found: step 2 skips the ${#DONE_INSTANCES[@]} DONE_INSTANCES"
fi

# ── Step 2: sMDD with -ConnectLayer_<k*> ─────────────────────────────────────
echo "######## Step 2: sMDD with k* -> $OUTPUT_FILE ########"
for instance in "${DONE_INSTANCES[@]}" "${INSTANCES[@]}"; do
    file="$INSTANCES_DIR/$instance"
    problem="${instance%%/*}"
    objective="${OBJECTIVE[$problem]}"

    k=$(get_connect_layer "$(basename "$file")")
    if [ -z "$k" ]; then
        echo "⚠️  $file has no k*, skipped"
        continue
    fi

    for type in "${TYPES[@]}"; do
        for mode in "${MODES[@]}"; do
            args=(main.py "$file" -$problem -$type -Semi -ConnectLayer_"$k" -$objective -Output_"$OUTPUT_FILE")
            [ "$mode" == "Reduce" ] && args+=(-Reduce)

            if [ "$type" == "Exact" ]; then
                launch "$TIMEOUT_EXACT" "$file | k=$k | $type | $mode" "${args[@]}"
            else
                for width in "${WIDTHS[@]}"; do
                    launch "$TIMEOUT_WIDTH" "$file | k=$k | $type | $mode | $width" "${args[@]}" -Width_"$width"
                done
            fi
        done
    done
done
wait_if_full 0
dedupe_header "$OUTPUT_FILE"

echo "✅ Finished. k*: $CONNECT_LAYERS_FILE | Results: $OUTPUT_FILE"
