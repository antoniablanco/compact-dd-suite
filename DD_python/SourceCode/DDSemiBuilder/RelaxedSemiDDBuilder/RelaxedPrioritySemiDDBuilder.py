import os
import sys
import heapq

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, os.pardir))
sys.path.append(parent_dir)

from SourceCode.DDSemiBuilder.AbstractSemiDDBuilder import AbstractSemiDDBuilder

class RelaxedPrioritySemiDDBuilder(AbstractSemiDDBuilder):
    '''
    Concrete class that inherits from AbstractSemiDDBuilder, generating a relaxed semi decision
    diagram. Every layer of the upper and lower graphs keeps at most max_width nodes by merging the
    two highest priority nodes, as RelaxedPriorityDDBuilder does. The upper graph uses
    merge_operator and get_priority_for_merge_nodes; the lower graph uses their backward versions,
    and since its nodes are the parents of the arcs, a merge redirects outgoing arcs.
    '''

    def __init__(self, problem: 'AbstractProblem', max_width: int) -> None:
        '''
        Constructor for the RelaxedPrioritySemiDDBuilder class.

        Parameters:
        - problem(AbstractProblem): Problem object for which the graph will be constructed.
        - max_width(int): Maximum allowed width for every layer of the upper and lower graphs.
        '''
        super().__init__(problem)
        self._max_width: int = max_width
        self._is_lower_graph: bool = False

    def _specific_end_of_layer_function(self, graph: 'Graph') -> None:
        '''
        Merges nodes of the last layer when its width exceeds the specified maximum.

        Parameters:
        - graph: Graph (upper or lower) whose last layer was just created.
        '''
        if len(graph.structure[-1]) > self._max_width:
            self._is_lower_graph = graph is self._lower_graph
            self._merge_nodes_when_width_is_greater_than_w(graph)
            self._delete_merged_nodes(graph)

    def _specific_end_of_construction_function(self) -> None:
        '''
        Removes the nodes left without a root-terminal path after the connection.
        '''
        self._prune_graph()

    def _merge_priority(self, node: 'Node') -> int:
        '''
        Merge priority of a node of the current graph (forward or backward).

        Parameters:
        - node(Node): Node of the last layer.

        Returns:
        - int: The merge priority of the node.
        '''
        if self._is_lower_graph:
            return self._problem.get_backward_priority_for_merge_nodes(node.get_id(), node.state)
        return self._problem.get_priority_for_merge_nodes(node.get_id(), node.state)

    def _merge_states(self, state_one: 'State', state_two: 'State') -> 'State':
        '''
        Merges two states of the current graph (forward or backward).

        Parameters:
        - state_one(State): First state to merge.
        - state_two(State): Second state to merge.

        Returns:
        - State: The merged state.
        '''
        if self._is_lower_graph:
            return self._problem.backward_merge_operator(state_one, state_two)
        return self._problem.merge_operator(state_one, state_two)

    def _merge_nodes_when_width_is_greater_than_w(self, graph: 'Graph') -> None:
        '''
        Merges nodes when the width of the last layer exceeds the specified maximum.

        Parameters:
        - graph: Graph (upper or lower) whose last layer is merged.
        '''
        self._nodes_set: list = []

        for node in graph.structure[-1]:
            heapq.heappush(self._nodes_set, (-self._merge_priority(node), node))

        while len(self._nodes_set) > self._max_width:
            self._reduce_layer_width()

    def _reduce_layer_width(self) -> None:
        '''
        Reduces the layer width by merging the two nodes with the highest priority.
        '''
        node_to_remove: 'Node' = heapq.heappop(self._nodes_set)[1]
        node_to_keep: 'Node' = heapq.heappop(self._nodes_set)[1]

        state_to_remove: str = self._problem.get_state_as_string(node_to_remove.state)
        state_to_keep: str = self._problem.get_state_as_string(node_to_keep.state)

        self._map_of_states.pop(state_to_remove, None)
        self._map_of_states.pop(state_to_keep, None)

        new_state: 'State' = self._merge_states(node_to_remove.state, node_to_keep.state)
        state_as_string: str = self._problem.get_state_as_string(new_state)

        if state_as_string in self._map_of_states:
            exist_node: 'Node' = self._map_of_states[state_as_string]
            self._redirect_arcs(node_to_remove, exist_node)
            self._redirect_arcs(node_to_keep, exist_node)
        else:
            self._redirect_arcs(node_to_remove, node_to_keep)
            node_to_keep.state = new_state
            heapq.heappush(self._nodes_set, (-self._merge_priority(node_to_keep), node_to_keep))
            self._map_of_states[state_as_string] = node_to_keep

    def _redirect_arcs(self, node_to_remove: 'Node', node_to_keep: 'Node') -> None:
        '''
        Moves the arcs that join node_to_remove with the previous layer to node_to_keep: incoming
        arcs in the upper graph, outgoing arcs in the lower graph.

        Parameters:
        - node_to_remove(Node): Node whose arcs are redirected.
        - node_to_keep(Node): Node to which the arcs are redirected.
        '''
        if self._is_lower_graph:
            for arc in node_to_remove.out_arcs:
                arc.parent_node = node_to_keep
                node_to_keep.out_arcs.append(arc)
            node_to_remove.out_arcs = []
        else:
            for arc in node_to_remove.in_arcs:
                arc.child_node = node_to_keep
                node_to_keep.in_arcs.append(arc)
            node_to_remove.in_arcs = []

    def _delete_merged_nodes(self, graph: 'Graph') -> None:
        '''
        Removes from the last layer the nodes left without arcs to the previous layer by the merges.

        Parameters:
        - graph: Graph (upper or lower) whose last layer was merged.
        '''
        layer: list['Node'] = graph.structure[-1]
        if self._is_lower_graph:
            layer[:] = [node for node in layer if node.out_arcs]
        else:
            layer[:] = [node for node in layer if node.in_arcs]
