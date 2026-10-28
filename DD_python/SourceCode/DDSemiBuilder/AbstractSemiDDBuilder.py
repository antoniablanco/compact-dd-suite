from abc import ABC, abstractmethod

import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, os.pardir))
sys.path.append(parent_dir)

from SourceCode.DDStructure.Node import Node
from SourceCode.DDStructure.Arc import Arc
from SourceCode.DDStructure.Graph import Graph
from SourceCode.Problems.AbstractProblemClass import AbstractProblem
from Exceptions.MyExceptions import SemiDDNotSupported


class AbstractSemiDDBuilder(ABC):
    '''
    Abstract class that provides the foundation for building semi decision diagrams (sMDD).

    With N variables and connection layer k (problem.connect_layer), the diagram is built in three parts:
    - Upper graph: layers 0..k-1, built top-down from the root with the transition function
      (variables 1..k-1).
    - Lower graph: layers k..N, built bottom-up from the terminal with the backward transition
      function (variables k+1..N). Its structure is stored reversed (structure[0] is the terminal),
      but its arcs already point in the direction of the diagram (parent in layer j, child in j+1).
    - Connection: arcs of variable k from layer k-1 to layer k, created with the connection
      function. Afterwards the lower graph is appended to the upper one, so the result is an
      ordinary layered Graph (root in structure[0], terminal in structure[-1]).
    '''

    _SEMI_DD_METHODS: tuple[str, ...] = ('connection_function',)

    def __init__(self, problem: AbstractProblem) -> None:
        '''
        Constructor for the AbstractSemiDDBuilder class.

        Parameters:
        - problem: Reference to the problem associated with the graph. 
        '''
        self._check_problem_supports_semi_dd(problem)

        self._node_number: int = 0
        self.graph: 'Graph' = None
        self._upper_graph: 'Graph' = None
        self._lower_graph: 'Graph' = None
        self._problem: 'AbstractProblem' = problem
        self._variables: list[str] = problem.ordered_variables
        self._variables_index: list[int] = [problem.name_to_index[name] for name in self._variables]
        self._variables_domain: list[list[int]] = [problem.variables_domain[name] for name in self._variables]
        self._map_of_states: dict[str, Node] = {}
        self.connect_layer: int = problem.connect_layer

        initial_backward_state: 'State' = problem.get_initial_backward_state()
        self._scratch_state: list = [problem.get_state_copy(problem.initial_state)]
        self._backward_scratch_state: list = [problem.get_state_copy(initial_backward_state)]

        self._initialize_graphs(problem.initial_state, initial_backward_state)

    def _check_problem_supports_semi_dd(self, problem: AbstractProblem) -> None:
        '''
        Raises SemiDDNotSupported if the problem does not override the semi DD methods.

        Parameters:
        - problem: Problem to check.
        '''
        problem_class = type(problem)
        missing_methods: list[str] = [
            method_name for method_name in self._SEMI_DD_METHODS
            if getattr(problem_class, method_name) is getattr(AbstractProblem, method_name)
        ]
        if missing_methods:
            raise SemiDDNotSupported(problem_class.__name__, missing_methods)

    def _initialize_graphs(self, initial_state: 'State', initial_backward_state: 'State') -> None:
        '''
        Initializes the upper graph with the root node and the lower graph with the terminal node.

        Parameters:
        - initial_state: State of the root node.
        - initial_backward_state: State of the terminal node.
        '''
        self._upper_graph = Graph(Node(self._node_number, initial_state))
        self._node_number += 1
        self._lower_graph = Graph(Node(self._node_number, initial_backward_state))
        self._node_number += 1

    def get_decision_diagram(self, should_visualize: bool) -> Graph:
        '''
        Builds the semi decision diagram.

        Parameters:
        - should_visualize: Boolean indicating whether to visualize the graph construction.

        Returns:
        - Graph: Pointer to the constructed graph.
        '''
        self._build_upper_graph(should_visualize)
        self._build_lower_graph(should_visualize)
        self._connect_graphs()

        self._specific_end_of_construction_function()
        self.adjust_node_number()
        self._print_graph(should_visualize, self.graph)

        return self.graph

    def _build_upper_graph(self, should_visualize: bool) -> None:
        '''
        Builds layers 1..k-1 top-down with the transition function.

        Parameters:
        - should_visualize: Boolean indicating whether to visualize the graph construction.
        '''
        transition_function = self._problem.transition_function

        for variable_id in range(self.connect_layer - 1):
            self._create_new_layer(self._upper_graph, variable_id, transition_function, False)
            self._specific_end_of_layer_function(self._upper_graph)
            self._print_graph(should_visualize, self._upper_graph)

    def _build_lower_graph(self, should_visualize: bool) -> None:
        '''
        Builds layers N-1..k bottom-up with the backward transition function.

        Parameters:
        - should_visualize: Boolean indicating whether to visualize the graph construction.
        '''
        backward_transition_function = self._problem.backward_transition_function

        for variable_id in range(len(self._variables) - 1, self.connect_layer - 1, -1):
            self._create_new_layer(self._lower_graph, variable_id, backward_transition_function, True)
            self._specific_end_of_layer_function(self._lower_graph)
            self._print_graph(should_visualize, self._lower_graph, is_lower_graph=True)

    def _create_new_layer(self, graph: Graph, variable_id: int, transition_function, is_lower_graph: bool) -> None:
        '''
        Creates a new layer in a graph, expanding every node of its last layer with the given
        transition function. In the lower graph the new node is the parent of the arc.

        Parameters:
        - graph: Graph (upper or lower) that receives the new layer.
        - variable_id: Position of the variable in the ordering.
        - transition_function: Forward or backward transition function of the problem.
        - is_lower_graph: True if the layer is built bottom-up.
        '''
        graph.add_new_layer()
        self._map_of_states = {}
        map_of_states: dict[str, Node] = self._map_of_states
        variable_index: int = self._variables_index[variable_id]
        domain: list[int] = self._variables_domain[variable_id]
        scratch_state: list = self._backward_scratch_state if is_lower_graph else self._scratch_state
        get_state_as_string = self._problem.get_state_as_string

        for previous_node in graph.structure[-2]:
            previous_state = previous_node.state

            for variable_value in domain:
                if not transition_function(previous_state, variable_index, variable_value, scratch_state):
                    continue

                state_as_string: str = get_state_as_string(scratch_state[0])
                new_node: 'Node' = map_of_states.get(state_as_string)

                if new_node is None:
                    node_state = self._problem.get_state_copy(scratch_state[0])
                    new_node = graph.create_and_add_node(self._node_number, node_state)
                    map_of_states[state_as_string] = new_node
                    self._node_number += 1

                if is_lower_graph:
                    self._create_arc(new_node, previous_node, variable_value)
                else:
                    self._create_arc(previous_node, new_node, variable_value)

    def _create_arc(self, parent_node: Node, child_node: Node, variable_value: int) -> None:
        '''
        Creates an arc from parent_node to child_node.

        Parameters:
        - parent_node: Node in the upper layer.
        - child_node: Node in the lower layer.
        - variable_value: Value of the variable for which the arc is created.
        '''
        arc: Arc = Arc(parent_node, child_node, variable_value)

        parent_node.out_arcs.append(arc)
        child_node.in_arcs.append(arc)

    def _connect_graphs(self) -> None:
        '''
        Creates the arcs of the connection layer and appends the lower graph to the upper one.
        '''
        self._create_connection_arcs()
        self._join_graphs()

    def _create_connection_arcs(self) -> None:
        '''
        Creates an arc (u, value, w) for every node u in the last upper layer, every value of the
        connection variable and every node w in the first lower layer accepted by the connection
        function. The resulting layer is not deterministic.
        '''
        variable_id: int = self.connect_layer - 1
        variable_index: int = self._variables_index[variable_id]
        domain: list[int] = self._variables_domain[variable_id]
        connection_function = self._problem.connection_function
        lower_layer: list[Node] = self._lower_graph.structure[-1]

        for upper_node in self._upper_graph.structure[-1]:
            upper_state = upper_node.state
            out_arcs: list[Arc] = upper_node.out_arcs

            for variable_value in domain:
                for lower_node in lower_layer:
                    if connection_function(upper_state, variable_index, variable_value, lower_node.state):
                        arc: Arc = Arc(upper_node, lower_node, variable_value)
                        out_arcs.append(arc)
                        lower_node.in_arcs.append(arc)

    def _join_graphs(self) -> None:
        '''
        Appends the layers of the lower graph, in diagram order, to the upper graph, which
        becomes the final graph.
        '''
        self.graph = self._upper_graph
        self.graph.structure.extend(reversed(self._lower_graph.structure))
        self.graph.actual_layer = len(self.graph.structure) - 1
        self._lower_graph = None

    def _prune_graph(self) -> bool:
        '''
        Removes the nodes that do not belong to any root-terminal path. Must run after the join.

        Returns:
        - bool: True if at least one node was removed, False otherwise.
        '''
        delete_some_node: bool = self._bottom_up_pruner()
        if self._top_down_pruner():
            delete_some_node = True
        return delete_some_node

    def _bottom_up_pruner(self) -> bool:
        '''
        Prunes the upper part (layers k-1..1): removes nodes without outgoing arcs and the arcs
        that point to them.

        Returns:
        - bool: True if at least one node was removed, False otherwise.
        '''
        structure: list[list[Node]] = self.graph.structure
        delete_some_node: bool = False

        for layer_id in range(self.connect_layer - 1, 0, -1):
            layer: list[Node] = structure[layer_id]
            live_nodes: list[Node] = []
            dirty_parents: dict[int, Node] = {}

            for node in layer:
                if node.out_arcs:
                    live_nodes.append(node)
                else:
                    for arc in node.in_arcs:
                        dirty_parents[id(arc.parent_node)] = arc.parent_node
                    node.in_arcs.clear()

            if len(live_nodes) != len(layer):
                delete_some_node = True
                layer[:] = live_nodes
                for parent_node in dirty_parents.values():
                    parent_node.out_arcs[:] = [arc for arc in parent_node.out_arcs if arc.child_node.out_arcs]

        return delete_some_node

    def _top_down_pruner(self) -> bool:
        '''
        Prunes the lower part (layers k..N-1): removes nodes without incoming arcs and the arcs
        that leave them.

        Returns:
        - bool: True if at least one node was removed, False otherwise.
        '''
        structure: list[list[Node]] = self.graph.structure
        delete_some_node: bool = False

        for layer_id in range(self.connect_layer, len(structure) - 1):
            layer: list[Node] = structure[layer_id]
            live_nodes: list[Node] = []
            dirty_children: dict[int, Node] = {}

            for node in layer:
                if node.in_arcs:
                    live_nodes.append(node)
                else:
                    for arc in node.out_arcs:
                        dirty_children[id(arc.child_node)] = arc.child_node
                    node.out_arcs.clear()

            if len(live_nodes) != len(layer):
                delete_some_node = True
                layer[:] = live_nodes
                for child_node in dirty_children.values():
                    child_node.in_arcs[:] = [arc for arc in child_node.in_arcs if arc.parent_node.in_arcs]

        return delete_some_node

    def _print_graph(self, should_visualize: bool, graph: Graph, is_lower_graph: bool = False) -> None:
        '''
        Print the graph if visualization is requested.

        Parameters:
        - should_visualize: Boolean indicating whether to visualize the graph.
        - graph: Graph to print (upper, lower or final).
        - is_lower_graph: True if the graph structure is stored bottom-up.
        '''
        if should_visualize:
            self._print(graph, is_lower_graph)

    def _print(self, graph: Graph, is_lower_graph: bool) -> None:
        '''
        Print the content of each layer of the graph, labelled with its diagram layer. The lower
        graph is printed in diagram order (top to bottom), even though it is stored bottom-up.

        Parameters:
        - graph: Graph to print.
        - is_lower_graph: True if the graph structure is stored bottom-up.
        '''
        number_of_variables: int = len(self._variables)
        layers = list(enumerate(graph.structure))
        if is_lower_graph:
            layers.reverse()
        print("")
        print("")
        for position, layer in layers:
            layer_idx: int = number_of_variables - position if is_lower_graph else position
            print("------------------------------------------------------")
            if 0 < layer_idx <= number_of_variables:
                print(f"[{self._variables[layer_idx - 1]}]", end="   ")
            for node in layer:
                in_arcs_str: str = ", ".join(arc.to_string() for arc in node.in_arcs)
                print("u" + node.to_string() + " " + self._problem.get_state_as_string(node.state) + "(" + in_arcs_str + ")", end="   ")
            print("")

    def adjust_node_number(self) -> None:
        '''
        Renumbers the nodes of the graph consecutively in layer order (root = 0).
        '''
        initial_node_number: int = 0
        for layer in self.graph.structure:
            for node in layer:
                node.set_id(initial_node_number)
                initial_node_number += 1

    @abstractmethod
    def _specific_end_of_layer_function(self, graph: Graph) -> None:
        '''
        Pure virtual method called after each layer of the upper or lower graph is created.

        Parameters:
        - graph: Graph (upper or lower) whose last layer was just created.
        '''
        pass

    @abstractmethod
    def _specific_end_of_construction_function(self) -> None:
        '''
        Pure virtual method called once the upper and lower graphs are connected.
        '''
        pass
