#!/bin/bash

# submit_connect_layer_python.sh for the Custom Sequencing instances (DataInstances/Sequencing/Custom,
# n = 3..20), which were added after the run of 25/10/2026.
# 1) For every instance, compute_connect_layer.py computes k*, the connection layer that minimizes
#    the nodes of the exact sMDD (before pruning and reduction).
# 2) The sMDD (Exact, Restricted, RelaxPriority) is run with -ConnectLayer_<k*>. Restricted and
#    relaxed use the k* of the exact sMDD. Instances without k* (timeout in step 1) are skipped.
# Step 2 uses 5m for every type, Exact included, as submit_sequencing_custom_python.sh, so its rows
# compare with results_sequencing_custom_{mdd,semi}_python_31_10_2026_17-44-03.csv.
# Locally, step 1 takes ~2s for n = 15 and ~3.5m / 1.9G for n = 20.
# The outputs use other names so the data_visualization scripts, which take the newest
# connect_layers_python_* / results_python_semi_kopt_*, do not pick this partial run by mistake.

#SBATCH --job-name=dd-connect-layer-sequencing-custom-python
#SBATCH --output=/home1/%u/compact-dd-suite-results/salidas/python/salida_connect_layer_sequencing_custom_python.txt
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
LOG_TIMEOUT="$HOME/compact-dd-suite-results/timeout_log/python/timeout_log_connect_layer_sequencing_custom_python_$DATE.txt"
CONNECT_LAYERS_FILE="$HOME/compact-dd-suite-results/results/python/connect_layers_sequencing_custom_python_$DATE.csv"
OUTPUT_FILE="$HOME/compact-dd-suite-results/results/python/results_sequencing_custom_kopt_python_$DATE.csv"
MAX_PARALLEL=5      # Must equal --cpus-per-task
TIMEOUT_K=60m       # Step 1 (same as submit_connect_layer_python.sh)
TIMEOUT_DD=5m       # Step 2, every type (same as submit_sequencing_custom_python.sh)
pids=()
metadata=()

TYPES=("Exact" "Restricted" "RelaxPriority") # There is no grouping sMDD
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

# Prints the k* of the instance file name given, or nothing if it was not computed.
get_connect_layer() {
    [ -f "$CONNECT_LAYERS_FILE" ] || return
    awk -F, -v f="$1" 'NR == 1 { for (i = 1; i <= NF; i++) if ($i == "K Opt") c = i; next }
                       $1 == f { print $c; exit }' "$CONNECT_LAYERS_FILE"
}

mapfile -t FILES < <(ls "$INSTANCE_DIR"/*.txt | sort -V)

# ── Step 1: k* per instance ──────────────────────────────────────────────────
echo "######## Step 1: connection layer k* (${#FILES[@]} instances) -> $CONNECT_LAYERS_FILE ########"
for file in "${FILES[@]}"; do
    launch "$TIMEOUT_K" "k* | $file" compute_connect_layer.py "$file" -Sequencing -Output_"$CONNECT_LAYERS_FILE"
done
wait_if_full 0
dedupe_header "$CONNECT_LAYERS_FILE"

if [ ! -s "$CONNECT_LAYERS_FILE" ]; then
    echo "❌ No connection layer was computed"
    exit 1
fi

# ── Step 2: sMDD with -ConnectLayer_<k*> ─────────────────────────────────────
echo "######## Step 2: sMDD with k* -> $OUTPUT_FILE ########"
for file in "${FILES[@]}"; do
    k=$(get_connect_layer "$(basename "$file")")
    if [ -z "$k" ]; then
        echo "⚠️  $file has no k*, skipped"
        continue
    fi

    for type in "${TYPES[@]}"; do
        for mode in "${MODES[@]}"; do
            args=(main.py "$file" -Sequencing -$type -Semi -ConnectLayer_"$k" -Min -Output_"$OUTPUT_FILE")
            [ "$mode" == "Reduce" ] && args+=(-Reduce)

            if [ "$type" == "Exact" ]; then
                launch "$TIMEOUT_DD" "$file | k=$k | $type | $mode" "${args[@]}"
            else
                for width in "${WIDTHS[@]}"; do
                    launch "$TIMEOUT_DD" "$file | k=$k | $type | $mode | $width" "${args[@]}" -Width_"$width"
                done
            fi
        done
    done
done
wait_if_full 0
dedupe_header "$OUTPUT_FILE"

echo "✅ Finished. k*: $CONNECT_LAYERS_FILE | Results: $OUTPUT_FILE"
