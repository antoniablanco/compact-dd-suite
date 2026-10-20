import os
import sys
import io
import unittest
from unittest.mock import patch
from types import SimpleNamespace

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, os.pardir))
sys.path.append(parent_dir)

from SourceCode.DD import DD
from SourceCode.GraphAlgorithms.ShortestLongestPath.ShortestLongestPath import ShortestLongestPath

from Examples.KnapsackInstance.KnapsackInstance import KnapsackStructure
from Examples.KnapsackInstance.KnapsackProblem import KnapsackProblem
from Examples.IndependentSetInstance.IndependentSetInstance import IndependentSetStructure
from Examples.IndependentSetInstance.IndependentSetProblem import IndependentSetProblem
from Examples.SetCoverInstance.SetCoverInstance import SetCoverStructure
from Examples.SetCoverInstance.SetCoverProblem import SetCoverProblem
from Examples.SOCKnapsack.SOCKnapsackInstance import SOCKnapsackInstance
from Examples.SOCKnapsack.SOCKnapsackProblem import SOCKnapsackProblem
from Examples.SequencingInstance.SequencingInstance import SequencingStructure
from Examples.SequencingInstance.SequencingProblem import SequencingProblem
from Examples.SequencingInstance.SequencingPathSolver import SequencingPathSolver

INSTANCES_DIR: str = os.path.join(parent_dir, "..", "DataInstances")
UNBOUNDED_WIDTH: int = 10 ** 6


def count_paths(graph: 'Graph') -> int:
    paths_to_node: dict[int, int] = {graph.structure[0][0].get_id(): 1}
    for layer in graph.structure[1:]:
        for node in layer:
            paths_to_node[node.get_id()] = sum(paths_to_node[arc.parent_node.get_id()] for arc in node.in_arcs)
    return paths_to_node[graph.structure[-1][0].get_id()]

