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
        self._connection_weights: list[int] = None
        self._connection_objective: str = None
        self._merge_before_connecting: bool = False

        initial_backward_state: 'State' = problem.get_initial_backward_state()
        self._scratch_state: list = [problem.get_state_copy(problem.initial_state)]
        self._backward_scratch_state: list = [problem.get_state_copy(initial_backward_state)]

        self._initialize_graphs(problem.initial_state, initial_backward_state)

    def set_connection_pruning(self, weights: list[int], objective: str) -> None:
        '''
        Keeps, for every node of the last upper layer and every value of the connection variable,
        only the arc to the compatible lower node with the best value to the terminal. The optimal
        value of the diagram does not change, but it no longer holds every solution: it is only
        valid for these weights (not for cuts) and for objectives that add one weight per arc.

        Parameters:
        - weights(list[int]): Objective weight of each variable, in diagram order.
        - objective(str): "max" or "min".
        '''
        self._connection_weights = weights
        self._connection_objective = objective

    def set_merge_before_connecting(self) -> None:
        '''
        Before creating the connection arcs, merges the nodes of the last upper layer that connect
        with the same lower nodes and then the nodes of the first lower layer reached by the same
        upper nodes, as the reduction would do afterwards. Only the arcs between the kept nodes
        are created. Ignored when the connection pruning is enabled.
        '''
        self._merge_before_connecting = True

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
        function. The resulting layer is not deterministic. If the problem builds a connection
        index, only its candidates are checked.
        '''
        variable_id: int = self.connect_layer - 1
        variable_index: int = self._variables_index[variable_id]
        domain: list[int] = self._variables_domain[variable_id]
        connection_function = self._problem.connection_function
        lower_layer: list[Node] = self._lower_graph.structure[-1]
        connection_index = self._problem.get_connection_index(variable_index, [node.state for node in lower_layer])
        all_positions: range = range(len(lower_layer))
        lower_scores: list[float] = None if self._connection_weights is None else self._lower_layer_scores()

        if self._merge_before_connecting and lower_scores is None:
            self._create_merged_connection_arcs(variable_index, domain, connection_index, all_positions)
            return

        for upper_node in self._upper_graph.structure[-1]:
            upper_state = upper_node.state
            out_arcs: list[Arc] = upper_node.out_arcs

            for variable_value in domain:
                candidates = all_positions if connection_index is None else \
                    self._problem.get_connection_candidates(connection_index, upper_state, variable_index, variable_value)
                if lower_scores is not None:
                    self._create_best_connection_arc(upper_node, variable_index, variable_value, candidates, lower_scores)
                    continue
                for position in candidates:
                    lower_node: Node = lower_layer[position]
                    if connection_function(upper_state, variable_index, variable_value, lower_node.state):
                        arc: Arc = Arc(upper_node, lower_node, variable_value)
                        out_arcs.append(arc)
                        lower_node.in_arcs.append(arc)

    def _create_merged_connection_arcs(self, variable_index: int, domain: list[int], connection_index, all_positions: range) -> None:
        '''
        Creates the connection arcs after merging, in the last upper layer, the nodes compatible
        with the same lower nodes for every value and, in the first lower layer, the nodes reached
        by the same kept upper nodes for every value. The first node of each group is kept.

        Parameters:
        - variable_index: Index of the connection variable.
        - domain: Values of the connection variable.
        - connection_index: Index returned by get_connection_index, or None.
        - all_positions: Every position of the first lower layer.
        '''
        connection_function = self._problem.connection_function
        upper_layer: list[Node] = self._upper_graph.structure[-1]
        lower_layer: list[Node] = self._lower_graph.structure[-1]

        upper_group_by_signature: dict[tuple, int] = {}
        kept_upper: list[Node] = []
        group_positions: list[tuple] = []
        for upper_node in upper_layer:
            upper_state = upper_node.state
            signature: tuple = tuple(
                tuple(position for position in (all_positions if connection_index is None else
                      self._problem.get_connection_candidates(connection_index, upper_state, variable_index, variable_value))
                      if connection_function(upper_state, variable_index, variable_value, lower_layer[position].state))
                for variable_value in domain)
            group: int = upper_group_by_signature.get(signature)
            if group is None:
                upper_group_by_signature[signature] = len(kept_upper)
                kept_upper.append(upper_node)
                group_positions.append(signature)
            else:
                for arc in upper_node.in_arcs:
                    arc.child_node = kept_upper[group]
                    kept_upper[group].in_arcs.append(arc)
                upper_node.in_arcs.clear()
        upper_layer[:] = kept_upper

        reached_by: list[list[list[int]]] = [[[] for _ in domain] for _ in lower_layer]
        for group, signature in enumerate(group_positions):
            for value_position, positions in enumerate(signature):
                for position in positions:
                    reached_by[position][value_position].append(group)

        lower_group_by_signature: dict[tuple, int] = {}
        kept_lower: list[Node] = []
        lower_group: list[int] = []
        for position, lower_node in enumerate(lower_layer):
            signature = tuple(map(tuple, reached_by[position]))
            group = lower_group_by_signature.get(signature)
            if group is None:
                group = lower_group_by_signature[signature] = len(kept_lower)
                kept_lower.append(lower_node)
            else:
                for arc in lower_node.out_arcs:
                    arc.parent_node = kept_lower[group]
                    kept_lower[group].out_arcs.append(arc)
                lower_node.out_arcs.clear()
            lower_group.append(group)
        lower_layer[:] = kept_lower

        for group, signature in enumerate(group_positions):
            for value_position, positions in enumerate(signature):
                connected: set[int] = set()
                for position in positions:
                    if lower_group[position] not in connected:
                        connected.add(lower_group[position])
                        self._create_arc(kept_upper[group], kept_lower[lower_group[position]], domain[value_position])

    def _lower_layer_scores(self) -> list[float]:
        '''
        Best value from each node of the first lower layer to the terminal, signed so that higher
        is better (-inf if the terminal is unreachable). Used by the connection pruning.

        Returns:
        - list[float]: The score of each node of the first lower layer, in layer order.
        '''
        sign: int = 1 if self._connection_objective == "max" else -1
        structure: list[list[Node]] = self._lower_graph.structure
        number_of_variables: int = len(self._variables)
        scores: dict[int, float] = {id(structure[0][0]): 0}

        for layer_position in range(1, len(structure)):
            weight: int = sign * self._connection_weights[number_of_variables - layer_position]
            for node in structure[layer_position]:
                scores[id(node)] = max((scores.get(id(arc.child_node), float("-inf")) + arc.variable_value * weight
                                        for arc in node.out_arcs), default=float("-inf"))

        return [scores[id(node)] for node in structure[-1]]

    def _create_best_connection_arc(self, upper_node: Node, variable_index: int, variable_value: int,
                                    candidates, lower_scores: list[float]) -> None:
        '''
        Creates the arc from upper_node to the compatible lower node with the best score; the first
        one in layer order on ties.

        Parameters:
        - upper_node: Node of the last upper layer.
        - variable_index: Index of the connection variable.
        - variable_value: Value of the connection variable.
        - candidates: Positions of the first lower layer that may connect.
        - lower_scores: Score of each node of the first lower layer.
        '''
        connection_function = self._problem.connection_function
        lower_layer: list[Node] = self._lower_graph.structure[-1]
        best_position: int = None
        best_score: float = float("-inf")

        for position in candidates:
            if lower_scores[position] > best_score and \
                    connection_function(upper_node.state, variable_index, variable_value, lower_layer[position].state):
                best_position, best_score = position, lower_scores[position]

        if best_position is not None:
            self._create_arc(upper_node, lower_layer[best_position], variable_value)

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
