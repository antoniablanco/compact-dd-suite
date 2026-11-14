import os
import sys
import io
import math
import time
from pathlib import Path
from typing import Optional
from unittest.mock import patch

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from Examples.GuiStructure import ProblemClass
from Examples.GuiHandler import to_string_problem_class, write_statistics
from Examples.KnapsackInstance.KnapsackInstance import KnapsackStructure
from Examples.KnapsackInstance.KnapsackProblem import KnapsackProblem
from Examples.SetCoverInstance.SetCoverInstance import SetCoverStructure
from Examples.SetCoverInstance.SetCoverProblem import SetCoverProblem
from Examples.IndependentSetInstance.IndependentSetInstance import IndependentSetStructure
from Examples.IndependentSetInstance.IndependentSetProblem import IndependentSetProblem
from Examples.SOCKnapsack.SOCKnapsackInstance import SOCKnapsackInstance
from Examples.SOCKnapsack.SOCKnapsackProblem import SOCKnapsackProblem
from Examples.SequencingInstance.SequencingInstance import SequencingStructure
from Examples.SequencingInstance.SequencingProblem import SequencingProblem

# Widths and node counts of the lower layers that were not built (see compute_layer_widths).
NOT_COMPUTED: str = "na"

HEADERS: str = "File_name,Problem type,Variables number,Sort,K Default,K Opt,Nodes Default,Nodes Opt,Forward Widths,Backward Widths,Time"


def create_problem(problem_class: ProblemClass, file_path: str, sort: bool) -> 'AbstractProblem':
    '''
    Reads the instance and creates the problem, as run_dd_code does.

    Parameters:
    - problem_class: Problem of the instance.
    - file_path: Path of the instance file.
    - sort: Whether the variables are sorted.

    Returns:
    - AbstractProblem: Problem of the instance.
    '''
    if problem_class == ProblemClass.SET_COVER:
        return SetCoverProblem(SetCoverStructure(file_path), sort=sort)
    elif problem_class == ProblemClass.INDEPENDENT_SET:
        return IndependentSetProblem(IndependentSetStructure(file_path), sort=sort)
    elif problem_class == ProblemClass.KNAPSACK:
        return KnapsackProblem(KnapsackStructure(file_path), sort=sort)
    elif problem_class == ProblemClass.SOC_KNAPSACK:
        return SOCKnapsackProblem(SOCKnapsackInstance(file_path), 0, sort=sort)
    elif problem_class == ProblemClass.SEQUENCING:
        return SequencingProblem(SequencingStructure(file_path), sort=sort)
    raise ValueError("A valid problem class was not specified.")


def expand_layer(problem: 'AbstractProblem', states: list, variable_id: int,
                 transition_function, scratch_state: list) -> list:
    '''
    States of the next layer, as ExactSemiDDBuilder._create_new_layer would create them (same
    transition and same state key), but without building nodes or arcs: only the widths are needed,
    so only one layer is kept in memory.

    Parameters:
    - problem: Problem of the instance.
    - states: States of the previous layer.
    - variable_id: Position of the variable in the ordering.
    - transition_function: Forward or backward transition function of the problem.
    - scratch_state: One-element list the transition function writes the new state into.

    Returns:
    - list: Distinct states of the new layer.
    '''
    variable_index: int = problem.name_to_index[problem.ordered_variables[variable_id]]
    domain: list[int] = problem.variables_domain[problem.ordered_variables[variable_id]]
    get_state_as_string = problem.get_state_as_string
    new_states: dict = {}

    for previous_state in states:
        for variable_value in domain:
            if not transition_function(previous_state, variable_index, variable_value, scratch_state):
                continue
            state_as_string: str = get_state_as_string(scratch_state[0])
            if state_as_string not in new_states:
                new_states[state_as_string] = problem.get_state_copy(scratch_state[0])

    return list(new_states.values())


def compute_layer_widths(problem: 'AbstractProblem') -> tuple[list[int], list[Optional[int]]]:
    '''
    Widths of the exact upper layers 0..N-1 and of the exact lower layers N..1. A layer does not
    depend on the connection layer (it only depends on the previous layers of its own side), so
    these widths give the size of the sMDD for every k.
    The lower side stops as soon as its layers k..N alone have more nodes than the best sMDD found
    so far: every k' <= k has at least those nodes, so none of them can be k*. The layers below
    the stop are left as None.

    Parameters:
    - problem: Problem of the instance.

    Returns:
    - tuple[list[int], list[Optional[int]]]: forward[j] = width of upper layer j (j = 0..N-1) and
      backward[j] = width of lower layer j (j = 1..N, None if not built; backward[0] is never used).
    '''
    number_of_variables: int = len(problem.ordered_variables)

    states: list = [problem.initial_state]
    scratch_state: list = [problem.get_state_copy(problem.initial_state)]
    forward: list[int] = [1]
    for variable_id in range(number_of_variables - 1):
        states = expand_layer(problem, states, variable_id, problem.transition_function, scratch_state)
        forward.append(len(states))

    initial_backward_state: 'State' = problem.get_initial_backward_state()
    states = [initial_backward_state]
    scratch_state = [problem.get_state_copy(initial_backward_state)]
    backward: list[Optional[int]] = [None] * (number_of_variables + 1)
    backward[number_of_variables] = 1
    upper_nodes: int = sum(forward)
    lower_nodes: int = 1
    best_nodes: int = upper_nodes + lower_nodes  # k = N
    for variable_id in range(number_of_variables - 1, 0, -1):
        states = expand_layer(problem, states, variable_id, problem.backward_transition_function, scratch_state)
        backward[variable_id] = len(states)
        upper_nodes -= forward[variable_id]
        lower_nodes += len(states)
        best_nodes = min(best_nodes, upper_nodes + lower_nodes)
        if lower_nodes > best_nodes:
            break

    return forward, backward


