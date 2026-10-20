import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, os.pardir))
sys.path.append(parent_dir)

from SourceCode.DDSemiBuilder.AbstractSemiDDBuilder import AbstractSemiDDBuilder

class RestrictedSemiDDBuilder(AbstractSemiDDBuilder):
    '''
    Concrete class that inherits from AbstractSemiDDBuilder, generating a restricted semi decision
    diagram. Every layer of the upper and lower graphs keeps at most max_width nodes; the rest are
    discarded, so the diagram represents a subset of the feasible solutions.
    '''

    def __init__(self, problem: 'AbstractProblem', max_width: int) -> None:
        '''
        Constructor for the RestrictedSemiDDBuilder class.

        Parameters:
        - problem: Problem object for which the graph will be constructed.
        - max_width: Maximum allowed width for every layer of the upper and lower graphs.
        '''
        super().__init__(problem)
        self._max_width: int = max_width

    def _specific_end_of_layer_function(self, graph: 'Graph') -> None:
        '''
        Discards the lowest priority nodes of the last layer when its width exceeds the maximum.
        The lower graph uses the backward discard priority.

        Parameters:
        - graph: Graph (upper or lower) whose last layer was just created.
        '''
        if len(graph.structure[-1]) > self._max_width:
            self._eliminate_nodes_when_width_is_greater_than_w(graph, graph is self._lower_graph)

    def _specific_end_of_construction_function(self) -> None:
        '''
        Removes the nodes left without a root-terminal path after the connection.
        '''
        self._prune_graph()

    def _eliminate_nodes_when_width_is_greater_than_w(self, graph: 'Graph', is_lower_graph: bool) -> None:
        '''
        Keeps the max_width nodes of the last layer with the lowest discard priority and removes the
        rest, together with their arcs to the previous layer. The kept nodes keep their order.

        Parameters:
        - graph: Graph (upper or lower) whose last layer is trimmed.
        - is_lower_graph: True if the layer was built bottom-up (its nodes are the parents of the arcs).
        '''
        get_priority = (self._problem.get_backward_priority_for_discard_node if is_lower_graph
                        else self._problem.get_priority_for_discard_node)
        layer: list['Node'] = graph.structure[-1]
        ordered_nodes: list['Node'] = sorted(layer, key=lambda node: get_priority(node.state))

        for node in ordered_nodes[self._max_width:]:
            if is_lower_graph:
                node.out_arcs.clear()
            else:
                node.in_arcs.clear()

        if is_lower_graph:
            layer[:] = [node for node in layer if node.out_arcs]
            for node in graph.structure[-2]:
                node.in_arcs[:] = [arc for arc in node.in_arcs if arc.parent_node.out_arcs]
        else:
            layer[:] = [node for node in layer if node.in_arcs]
            for node in graph.structure[-2]:
                node.out_arcs[:] = [arc for arc in node.out_arcs if arc.child_node.in_arcs]
