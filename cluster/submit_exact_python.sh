#!/bin/bash

#SBATCH --job-name=dd-exact-python
#SBATCH --output=/home1/%u/compact-dd-suite-results/salidas/python/salida_semi_exact_python.txt
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

SEMI="-Semi" # "-Semi" builds the sMDD; set it to "" for the standard MDD
LOG_TIMEOUT="$HOME/compact-dd-suite-results/timeout_log/python/timeout_log_exact_python${SEMI:+_semi}_$(date '+%d_%m_%Y_%H-%M-%S').txt"
OUTPUT_FILE="$HOME/compact-dd-suite-results/results/python/results_semi_exact_python${SEMI:+_semi}_$(date '+%d_%m_%Y_%H-%M-%S').csv"
MAX_PARALLEL=5
MAX_TIMEOUT=60m
pids=()
metadata=()

# (Problem, Objective, instance directory/ies)
declare -A OBJECTIVE=(
    [Knapsack]="Max"
    [IndependentSet]="Max"
    [SetCover]="Min"
    [SOCKnapsack]="Max"
    [Sequencing]="Min"
)

declare -A DIRECTORIOS=(
    [Knapsack]="Standard"
    [IndependentSet]="Standard"
    [SetCover]="Standard"
    [SOCKnapsack]="Standard"
    [Sequencing]="Standard"
)

PROBLEMS=("Knapsack" "IndependentSet" "SetCover" "SOCKnapsack" "Sequencing")
MODES=("Reduce" "NoReduce")

wait_if_full() {
    while (( ${#pids[@]} >= MAX_PARALLEL )); do
        for i in "${!pids[@]}"; do
            if ! kill -0 "${pids[$i]}" 2>/dev/null; then
                wait "${pids[$i]}"
                if [ $? -eq 124 ]; then
                    IFS="|" read -r _pid _file _mode <<< "${metadata[$i]}"
                    echo "$(date '+%F %T') ❌ Timeout: $_file | Exact | $_mode" >> "$LOG_TIMEOUT"
                fi
                unset "pids[$i]"
                unset "metadata[$i]"
            fi
        done
        sleep 1
    done
}

for problem in "${PROBLEMS[@]}"; do
    objective="${OBJECTIVE[$problem]}"
    read -ra dirs <<< "${DIRECTORIOS[$problem]}"

    for subdir in "${dirs[@]}"; do
        instance_dir="$HOME/compact-dd-suite/DataInstances/$problem/$subdir"
        [ -d "$instance_dir" ] || continue
        mapfile -t FILES < <(ls "$instance_dir"/*.txt 2>/dev/null | sort -V)

        for file_path in "${FILES[@]}"; do
            [ -f "$file_path" ] || continue

            for mode in "${MODES[@]}"; do
                echo "==== $file_path | Exact${SEMI:+ (semi)} | $mode | $objective ===="

                if [ "$mode" == "Reduce" ]; then
                    timeout "$MAX_TIMEOUT" python main.py "$file_path" \
                        -$problem -Exact $SEMI -Reduce -$objective \
                        -Output_"$OUTPUT_FILE" &
                else
                    timeout "$MAX_TIMEOUT" python main.py "$file_path" \
                        -$problem -Exact $SEMI -$objective \
                        -Output_"$OUTPUT_FILE" &
                fi

                pid=$!
                pids+=($pid)
                metadata+=("$pid|$file_path|$mode")
                wait_if_full
            done
        done
    done
done

# Wait for the last processes
for i in "${!pids[@]}"; do
    wait "${pids[$i]}"
    if [ $? -eq 124 ]; then
        IFS="|" read -r _pid _file _mode <<< "${metadata[$i]}"
        echo "$(date '+%F %T') ❌ Timeout: $_file | Exact | $_mode" >> "$LOG_TIMEOUT"
    fi
done

echo "✅ Finished. Results in: $OUTPUT_FILE"
