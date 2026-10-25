#!/bin/bash

# Re-runs the standard MDD (not sMDD) for Sequencing with the corrected
# SequencingPathSolver (commit d1a1192), to replace the Sequencing rows of
# data_visualization/data/python/original/results_python_10_08_2026_11-14-18.csv.
# Same grid as that baseline: Exact + Restricted/RelaxPriority/RelaxGrouping x widths x Reduce/NoReduce.

#SBATCH --job-name=dd-sequencing-mdd-python
#SBATCH --output=/home1/%u/compact-dd-suite-results/salidas/python/salida_sequencing_mdd_python.txt
#SBATCH --partition=gpus
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=5
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
LOG_TIMEOUT="$HOME/compact-dd-suite-results/timeout_log/python/timeout_log_sequencing_mdd_python_$DATE.txt"
OUTPUT_FILE="$HOME/compact-dd-suite-results/results/python/results_sequencing_mdd_python_$DATE.csv"
MAX_PARALLEL=5      # Must equal --cpus-per-task
TIMEOUT_WIDTH=5m    # Restricted / Relax (same as submit_python.sh)
TIMEOUT_EXACT=60m   # Exact (same as submit_exact_python.sh)
pids=()
metadata=()

problem="Sequencing"
objective="Min"
TYPES=("Restricted" "RelaxPriority" "RelaxGrouping")
RUN_EXACT=true      # set to false to skip the exact MDD
MODES=("Reduce" "NoReduce")
WIDTHS=(500 1000 2000 5000 10000 20000)

wait_if_full() {
    while (( ${#pids[@]} >= MAX_PARALLEL )); do
        for i in "${!pids[@]}"; do
            if ! kill -0 "${pids[$i]}" 2>/dev/null; then
                wait "${pids[$i]}"
                if [ $? -eq 124 ]; then
                    IFS="|" read -r _pid _file _type _mode _width <<< "${metadata[$i]}"
                    echo "$(date '+%F %T') ❌ Timeout: $_file | $_type | $_mode | $_width" >> "$LOG_TIMEOUT"
                fi
                unset "pids[$i]"
                unset "metadata[$i]"
            fi
        done
        sleep 1
    done
}

# run <timeout> <file> <type> <mode> <width|no-width>
run() {
    local max_timeout="$1" file="$2" type="$3" mode="$4" width="$5"
    local args=("$file" -$problem -$type -$objective -Output_"$OUTPUT_FILE")
    [ "$mode" == "Reduce" ] && args+=(-Reduce)
    [ "$width" != "no-width" ] && args+=(-Width_"$width")

    echo "==== $file | $type | $mode | $width ===="
    timeout "$max_timeout" python main.py "${args[@]}" &

    pid=$!
    pids+=($pid)
    metadata+=("$pid|$file|$type|$mode|$width")
    wait_if_full
}

mapfile -t FILES < <(ls "$HOME/compact-dd-suite/DataInstances/$problem/Standard"/*.txt | sort -V)

for file in "${FILES[@]}"; do
    for type in "${TYPES[@]}"; do
        for mode in "${MODES[@]}"; do
            for width in "${WIDTHS[@]}"; do
                run "$TIMEOUT_WIDTH" "$file" "$type" "$mode" "$width"
            done
        done
    done
done

# Exact last so the long runs do not block the width grid
if [ "$RUN_EXACT" = true ]; then
    for file in "${FILES[@]}"; do
        for mode in "${MODES[@]}"; do
            run "$TIMEOUT_EXACT" "$file" "Exact" "$mode" "no-width"
        done
    done
fi

# Wait for the last processes
for i in "${!pids[@]}"; do
    wait "${pids[$i]}"
    if [ $? -eq 124 ]; then
        IFS="|" read -r _pid _file _type _mode _width <<< "${metadata[$i]}"
        echo "$(date '+%F %T') ❌ Timeout: $_file | $_type | $_mode | $_width" >> "$LOG_TIMEOUT"
    fi
done

echo "✅ Finished. Results in: $OUTPUT_FILE"