class ProblemsSemiDDTest(unittest.TestCase):
    '''
    For every connection layer, the exact sMDD (reduced or not) must represent the same solutions
    as the MDD: same number of paths and same optimal value.
    '''

    def build_dd(self, problem: 'AbstractProblem', semi: bool, reduce: bool) -> DD:
        dd_instance: DD = DD(problem)
        with patch('sys.stdout', new_callable=io.StringIO):
            if semi:
                dd_instance.create_semi_decision_diagram()
            else:
                dd_instance.create_decision_diagram()
            if reduce:
                dd_instance.reduce_decision_diagram()
        return dd_instance

    def get_value_path_solution(self, dd_instance: DD, weights: list[int], objective: str) -> float:
        with patch('sys.stdout', new_callable=io.StringIO):
            shortest_longest_path_instance: ShortestLongestPath = ShortestLongestPath(dd_instance)
            shortest_longest_path_instance.set_parameters(weights, objective)
            return shortest_longest_path_instance.solve().value

    def assert_semi_dd_equals_mdd(self, problem: 'AbstractProblem', weights: list[int], objective: str) -> None:
        weights = problem.reorder_to_dd_order(weights)
        mdd: DD = self.build_dd(problem, semi=False, reduce=True)
        expected_paths: int = count_paths(mdd.get_decision_diagram())
        expected_value: float = self.get_value_path_solution(mdd, weights, objective)

        for connect_layer in range(1, len(problem.ordered_variables) + 1):
            problem.connect_layer = connect_layer
            for reduce in (False, True):
                with self.subTest(connect_layer=connect_layer, reduce=reduce):
                    dd_instance: DD = self.build_dd(problem, semi=True, reduce=reduce)
                    self.assertEqual(expected_paths, count_paths(dd_instance.get_decision_diagram()))
                    self.assertAlmostEqual(expected_value, self.get_value_path_solution(dd_instance, weights, objective))

    def test_independent_set(self):
        for file_name in ("Standard/johnson8-2-4.txt", "Custom/independent_set_instance_v5_d3_seed2.txt"):
            with self.subTest(file_name=file_name):
                params = IndependentSetStructure(os.path.join(INSTANCES_DIR, "IndependentSet", file_name))
                self.assert_semi_dd_equals_mdd(IndependentSetProblem(params), params.objective_weights, "max")

    def test_set_cover(self):
        for file_name in ("set_cover_v6_r3_seed1.txt", "set_cover_debug.txt"):
            with self.subTest(file_name=file_name):
                params = SetCoverStructure(os.path.join(INSTANCES_DIR, "SetCover", "Custom", file_name))
                self.assert_semi_dd_equals_mdd(SetCoverProblem(params), params.objective_weights, "min")

    def test_socknapsack(self):
        for file_name in ("knapsack_n5m2o1b5_1.txt", "knapsack_n5m2o5b5_2.txt"):
            with self.subTest(file_name=file_name):
                params = SOCKnapsackInstance(os.path.join(INSTANCES_DIR, "SOCKnapsack", file_name))
                self.assert_semi_dd_equals_mdd(SOCKnapsackProblem(params, 0), params.objective_weights, "max")

    def test_socknapsack_sentinel_connection(self):
        params = SOCKnapsackInstance(os.path.join(INSTANCES_DIR, "SOCKnapsack", "knapsack_n5m2o1b5_1.txt"))
        problem = SOCKnapsackProblem(params, 0)
        self.assertTrue(problem.connection_function([-2, -2], 0, 1, [10 ** 6, 10 ** 6]))
        self.assertTrue(problem.connection_function([-1, -1], 0, 0, [0, 0]))
        self.assertFalse(problem.connection_function([-1, -1], 0, 1, [0, 0]))
        self.assertFalse(problem.connection_function([-1, -1], 0, 0, [1, 1]))

    def test_socknapsack_requires_monotone_constraint(self):
        def make_params(linear_weights: list[int], omega: int) -> SimpleNamespace:
            return SimpleNamespace(initial_state=[0, 0], variables=[('x_1', [0, 1]), ('x_2', [0, 1])],
                                   linear_weights=[linear_weights], sqrt_weights=[[1, 1]],
                                   omega=omega, right_side_of_restrictions=[10])

        with self.assertRaises(ValueError):
            SOCKnapsackProblem(make_params([3, -1], 1), 0)
        with self.assertRaises(ValueError):
            SOCKnapsackProblem(make_params([3, 1], -1), 0)
        SOCKnapsackProblem(make_params([3, 0], 1), 0)

    def test_sequencing_permutations(self):
        params = SequencingStructure(os.path.join(INSTANCES_DIR, "Sequencing", "Custom", "sequencing_n5_s025_seed1.txt"))
        problem = SequencingProblem(params)
        for connect_layer in range(1, params.n_jobs + 1):
            problem.connect_layer = connect_layer
            for reduce in (False, True):
                with self.subTest(connect_layer=connect_layer, reduce=reduce):
                    dd_instance: DD = self.build_dd(problem, semi=True, reduce=reduce)
                    self.assertEqual(120, count_paths(dd_instance.get_decision_diagram()))


