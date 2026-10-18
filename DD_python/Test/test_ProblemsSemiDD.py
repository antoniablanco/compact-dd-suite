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

from Examples.IndependentSetInstance.IndependentSetInstance import IndependentSetStructure
from Examples.IndependentSetInstance.IndependentSetProblem import IndependentSetProblem
from Examples.SetCoverInstance.SetCoverInstance import SetCoverStructure
from Examples.SetCoverInstance.SetCoverProblem import SetCoverProblem
from Examples.SOCKnapsack.SOCKnapsackInstance import SOCKnapsackInstance
from Examples.SOCKnapsack.SOCKnapsackProblem import SOCKnapsackProblem
from Examples.SequencingInstance.SequencingInstance import SequencingStructure
from Examples.SequencingInstance.SequencingProblem import SequencingProblem

INSTANCES_DIR: str = os.path.join(parent_dir, "..", "DataInstances")


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


if __name__ == '__main__':
    unittest.main()
