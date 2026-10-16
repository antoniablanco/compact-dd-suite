import os
import sys
import io
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, os.pardir))
sys.path.append(parent_dir)

from SourceCode.DD import DD
from SourceCode.DDSemiBuilder.ExactSemiDDBuilder.ExactSemiDDBuilder import ExactSemiDDBuilder
from SourceCode.GraphAlgorithms.ShortestLongestPath.ShortestLongestPath import ShortestLongestPath
from SourceCode.GraphVisualization.GraphFile import GraphFile
from SourceCode.Problems.AbstractProblemClass import AbstractProblem
from Exceptions.MyExceptions import SemiDDNotSupported

from Examples.KnapsackInstance.KnapsackProblem import KnapsackProblem
from Examples.KnapsackInstance.KnapsackInstance import KnapsackStructure


class ProblemWithoutSemiDD(AbstractProblem):
    def transition_function(self, previous_state, variable_id, variable_value, scratch_state):
        scratch_state[0] = previous_state
        return True

    def get_state_as_string(self, state):
        return str(state)

    def get_state_copy(self, state):
        return state


def count_paths(graph: 'Graph') -> int:
    paths_to_node: dict[int, int] = {graph.structure[0][0].get_id(): 1}
    for layer in graph.structure[1:]:
        for node in layer:
            paths_to_node[node.get_id()] = sum(paths_to_node[arc.parent_node.get_id()] for arc in node.in_arcs)
    return paths_to_node[graph.structure[-1][0].get_id()]