class ProblemsSemiDDWidthTest(unittest.TestCase):
    '''
    For every connection layer, the restricted sMDD must give a primal bound and the relaxed sMDD a
    dual bound, with every layer within the width; with an unbounded width both are the exact sMDD.
    '''

    def build_dd(self, problem: 'AbstractProblem', build, reduce: bool) -> DD:
        dd_instance: DD = DD(problem)
        with patch('sys.stdout', new_callable=io.StringIO):
            build(dd_instance)
            if reduce:
                dd_instance.reduce_decision_diagram()
        return dd_instance

    def solve(self, dd_instance: DD, weights: list[int], objective: str, solver_class) -> float:
        with patch('sys.stdout', new_callable=io.StringIO):
            solver = solver_class(dd_instance)
            solver.set_parameters(weights, objective)
            return solver.solve().value

    def assert_semi_dd_bounds(self, problem: 'AbstractProblem', weights: list[int], objective: str,
                              solver_class=ShortestLongestPath) -> None:
        exact: DD = self.build_dd(problem, lambda dd: dd.create_decision_diagram(), reduce=True)
        optimum: float = self.solve(exact, weights, objective, solver_class)
        expected_paths: int = count_paths(exact.get_decision_diagram())
        sign: int = 1 if objective == "max" else -1

        for connect_layer in range(1, len(problem.ordered_variables) + 1):
            problem.connect_layer = connect_layer
            for width in (1, 2, 3, UNBOUNDED_WIDTH):
                for reduce in (False, True):
                    with self.subTest(connect_layer=connect_layer, width=width, reduce=reduce):
                        restricted: DD = self.build_dd(problem, lambda dd: dd.create_semi_restricted_decision_diagram(width), reduce)
                        relaxed: DD = self.build_dd(problem, lambda dd: dd.create_semi_relax_priority_decision_diagram(width), reduce)
                        primal: float = self.solve(restricted, weights, objective, solver_class)
                        dual: float = self.solve(relaxed, weights, objective, solver_class)

                        self.assertLessEqual(sign * primal, sign * optimum + 1e-9)
                        self.assertGreaterEqual(sign * dual, sign * optimum - 1e-9)
                        for dd_instance in (restricted, relaxed):
                            self.assertLessEqual(max(len(layer) for layer in dd_instance.get_decision_diagram().structure), width)

                        if width == UNBOUNDED_WIDTH:
                            self.assertAlmostEqual(optimum, primal)
                            self.assertAlmostEqual(optimum, dual)
                            self.assertEqual(expected_paths, count_paths(restricted.get_decision_diagram()))
                            self.assertEqual(expected_paths, count_paths(relaxed.get_decision_diagram()))

    def test_knapsack(self):
        params = KnapsackStructure(os.path.join(INSTANCES_DIR, "Knapsack", "Standard", "f1_l-d_kp_10_269.txt"))
        problem = KnapsackProblem(params)
        self.assert_semi_dd_bounds(problem, problem.reorder_to_dd_order(params.objective_weights), "max")

    def assert_restricted_is_never_empty(self, problem: 'AbstractProblem', weights: list[int], objective: str,
                                         solver_class=ShortestLongestPath) -> None:
        no_solution: float = float("-inf") if objective == "max" else float("inf")
        for connect_layer in range(1, len(problem.ordered_variables) + 1):
            problem.connect_layer = connect_layer
            for width in (1, 2, 4):
                with self.subTest(connect_layer=connect_layer, width=width):
                    restricted: DD = self.build_dd(problem, lambda dd: dd.create_semi_restricted_decision_diagram(width), reduce=False)
                    self.assertNotEqual(no_solution, self.solve(restricted, weights, objective, solver_class))

    def test_knapsack_restricted_is_never_empty(self):
        # The backward discard keeps the empty suffix, which connects with every prefix.
        params = KnapsackStructure(os.path.join(INSTANCES_DIR, "Knapsack", "Standard", "f2_l-d_kp_20_878.txt"))
        problem = KnapsackProblem(params)
        self.assert_restricted_is_never_empty(problem, problem.reorder_to_dd_order(params.objective_weights), "max")

    def test_sequencing_restricted_is_never_empty(self):
        # The upper graph keeps the shortest jobs and the lower graph the longest ones.
        params = SequencingStructure(os.path.join(INSTANCES_DIR, "Sequencing", "Custom", "sequencing_n10_s025_seed1.txt"))
        problem = SequencingProblem(params)
        self.assert_restricted_is_never_empty(problem, problem.weights, "min", SequencingPathSolver)

    def test_independent_set(self):
        params = IndependentSetStructure(os.path.join(INSTANCES_DIR, "IndependentSet", "Standard", "johnson8-2-4.txt"))
        problem = IndependentSetProblem(params)
        self.assert_semi_dd_bounds(problem, problem.reorder_to_dd_order(params.objective_weights), "max")

    def test_set_cover(self):
        params = SetCoverStructure(os.path.join(INSTANCES_DIR, "SetCover", "Custom", "set_cover_v6_r3_seed1.txt"))
        problem = SetCoverProblem(params)
        self.assert_semi_dd_bounds(problem, problem.reorder_to_dd_order(params.objective_weights), "min")

    def test_socknapsack(self):
        params = SOCKnapsackInstance(os.path.join(INSTANCES_DIR, "SOCKnapsack", "knapsack_n5m2o5b5_2.txt"))
        problem = SOCKnapsackProblem(params, 0)
        self.assert_semi_dd_bounds(problem, problem.reorder_to_dd_order(params.objective_weights), "max")

    def test_sequencing(self):
        params = SequencingStructure(os.path.join(INSTANCES_DIR, "Sequencing", "Custom", "sequencing_n5_s025_seed1.txt"))
        problem = SequencingProblem(params)
        self.assert_semi_dd_bounds(problem, problem.weights, "min", SequencingPathSolver)

    def test_dd_kind(self):
        params = SequencingStructure(os.path.join(INSTANCES_DIR, "Sequencing", "Custom", "sequencing_n5_s025_seed1.txt"))
        problem = SequencingProblem(params)
        builders = {
            'restricted': lambda dd: dd.create_semi_restricted_decision_diagram(2),
            'relaxed': lambda dd: dd.create_semi_relax_priority_decision_diagram(2),
        }
        for expected, build in builders.items():
            with self.subTest(kind=expected):
                dd_instance: DD = self.build_dd(problem, build, reduce=True)
                self.assertEqual(expected, dd_instance.get_dd_kind())
                self.assertEqual(problem.connect_layer, dd_instance.get_connect_layer())


