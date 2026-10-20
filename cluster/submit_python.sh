#!/bin/bash

# Job name
#SBATCH --job-name=dd-batch-python
#SBATCH --output=/home1/%u/dd-suite-results/salidas/python/salida_semi_python.txt
#SBATCH --partition=gpus
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=5
#SBATCH --mail-user=antonia.blanco@uc.cl
#SBATCH --mail-type=ALL

# Activate the conda environment
source ~/.bashrc
conda activate py3.12.9 || { echo "❌ Failed to activate the conda env"; exit 1; }

echo "Current working directory at start:"
pwd

# Create the folders if they do not exist
mkdir -p "$HOME/dd-suite-results/results/python"
mkdir -p "$HOME/dd-suite-results/timeout_log/python"

cd "$HOME/dd-suite-dev/DD_python" || { echo "❌ Directory not found"; exit 1; }

echo "Changed to directory:"
pwd
sleep 1


LOG_TIMEOUT="$HOME/dd-suite-results/timeout_log/python/timeout_log_python_$(date '+%d_%m_%Y_%H-%M-%S').txt"
MAX_PARALLEL=5  # Maximum number of parallel processes, must equal --cpus-per-task
MAX_TIMEOUT=5m # Maximum wait time per process (s: seconds, m: minutes, h: hours)
pids=()
metadata=()

PROBLEMS=("Knapsack" "IndependentSet" "SetCover" "SOCKnapsack" "Sequencing")
TYPES=("Exact" "Restricted" "RelaxPriority" "RelaxGrouping")
SEMI="-Semi" # "-Semi" builds the sMDD; set it to "" for the standard MDD
if [[ -n "$SEMI" ]]; then # There is no grouping sMDD
    _types=()
    for t in "${TYPES[@]}"; do [[ "$t" != "RelaxGrouping" ]] && _types+=("$t"); done
    TYPES=("${_types[@]}")
fi
MODES=("Reduce" "NoReduce")
WIDTHS=(500 1000 2000 5000 10000 20000)
OUTPUT_FILE="$HOME/dd-suite-results/results/python/results_python_semi${SEMI:+_semi}_$(date '+%d_%m_%Y_%H-%M-%S').csv"


for problem in "${PROBLEMS[@]}"; do
    case "$problem" in # Assign the objective according to the problem
        SetCover|Sequencing)
            objective="Min"
            ;;
        Knapsack|IndependentSet|SOCKnapsack)
            objective="Max"
            ;;
    esac
    mapfile -t FILES < <(ls $HOME/dd-suite-dev/DataInstances/$problem/Standard/*.txt | sort -V) # Load the files and sort them in order natural
    for file_path in "${FILES[@]}"; do
        file="${file_path#../}"

        if [[ -z "$file" ]]; then
            echo "❌ Empty file — skipping this iteration"
            continue
        fi
        for type in "${TYPES[@]}"; do
            for mode in "${MODES[@]}"; do
                if [[ "$type" == "Restricted" || "$type" == "RelaxPriority" || "$type" == "RelaxGrouping" ]]; then # If it is Restricted or Relax, it is run with different widths
                    for width in "${WIDTHS[@]}"; do
                        echo "==== Running with file: $file | type: $type${SEMI:+ (semi)} | mode: $mode | width: $width | output: $OUTPUT_FILE ===="

                        if [ "$mode" == "Reduce" ]; then
                            timeout "$MAX_TIMEOUT" python main.py "$file" -$problem -$type $SEMI -Reduce -$objective -Width_"$width" -Output_"$OUTPUT_FILE" &
                        else
                            timeout "$MAX_TIMEOUT" python main.py "$file" -$problem -$type $SEMI -$objective -Width_"$width" -Output_"$OUTPUT_FILE" &
                        fi
                        sleep 1

                        pid=$!
                        pids+=($pid)
                        metadata+=("$pid|$file|$type|$mode|$width")

                        # Throttle the parallelism
                        while (( ${#pids[@]} >= MAX_PARALLEL )); do
                            for i in "${!pids[@]}"; do
                                if ! kill -0 "${pids[$i]}" 2>/dev/null; then
                                    wait "${pids[$i]}"
                                    status=$?
                                    if [ $status -eq 124 ]; then
                                        IFS="|" read -r _pid _file _type _mode _width <<< "${metadata[$i]}"
                                        echo "$(date '+%F %T') ❌ Timeout: $_file | $_type | $_mode | $_width | exit code: $status" >> "$LOG_TIMEOUT"
                                    fi
                                    unset "pids[$i]"
                                    unset "metadata[$i]"
                                fi
                            done
                            sleep 1
                        done
                    done
                else
                    # Run only once when there is no width
                    echo "==== Running with file: $file | type: $type${SEMI:+ (semi)} | mode: $mode | output: $OUTPUT_FILE ===="
                    if [ "$mode" == "Reduce" ]; then
                        timeout "$MAX_TIMEOUT" python main.py "$file" -$problem -$type $SEMI -Reduce -$objective -Output_"$OUTPUT_FILE" &
                    else
                        timeout "$MAX_TIMEOUT" python main.py "$file" -$problem -$type $SEMI -$objective -Output_"$OUTPUT_FILE" &
                    fi

                    sleep 1

                    pid=$!
                    pids+=($pid)
                    metadata+=("$pid|$file|$type|$mode|no-width")

                    # Throttle the parallelism
                    while (( ${#pids[@]} >= MAX_PARALLEL )); do
                        for i in "${!pids[@]}"; do
                            if ! kill -0 "${pids[$i]}" 2>/dev/null; then
                                wait "${pids[$i]}"
                                status=$?
                                if [ $status -eq 124 ]; then
                                    IFS="|" read -r _pid _file _type _mode _width <<< "${metadata[$i]}"
                                    echo "$(date '+%F %T') ❌ Timeout: $_file | $_type | $_mode | $_width | exit code: $status" >> "$LOG_TIMEOUT"
                                fi
                                unset "pids[$i]"
                                unset "metadata[$i]"
                            fi
                        done
                        sleep 1
                    done
                fi
            done
        done
    done
done

# Wait for the last processes
for i in "${!pids[@]}"; do  
    wait "${pids[$i]}"
    status=$?
    if [ $status -eq 124 ]; then
        IFS="|" read -r _pid _file _type _mode _width <<< "${metadata[$i]}"
        echo "$(date '+%F %T') ❌ Timeout: $_file | $_type | $_mode | $_width | exit code: $status" >> "$LOG_TIMEOUT"
    fi
done