class KnapsackSemiDDTest(unittest.TestCase):
    def setUp(self):

        params = SimpleNamespace(
            initial_state=0,
            variables=[('item_oro', [0, 1]), ('item_plata', [0, 1]), ('item_bronce', [0, 1]), ('item_hierro', [0, 1])],
            weights=[3, 3, 4, 6],
            right_side_of_restrictions=6,
        )

        self.problem_instance: 'AbstractProblem' = KnapsackProblem(params)

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

    def get_value_path_solution(self, dd_instance: DD, weights: list[int]) -> int:
        with patch('sys.stdout', new_callable=io.StringIO):
            shortest_longest_path_instance: ShortestLongestPath = ShortestLongestPath(dd_instance)
            shortest_longest_path_instance.set_parameters(weights, "max")
            return shortest_longest_path_instance.solve().value

    def test_default_connect_layer(self):
        self.assertEqual(2, self.problem_instance.connect_layer)

        params = SimpleNamespace(initial_state=0, variables=[(f'x_{i}', [0, 1]) for i in range(5)],
                                 weights=[1] * 5, right_side_of_restrictions=3)
        self.assertEqual(3, KnapsackProblem(params).connect_layer)

    def test_connect_layer_out_of_range(self):
        with self.assertRaises(ValueError):
            self.problem_instance.connect_layer = 0
        with self.assertRaises(ValueError):
            self.problem_instance.connect_layer = 5
        with self.assertRaises(TypeError):
            self.problem_instance.connect_layer = 2.0

    def test_get_initial_backward_state(self):
        self.assertEqual(0, self.problem_instance.get_initial_backward_state())

    def test_connection_function(self):
        self.assertTrue(self.problem_instance.connection_function(3, 1, 1, 0))
        self.assertFalse(self.problem_instance.connection_function(3, 1, 1, 4))
        self.assertTrue(self.problem_instance.connection_function(0, 1, 0, 6))

    def test_problem_without_semi_dd_functions(self):
        problem = ProblemWithoutSemiDD(0, [('x_1', [0, 1]), ('x_2', [0, 1])])
        with self.assertRaises(SemiDDNotSupported):
            ExactSemiDDBuilder(problem)

    def test_semi_dd_structure(self):
        dd_instance: DD = self.build_dd(self.problem_instance, semi=True, reduce=False)
        graph = dd_instance.get_decision_diagram()

        self.assertEqual([[0], [0, 3], [0, 4, 6], [0, 6], [0]],
                         [sorted(node.state for node in layer) for layer in graph.structure])
        self.assertEqual(9, graph.get_node_count())
        self.assertEqual(13, graph.get_arc_count())
        self.assertEqual(6, count_paths(graph))
        self.assertEqual(list(range(9)), [node.get_id() for layer in graph.structure for node in layer])

    def test_reduce_semi_dd_structure(self):
        dd_instance: DD = self.build_dd(self.problem_instance, semi=True, reduce=True)
        graph = dd_instance.get_decision_diagram()

        self.assertEqual([1, 2, 2, 2, 1], [len(layer) for layer in graph.structure])
        self.assertEqual(8, graph.get_node_count())
        self.assertEqual(12, graph.get_arc_count())
        self.assertEqual(6, count_paths(graph))

    def test_last_connect_layer_equals_reduced_dd(self):
        mdd_graph = self.build_dd(self.problem_instance, semi=False, reduce=True).get_decision_diagram()

        self.problem_instance.connect_layer = 4
        semi_graph = self.build_dd(self.problem_instance, semi=True, reduce=True).get_decision_diagram()

        self.assertEqual(mdd_graph.get_node_count(), semi_graph.get_node_count())
        self.assertEqual(mdd_graph.get_arc_count(), semi_graph.get_arc_count())
        self.assertTrue(mdd_graph == semi_graph)

    def test_semi_dd_standard_instance(self):
        file_path: str = os.path.join(parent_dir, "..", "DataInstances", "Knapsack", "Standard", "f1_l-d_kp_10_269.txt")
        knapsack_instance = KnapsackStructure(file_path)
        problem = KnapsackProblem(knapsack_instance)

        mdd: DD = self.build_dd(problem, semi=False, reduce=True)
        expected_paths: int = count_paths(mdd.get_decision_diagram())

        for connect_layer in range(1, 11):
            problem.connect_layer = connect_layer
            for reduce in (False, True):
                with self.subTest(connect_layer=connect_layer, reduce=reduce):
                    dd_instance: DD = self.build_dd(problem, semi=True, reduce=reduce)
                    self.assertEqual(expected_paths, count_paths(dd_instance.get_decision_diagram()))
                    self.assertEqual(295, self.get_value_path_solution(dd_instance, knapsack_instance.objective_weights))
                    if reduce:
                        self.assertEqual(mdd.get_decision_diagram().get_node_count(), dd_instance.get_decision_diagram().get_node_count())

    def test_verbose_create_semi_dd(self):
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            dd_instance: DD = DD(self.problem_instance)
            dd_instance.create_semi_decision_diagram(verbose=True)
            dd_instance.reduce_decision_diagram(verbose=True)
        self.assertIn("[item_bronce]", mock_stdout.getvalue())

    def test_export_semi_dd_highlights_connection_layer(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            semi_dd: DD = self.build_dd(self.problem_instance, semi=True, reduce=True)
            semi_dd.export_graph_file(os.path.join(temp_dir, "semi"))
            with open(os.path.join(temp_dir, "semi.gml")) as gml_file:
                semi_gml: str = gml_file.read()

            mdd: DD = self.build_dd(self.problem_instance, semi=False, reduce=True)
            mdd.export_graph_file(os.path.join(temp_dir, "mdd"))
            with open(os.path.join(temp_dir, "mdd.gml")) as gml_file:
                mdd_gml: str = gml_file.read()

        connection_layer = semi_dd.get_decision_diagram().structure[semi_dd.get_connect_layer() - 1]
        connection_arcs: int = sum(len(node.out_arcs) for node in connection_layer)
        self.assertEqual(connection_arcs, semi_gml.count(GraphFile.CONNECTION_ARC_COLOR))
        self.assertNotIn(GraphFile.CONNECTION_ARC_COLOR, mdd_gml)

    def test_get_dd_kind_and_connect_layer(self):
        mdd: DD = self.build_dd(self.problem_instance, semi=False, reduce=False)
        self.assertIsNone(mdd.get_connect_layer())

        dd_instance: DD = self.build_dd(self.problem_instance, semi=True, reduce=False)
        self.assertEqual('exact', dd_instance.get_dd_kind())
        self.assertEqual(2, dd_instance.get_connect_layer())


if __name__ == '__main__':
    unittest.main()
