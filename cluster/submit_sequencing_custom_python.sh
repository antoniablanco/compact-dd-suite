#!/bin/bash

# MDD and sMDD (default connection layer ceil(N/2)) on the Custom Sequencing instances
# (DataInstances/Sequencing/Custom, n = 3..20), with the same combinations as submit_python.sh:
# Exact, Restricted, RelaxPriority and RelaxGrouping (MDD only, there is no grouping sMDD), with and
# without -Reduce, and widths 500..20000. No exact sMDD of the Standard instances (n >= 16) finished,
# so this checks whether the smaller Custom ones do.
# The instances go from the smallest n to the largest, and for each one the MDD and the sMDD run
# back to back for every combination, so the comparison is complete for every one that finishes.
# Same resources as submit_python.sh (5m per process, 5 in parallel, default memory).
# MDD and sMDD go to separate CSVs, as in the rest of the runs (data/python/original vs semi).

#SBATCH --job-name=dd-sequencing-custom-python
#SBATCH --output=/home1/%u/compact-dd-suite-results/salidas/python/salida_sequencing_custom_python.txt
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
INSTANCE_DIR="$HOME/compact-dd-suite/DataInstances/Sequencing/Custom"
LOG_TIMEOUT="$HOME/compact-dd-suite-results/timeout_log/python/timeout_log_sequencing_custom_python_$DATE.txt"
OUTPUT_MDD="$HOME/compact-dd-suite-results/results/python/results_sequencing_custom_mdd_python_$DATE.csv"
OUTPUT_SEMI="$HOME/compact-dd-suite-results/results/python/results_sequencing_custom_semi_python_$DATE.csv"
MAX_PARALLEL=5      # Must equal --cpus-per-task
MAX_TIMEOUT=5m      # Same as submit_python.sh, so the results compare with its runs
pids=()
metadata=()

TYPES=("Exact" "Restricted" "RelaxPriority" "RelaxGrouping")
MODES=("Reduce" "NoReduce")
WIDTHS=(500 1000 2000 5000 10000 20000)

# Every failure is logged, not only the timeouts: an out-of-memory kill exits with 137 (SIGKILL)
# and would otherwise only show up as "Killed" in salidas/.
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

# launch <description> <args of main.py...>
launch() {
    local description="$1"
    shift
    echo "==== $description ===="
    timeout "$MAX_TIMEOUT" python main.py "$@" &

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

mapfile -t FILES < <(ls "$INSTANCE_DIR"/*.txt | sort -V)
echo "######## ${#FILES[@]} instances | MDD -> $OUTPUT_MDD | sMDD -> $OUTPUT_SEMI ########"

# launch_pair <description> <type> <args of main.py...>: the MDD and, except for RelaxGrouping, the sMDD.
launch_pair() {
    local description="$1" type="$2"
    shift 2
    launch "$description" "$@" -Output_"$OUTPUT_MDD"
    if [ "$type" != "RelaxGrouping" ]; then
        launch "${description/ | / (semi) | }" "$@" -Semi -Output_"$OUTPUT_SEMI"
    fi
}

for file in "${FILES[@]}"; do
    for type in "${TYPES[@]}"; do
        for mode in "${MODES[@]}"; do
            args=("$file" -Sequencing -$type -Min)
            [ "$mode" == "Reduce" ] && args+=(-Reduce)

            if [ "$type" == "Exact" ]; then
                launch_pair "$type | $file | $mode" "$type" "${args[@]}"
            else
                for width in "${WIDTHS[@]}"; do
                    launch_pair "$type | $file | $mode | $width" "$type" "${args[@]}" -Width_"$width"
                done
            fi
        done
    done
done
wait_if_full 0
dedupe_header "$OUTPUT_MDD"
dedupe_header "$OUTPUT_SEMI"

echo "✅ Finished. MDD: $OUTPUT_MDD | sMDD: $OUTPUT_SEMI"
