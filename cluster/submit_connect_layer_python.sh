#!/bin/bash

# Cluster test of the sMDD with the precomputed connection layer k*.
# 1) For every instance, compute_connect_layer.py computes k*, the connection layer that minimizes
#    the nodes of the exact sMDD (before pruning and reduction).
# 2) The sMDD (Exact, Restricted, RelaxPriority) is run with -ConnectLayer_<k*>. Restricted and
#    relaxed use the k* of the exact sMDD. Instances without k* (timeout in step 1) are skipped.

#SBATCH --job-name=dd-connect-layer-python
#SBATCH --output=/home1/%u/compact-dd-suite-results/salidas/python/salida_connect_layer_python.txt
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
LOG_TIMEOUT="$HOME/compact-dd-suite-results/timeout_log/python/timeout_log_connect_layer_python_$DATE.txt"
CONNECT_LAYERS_FILE="$HOME/compact-dd-suite-results/results/python/connect_layers_python_$DATE.csv"
OUTPUT_FILE="$HOME/compact-dd-suite-results/results/python/results_python_semi_kopt_$DATE.csv"
MAX_PARALLEL=5      # Must equal --cpus-per-task
TIMEOUT_K=60m       # Step 1: builds a full forward and a full backward exact DD
TIMEOUT_EXACT=60m   # Step 2, Exact (same as submit_exact_python.sh)
TIMEOUT_WIDTH=5m    # Step 2, Restricted / RelaxPriority (same as submit_python.sh)
pids=()
metadata=()

declare -A OBJECTIVE=(
    [Knapsack]="Max"
    [IndependentSet]="Max"
    [SetCover]="Min"
    [SOCKnapsack]="Max"
    [Sequencing]="Min"
)

PROBLEMS=("Knapsack" "IndependentSet" "SetCover" "SOCKnapsack" "Sequencing")
TYPES=("Exact" "Restricted" "RelaxPriority") # There is no grouping sMDD
MODES=("Reduce" "NoReduce")
WIDTHS=(500 1000 2000 5000 10000 20000)

wait_if_full() {
    local max_running="$1"
    while (( ${#pids[@]} > max_running )); do
        for i in "${!pids[@]}"; do
            if ! kill -0 "${pids[$i]}" 2>/dev/null; then
                wait "${pids[$i]}"
                if [ $? -eq 124 ]; then
                    echo "$(date '+%F %T') ❌ Timeout: ${metadata[$i]#*|}" >> "$LOG_TIMEOUT"
                fi
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
    awk -F, -v f="$1" 'NR == 1 { for (i = 1; i <= NF; i++) if ($i == "K Opt") c = i; next }
                       $1 == f { print $c; exit }' "$CONNECT_LAYERS_FILE"
}

# ── Step 1: k* per instance ──────────────────────────────────────────────────
echo "######## Step 1: connection layer k* -> $CONNECT_LAYERS_FILE ########"
for problem in "${PROBLEMS[@]}"; do
    mapfile -t FILES < <(ls "$HOME/compact-dd-suite/DataInstances/$problem/Standard"/*.txt | sort -V)
    for file in "${FILES[@]}"; do
        launch "$TIMEOUT_K" "k* | $file" compute_connect_layer.py "$file" -$problem -Output_"$CONNECT_LAYERS_FILE"
    done
done
wait_if_full 0
dedupe_header "$CONNECT_LAYERS_FILE"

if [ ! -s "$CONNECT_LAYERS_FILE" ]; then
    echo "❌ No connection layer was computed"
    exit 1
fi

# ── Step 2: sMDD with -ConnectLayer_<k*> ─────────────────────────────────────
echo "######## Step 2: sMDD with k* -> $OUTPUT_FILE ########"
for problem in "${PROBLEMS[@]}"; do
    objective="${OBJECTIVE[$problem]}"
    mapfile -t FILES < <(ls "$HOME/compact-dd-suite/DataInstances/$problem/Standard"/*.txt | sort -V)

    for file in "${FILES[@]}"; do
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
done
wait_if_full 0
dedupe_header "$OUTPUT_FILE"

echo "✅ Finished. k*: $CONNECT_LAYERS_FILE | Results: $OUTPUT_FILE"
