#!/bin/bash
#SBATCH --job-name=soc-table2-python
#SBATCH --output=/home1/%u/dd-suite-results/salidas/python/salida_soc_table2_relax.txt
#SBATCH --partition=gpus
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=10
#SBATCH --mail-user=antonia.blanco@uc.cl
#SBATCH --mail-type=ALL

# Activate the conda environment
source ~/.bashrc
conda activate py3.12.9 || { echo "Error al activar conda env"; exit 1; }

echo "Working directory: $(pwd)"

# Create the result folders
mkdir -p "$HOME/dd-suite-results/results/python"
mkdir -p "$HOME/dd-suite-results/timeout_log/python"
mkdir -p "$HOME/dd-suite-results/salidas/python"

cd "$HOME/dd-suite-dev/DD_python" || { echo "DD_python directory not found"; exit 1; }
echo "Running from: $(pwd)"

TIMESTAMP=$(date '+%d_%m_%Y_%H-%M-%S')
LOG_TIMEOUT="$HOME/dd-suite-results/timeout_log/python/timeout_soc_table2_${TIMESTAMP}.txt"
RESULTS_DIR="$HOME/dd-suite-results/results/python"

MAX_PARALLEL=5    # Must match --cpus-per-task
MAX_TIMEOUT=90m   # OS backstop > Gurobi TimeLimit (1h, same as the paper) + margin for the DD build and the CSV write

# Load the 90 Standard SOCKnapsack instances, sorted
mapfile -t FILES < <(ls "$HOME/dd-suite-dev/DataInstances/SOCKnapsack/Standard"/*.txt | sort -V)
echo "Instances found: ${#FILES[@]}"

SEMI="-Semi" # "-Semi" builds the sMDD (RelaxPriority only); set it to "" for the standard MDD

# Paths relative to the source_directory of the Python mains (DD_python/)
# source_directory = $HOME/dd-suite-dev/DD_python => ../../dd-suite-results/...
OUTPUT_GUROBI="../../dd-suite-results/results/python/soc_gurobi_${TIMESTAMP}.csv"
OUTPUT_CUTS="../../dd-suite-results/results/python/soc_cuts${SEMI:+_semi}_${TIMESTAMP}.csv"

# Variant definition: "variant_name|script|flags|output_file"
# Relaxed DD with width 4000, same as the paper (Castro, Cire & Beck).
VARIANTS=(
    #"Gurobi|main_gurobi.py|-SOCKnapsack|${OUTPUT_GUROBI}"
    "B-Flow|main_cuts.py|-SOCKnapsack -FlowCuts -RelaxPriority $SEMI -Width_4000|${OUTPUT_CUTS}"
    "B-Flow+L|main_cuts.py|-SOCKnapsack -FlowCuts -CutStrengthening -RelaxPriority $SEMI -Width_4000|${OUTPUT_CUTS}"
    "B-Gen|main_cuts.py|-SOCKnapsack -JointFlowCuts -RelaxPriority $SEMI -Width_4000|${OUTPUT_CUTS}"
    "B-Gen+L|main_cuts.py|-SOCKnapsack -JointFlowCuts -CutStrengthening -RelaxPriority $SEMI -Width_4000|${OUTPUT_CUTS}"
    "B-Target|main_cuts.py|-SOCKnapsack -TargetCuts -RelaxPriority $SEMI -Width_4000|${OUTPUT_CUTS}"
    "B-Target+L|main_cuts.py|-SOCKnapsack -TargetCuts -CutStrengthening -RelaxPriority $SEMI -Width_4000|${OUTPUT_CUTS}"
)

# ---- Parallelism control ----
wait_for_slot() {
    local -n _pids=$1
    local -n _meta=$2
    while (( ${#_pids[@]} >= MAX_PARALLEL )); do
        for i in "${!_pids[@]}"; do
            if ! kill -0 "${_pids[$i]}" 2>/dev/null; then
                wait "${_pids[$i]}"
                local status=$?
                if [ $status -eq 124 ]; then
                    IFS="|" read -r _pid _file _var <<< "${_meta[$i]}"
                    echo "$(date '+%F %T') TIMEOUT: $_file | $_var" >> "$LOG_TIMEOUT"
                fi
                unset "_pids[$i]"
                unset "_meta[$i]"
            fi
        done
        sleep 1
    done
}

drain_pids() {
    local -n _pids=$1
    local -n _meta=$2
    for i in "${!_pids[@]}"; do
        wait "${_pids[$i]}"
        local status=$?
        if [ $status -eq 124 ]; then
            IFS="|" read -r _pid _file _var <<< "${_meta[$i]}"
            echo "$(date '+%F %T') TIMEOUT: $_file | $_var" >> "$LOG_TIMEOUT"
        fi
    done
}

# ---- Main loop: one variant at a time ----
for entry in "${VARIANTS[@]}"; do
    IFS="|" read -r VARIANT SCRIPT FLAGS OUTPUT_FILE <<< "$entry"

    echo ""
    echo "============================================================"
    echo "Variant : $VARIANT"
    echo "Script   : python $SCRIPT"
    echo "Flags    : $FLAGS"
    echo "Output   : $OUTPUT_FILE"
    echo "============================================================"

    pids=()
    metadata=()

    for file_path in "${FILES[@]}"; do
        name=$(basename "$file_path")

        echo "  -> $name | $VARIANT"

        # shellcheck disable=SC2086
        timeout "$MAX_TIMEOUT" python "$SCRIPT" "$file_path" $FLAGS -Output_"$OUTPUT_FILE" &

        pid=$!
        pids+=($pid)
        metadata+=("$pid|$name|$VARIANT")

        wait_for_slot pids metadata
    done

    drain_pids pids metadata
    echo "  Variant $VARIANT finished."
done

echo ""
echo "All experiments completed."
echo "Results in: ${RESULTS_DIR}/"
echo "  Gurobi : $OUTPUT_GUROBI"
echo "  Cuts   : $OUTPUT_CUTS"
