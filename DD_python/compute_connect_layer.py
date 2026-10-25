import os
import sys
import io
import math
import time
from pathlib import Path
from unittest.mock import patch

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from SourceCode.DDSemiBuilder.ExactSemiDDBuilder.ExactSemiDDBuilder import ExactSemiDDBuilder
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


def compute_layer_widths(problem: 'AbstractProblem') -> tuple[list[int], list[int]]:
    '''
    Builds the exact upper graph down to layer N-1 and the exact lower graph up to layer 1, and
    returns their widths. A layer does not depend on the connection layer (it only depends on the
    previous layers of its own side), so these widths give the size of the sMDD for every k.

    Parameters:
    - problem: Problem of the instance.

    Returns:
    - tuple[list[int], list[int]]: forward[j] = width of upper layer j (j = 0..N-1) and
      backward[j] = width of lower layer j (j = 1..N; backward[0] is 0, it is never used).
    '''
    number_of_variables: int = len(problem.ordered_variables)

    upper_builder: ExactSemiDDBuilder = ExactSemiDDBuilder(problem)
    upper_builder.connect_layer = number_of_variables
    upper_builder._build_upper_graph(False)
    forward: list[int] = [len(layer) for layer in upper_builder._upper_graph.structure]
    upper_builder = None

    lower_builder: ExactSemiDDBuilder = ExactSemiDDBuilder(problem)
    lower_builder.connect_layer = 1
    lower_builder._build_lower_graph(False)
    backward: list[int] = [0] + [len(layer) for layer in reversed(lower_builder._lower_graph.structure)]

    return forward, backward


def nodes_per_connect_layer(forward: list[int], backward: list[int]) -> list[int]:
    '''
    Number of nodes of the sMDD (before pruning and reduction) for every connection layer:
    nodes(k) = sum(forward[0..k-1]) + sum(backward[k..N]).

    Parameters:
    - forward: Widths of the upper layers 0..N-1.
    - backward: Widths of the lower layers 0..N (index 0 unused).

    Returns:
    - list[int]: nodes[k] for k = 0..N (index 0 unused).
    '''
    number_of_variables: int = len(forward)
    nodes: list[int] = [0] * (number_of_variables + 1)
    upper_nodes: int = 0
    lower_nodes: int = sum(backward[1:])

    for k in range(1, number_of_variables + 1):
        upper_nodes += forward[k - 1]
        nodes[k] = upper_nodes + lower_nodes
        lower_nodes -= backward[k]

    return nodes


def optimal_connect_layer(forward: list[int], backward: list[int], nodes: list[int]) -> int:
    '''
    Connection layer with the fewest nodes. Ties are broken by the size of the connection
    (forward[k-1] * backward[k], the pairs checked by the connection function) and then by the
    smallest k.

    Parameters:
    - forward: Widths of the upper layers 0..N-1.
    - backward: Widths of the lower layers 0..N (index 0 unused).
    - nodes: Number of nodes for every connection layer (index 0 unused).

    Returns:
    - int: Optimal connection layer, in [1, N].
    '''
    return min(range(1, len(nodes)), key=lambda k: (nodes[k], forward[k - 1] * backward[k], k))


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
    print(f"Backward widths: {backward[1:]}")
    print(f"Nodes per k:     {nodes[1:]}")
    print(f"K default: {k_default} ({nodes[k_default]} nodes) | K opt: {k_opt} ({nodes[k_opt]} nodes)")

    if output_path != "":
        statistics: str = (
            f'{Path(file_path).name},'
            f'{to_string_problem_class(problem_class)},'
            f'{len(forward)},'
            f'{sort_flag},'
            f'{k_default},'
            f'{k_opt},'
            f'{nodes[k_default]},'
            f'{nodes[k_opt]},'
            f'{";".join(map(str, forward))},'
            f'{";".join(map(str, backward[1:]))},'
            f'{elapsed_time}\n'
        )
        write_statistics(output_path, statistics, HEADERS)

    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))