def nodes_per_connect_layer(forward: list[int], backward: list[Optional[int]]) -> list[Optional[int]]:
    '''
    Number of nodes of the sMDD (before pruning and reduction) for every connection layer:
    nodes(k) = sum(forward[0..k-1]) + sum(backward[k..N]), or None if a lower layer >= k was not built.

    Parameters:
    - forward: Widths of the upper layers 0..N-1.
    - backward: Widths of the lower layers 0..N (index 0 unused, None if not built).

    Returns:
    - list[Optional[int]]: nodes[k] for k = 0..N (index 0 unused).
    '''
    number_of_variables: int = len(forward)
    nodes: list[Optional[int]] = [None] * (number_of_variables + 1)
    upper_nodes: int = sum(forward)
    lower_nodes: int = 0

    for k in range(number_of_variables, 0, -1):
        if backward[k] is None:
            break
        lower_nodes += backward[k]
        nodes[k] = upper_nodes + lower_nodes
        upper_nodes -= forward[k - 1]

    return nodes


def optimal_connect_layer(forward: list[int], backward: list[int], nodes: list[int]) -> int:
    '''
    Connection layer with the fewest nodes. Ties are broken by the size of the connection
    (forward[k-1] * backward[k], the pairs checked by the connection function) and then by the
    smallest k.

    Parameters:
    - forward: Widths of the upper layers 0..N-1.
    - backward: Widths of the lower layers 0..N (index 0 unused).
    - nodes: Number of nodes for every connection layer (index 0 unused, None if not computed).

    Returns:
    - int: Optimal connection layer, in [1, N].
    '''
    return min((k for k in range(1, len(nodes)) if nodes[k] is not None),
               key=lambda k: (nodes[k], forward[k - 1] * backward[k], k))


def main(argv):
    if len(argv) < 2:
        print("\nUsage: program_name [filename] [flags] \n")
        print("\tComputes the connection layer k* that minimizes the nodes of the exact sMDD")
        print("\t(before pruning and reduction), to pass it afterwards with -ConnectLayer_<k*>.\n")
        print("\tflags:")
        print("\t\t-SetCover | -Knapsack | -IndependentSet | -SOCKnapsack | -Sequencing = Problem class")
        print("\t\t-NoSort = Disable variable sorting")
        print("\t\t-Output_ = Output file path")
        print("\n\n")
        return 1

    source_directory: str = os.path.dirname(os.path.abspath(__file__))
    filename: str = argv[1]
    output_name: str = ""
    problem_class: ProblemClass = ProblemClass.NONE
    sort_flag: bool = True

    for arg in argv[2:]:
        if arg == "-SetCover":
            problem_class = ProblemClass.SET_COVER
        elif arg == "-Knapsack":
            problem_class = ProblemClass.KNAPSACK
        elif arg == "-IndependentSet":
            problem_class = ProblemClass.INDEPENDENT_SET
        elif arg == "-SOCKnapsack":
            problem_class = ProblemClass.SOC_KNAPSACK
        elif arg == "-Sequencing":
            problem_class = ProblemClass.SEQUENCING
        elif arg == "-NoSort":
            sort_flag = False
        elif arg.startswith("-Output_"):
            output_name = arg[8:]

    if problem_class == ProblemClass.NONE:
        print("Error: A valid problem class was not specified.")
        sys.exit(1)

    file_path: str = filename if os.path.isabs(filename) else f"{source_directory}/{filename}"
    output_path: str = ""
    if output_name != "":
        output_path = output_name if os.path.isabs(output_name) else os.path.join(source_directory, output_name)

    start_time: float = time.time()
    with patch('sys.stdout', new_callable=io.StringIO):
        problem: 'AbstractProblem' = create_problem(problem_class, file_path, sort_flag)
    forward, backward = compute_layer_widths(problem)
    nodes: list[int] = nodes_per_connect_layer(forward, backward)
    k_opt: int = optimal_connect_layer(forward, backward, nodes)
    k_default: int = math.ceil(len(forward) / 2)
    elapsed_time: float = round(time.time() - start_time, 4)

    print(f"Instance: {Path(file_path).name}")
    print(f"Forward widths:  {forward}")
    print(f"Backward widths: {[NOT_COMPUTED if b is None else b for b in backward[1:]]}")
    print(f"Nodes per k:     {[NOT_COMPUTED if n is None else n for n in nodes[1:]]}")
    print(f"K default: {k_default} ({NOT_COMPUTED if nodes[k_default] is None else nodes[k_default]} nodes) | "
          f"K opt: {k_opt} ({nodes[k_opt]} nodes)")

    if output_path != "":
        statistics: str = (
            f'{Path(file_path).name},'
            f'{to_string_problem_class(problem_class)},'
            f'{len(forward)},'
            f'{sort_flag},'
            f'{k_default},'
            f'{k_opt},'
            f'{NOT_COMPUTED if nodes[k_default] is None else nodes[k_default]},'
            f'{nodes[k_opt]},'
            f'{";".join(map(str, forward))},'
            f'{";".join(NOT_COMPUTED if b is None else str(b) for b in backward[1:])},'
            f'{elapsed_time}\n'
        )
        write_statistics(output_path, statistics, HEADERS)

    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))
