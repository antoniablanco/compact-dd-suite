import os
import sys
import io
import unittest
from types import SimpleNamespace
from unittest.mock import patch

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, os.pardir))
sys.path.append(parent_dir)

from SourceCode.DD import DD
from SourceCode.DDStructure.Node import Node
from SourceCode.DDStructure.Arc import Arc
from SourceCode.DDStructure.Graph import Graph
from SourceCode.GraphAlgorithms.DDReducer.DDReducer import DDReducer
from SourceCode.GraphAlgorithms.ShortestLongestPath.ShortestLongestPath import ShortestLongestPath

from Examples.KnapsackInstance.KnapsackProblem import KnapsackProblem
from Examples.AbstractGurobiProblems.AbstractProblemGurobiClass import AbstractProblemGurobi


class KnapsackProblemSortedByWeight(KnapsackProblem):
    def __init__(self, params: 'KnapsackStructure', sort: bool = True):
        self._raw_weights = params.weights
        super().__init__(params, sort)

    def sort_variables(self, variables: list[tuple['Variable', 'Domain']]) -> list[str]:
        positions = sorted(range(len(variables)), key=lambda i: -self._raw_weights[i])
        return [variables[i][0] for i in positions]


class KnapsackProblemWrongSort(KnapsackProblem):
    def sort_variables(self, variables: list[tuple['Variable', 'Domain']]) -> list[str]:
        return [name for name, _ in variables][:-1]


class VariableOrderingTest(unittest.TestCase):
    def setUp(self):

        self.params = SimpleNamespace(
            initial_state=0,
            variables=[('item_oro', [0, 1]), ('item_plata', [0, 1]), ('item_bronce', [0, 1]), ('item_hierro', [0, 1])],
            weights=[3, 3, 4, 6],
            right_side_of_restrictions=6,
        )
        self.objective_weights: list[int] = [-5, 1, 18, 15]

        self.problem_instance: 'AbstractProblem' = KnapsackProblemSortedByWeight(self.params)

    def solve(self, problem: 'AbstractProblem', semi: bool = False) -> int:
        dd_instance: DD = DD(problem)
        with patch('sys.stdout', new_callable=io.StringIO):
            if semi:
                dd_instance.create_semi_decision_diagram()
            else:
                dd_instance.create_decision_diagram()
            dd_instance.reduce_decision_diagram()

            shortest_longest_path_instance: ShortestLongestPath = ShortestLongestPath(dd_instance)
            shortest_longest_path_instance.set_parameters(problem.reorder_to_dd_order(self.objective_weights), "max")
            return shortest_longest_path_instance.solve().value

    def test_sorted_mappings(self):
        self.assertEqual(['item_hierro', 'item_bronce', 'item_oro', 'item_plata'], self.problem_instance.ordered_variables)
        self.assertEqual([3, 2, 0, 1], self.problem_instance.dd_to_original_index)
        self.assertEqual(0, self.problem_instance.name_to_index['item_hierro'])
        self.assertEqual('item_oro', self.problem_instance.index_to_name[2])
        self.assertEqual([6, 4, 3, 3], self.problem_instance.weights)

    def test_sorted_problem_same_solution(self):
        unsorted_problem: 'AbstractProblem' = KnapsackProblemSortedByWeight(self.params, sort=False)
        expected_value: int = self.solve(unsorted_problem)

        self.assertEqual(expected_value, self.solve(self.problem_instance))
        self.assertEqual(expected_value, self.solve(self.problem_instance, semi=True))

    def test_ordering_cannot_change(self):
        for attribute in ('ordered_variables', 'name_to_index', 'index_to_name', 'dd_to_original_index'):
            with self.subTest(attribute=attribute):
                with self.assertRaises(AttributeError):
                    setattr(self.problem_instance, attribute, [])

    def test_sort_must_return_permutation(self):
        with self.assertRaises(ValueError):
            KnapsackProblemWrongSort(self.params)

    def test_domains_follow_ordering(self):
        params = SimpleNamespace(
            initial_state=0,
            variables=[('x_1', [0, 1]), ('x_2', [0, 1, 2])],
            weights=[1, 5],
            right_side_of_restrictions=20,
        )
        dd_instance: DD = DD(KnapsackProblemSortedByWeight(params))
        with patch('sys.stdout', new_callable=io.StringIO):
            dd_instance.create_decision_diagram()

        root: 'Node' = dd_instance.get_decision_diagram().structure[0][0]
        self.assertEqual([0, 1, 2], sorted(arc.variable_value for arc in root.out_arcs))

    def test_reducer_ignores_arc_order(self):
        problem = SimpleNamespace(ordered_variables=['x_1', 'x_2'], get_state_as_string=str)
        root, node_a, node_b, terminal_0 = (Node(i, i) for i in range(4))
        graph = Graph(root)
        graph.add_new_layer()
        graph.add_node(node_a)
        graph.add_node(node_b)
        graph.add_new_layer()
        graph.add_node(terminal_0)

        for parent_node, child_node, value in [(root, node_a, 0), (root, node_b, 1),
                                               (node_a, terminal_0, 0), (node_a, terminal_0, 1),
                                               (node_b, terminal_0, 1), (node_b, terminal_0, 0)]:
            arc = Arc(parent_node, child_node, value)
            parent_node.out_arcs.append(arc)
            child_node.in_arcs.append(arc)

        DDReducer(graph, problem).reduce_decision_diagram(False)
        self.assertEqual([1, 1, 1], [len(layer) for layer in graph.structure])

    def test_gurobi_values_follow_dd_order(self):
        dd_instance = SimpleNamespace(problem=self.problem_instance)
        x_sol_dd, var_ids = AbstractProblemGurobi._get_variable_values(None, [0.1, 0.2, 0.3, 0.4], dd_instance)
        self.assertEqual([3, 2, 0, 1], var_ids)
        self.assertEqual([0.4, 0.3, 0.1, 0.2], x_sol_dd)


if __name__ == '__main__':
    unittest.main()