class KnapsackWithBackwardHooks(KnapsackProblem):
    '''
    Knapsack that records which merge and discard hooks each half of the sMDD calls.
    '''

    def __init__(self, params: 'KnapsackStructure'):
        super().__init__(params)
        self.calls: dict[str, int] = {'merge': 0, 'backward_merge': 0, 'discard': 0, 'backward_discard': 0}

    def merge_operator(self, state_one, state_two):
        self.calls['merge'] += 1
        return super().merge_operator(state_one, state_two)

    def backward_merge_operator(self, state_one, state_two):
        self.calls['backward_merge'] += 1
        return super().merge_operator(state_one, state_two)

    def get_priority_for_discard_node(self, state):
        self.calls['discard'] += 1
        return super().get_priority_for_discard_node(state)

    def get_backward_priority_for_discard_node(self, state):
        self.calls['backward_discard'] += 1
        return super().get_priority_for_discard_node(state)


class SemiDDBackwardHooksTest(unittest.TestCase):
    '''
    The lower graph must use the backward merge and discard hooks, and the upper graph the forward ones.
    '''

    def build_problem(self, connect_layer: int) -> KnapsackWithBackwardHooks:
        params = KnapsackStructure(os.path.join(INSTANCES_DIR, "Knapsack", "Standard", "f1_l-d_kp_10_269.txt"))
        problem = KnapsackWithBackwardHooks(params)
        problem.connect_layer = connect_layer
        return problem

    def test_hooks_by_half(self):
        number_of_variables: int = len(self.build_problem(1).ordered_variables)
        # k=1 has no upper layers and k=N no lower layers.
        cases = {1: ('backward_merge', 'merge', 'backward_discard', 'discard'),
                 number_of_variables: ('merge', 'backward_merge', 'discard', 'backward_discard')}
        for connect_layer, (merge_used, merge_unused, discard_used, discard_unused) in cases.items():
            with self.subTest(connect_layer=connect_layer):
                problem = self.build_problem(connect_layer)
                with patch('sys.stdout', new_callable=io.StringIO):
                    DD(problem).create_semi_relax_priority_decision_diagram(2)
                    DD(problem).create_semi_restricted_decision_diagram(2)
                self.assertGreater(problem.calls[merge_used], 0)
                self.assertEqual(0, problem.calls[merge_unused])
                self.assertGreater(problem.calls[discard_used], 0)
                self.assertEqual(0, problem.calls[discard_unused])


if __name__ == '__main__':
    unittest.main()
