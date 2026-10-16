
class SemiDDReducer():
    '''
    SourceCode representing the reduction algorithm for a semi decision diagram (sMDD).

    The upper part (layers 1..k-1) is reduced bottom-up, merging nodes with the same set of
    outgoing arcs; the lower part (layers k..N-1) is reduced top-down, merging nodes with the
    same set of incoming arcs. The connection layer stays non-deterministic.
    '''

    def __init__(self, graph: 'Graph', problem: 'AbstractProblem', connect_layer: int) -> None:
        '''
        Constructor for the SemiDDReducer class.

        Parameters:
        - graph (Graph): The semi decision diagram graph to reduce, already joined.
        - problem(AbstractProblem): The problem instance associated with the graph.
        - connect_layer(int): Layer where the graph was connected (first layer of the lower part).
        '''

        self._graph: 'Graph' = graph
        self._problem: 'AbstractProblem' = problem
        self._connect_layer: int = connect_layer

    def reduce_decision_diagram(self, should_visualize: bool) -> 'Graph':
        '''
        Reduces the semi decision diagram graph and returns it.

        Parameters:
        - should_visualize (bool): Indicates whether to visualize the graph during the process.

        Returns:
        - Graph: The reduced semi decision diagram graph.
        '''
        structure: list[list['Node']] = self._graph.structure

        for layer_id in range(self._connect_layer - 1, 0, -1):
            if should_visualize:
                self._print_graph()

            dirty_children: dict = self._merge_nodes_with_same_out_arcs(structure[layer_id])
            for child_node in dirty_children.values():
                child_node.in_arcs[:] = [arc for arc in child_node.in_arcs if arc.parent_node.out_arcs]

        for layer_id in range(self._connect_layer, len(structure) - 1):
            if should_visualize:
                self._print_graph()

            dirty_parents: dict = self._merge_nodes_with_same_in_arcs(structure[layer_id])
            for parent_node in dirty_parents.values():
                parent_node.out_arcs[:] = [arc for arc in parent_node.out_arcs if arc.child_node.in_arcs]

        self._adjust_nodes_id()

        if should_visualize:
            self._print_graph()

        return self._graph

    def _merge_nodes_with_same_out_arcs(self, layer: list['Node']) -> dict:
        '''
        Merges the nodes of an upper layer that reach the same nodes with the same values.
        The incoming arcs of a removed node are redirected to the kept node and its outgoing
        arcs are dropped.

        Parameters:
        - layer: List of nodes in the current layer.

        Returns:
        - dict: Children (by id) that still hold incoming arcs from removed nodes.
        '''
        map_of_paths: dict[frozenset, 'Node'] = {}
        dirty_children: dict[int, 'Node'] = {}
        new_layer: list['Node'] = []

        for node in layer:
            path = frozenset([(arc.variable_value, id(arc.child_node)) for arc in node.out_arcs])
            node_to_keep: 'Node' = map_of_paths.get(path)

            if node_to_keep is None:
                map_of_paths[path] = node
                new_layer.append(node)
            else:
                self._redirect_in_arcs(node, node_to_keep)
                for arc in node.out_arcs:
                    dirty_children[id(arc.child_node)] = arc.child_node
                node.out_arcs.clear()

        if len(new_layer) != len(layer):
            layer[:] = new_layer

        return dirty_children

    def _merge_nodes_with_same_in_arcs(self, layer: list['Node']) -> dict:
        '''
        Merges the nodes of a lower layer that are reached from the same nodes with the same
        values. The outgoing arcs of a removed node are redirected to the kept node and its
        incoming arcs are dropped.

        Parameters:
        - layer: List of nodes in the current layer.

        Returns:
        - dict: Parents (by id) that still hold outgoing arcs to removed nodes.
        '''
        map_of_paths: dict[frozenset, 'Node'] = {}
        dirty_parents: dict[int, 'Node'] = {}
        new_layer: list['Node'] = []

        for node in layer:
            path = frozenset([(arc.variable_value, id(arc.parent_node)) for arc in node.in_arcs])
            node_to_keep: 'Node' = map_of_paths.get(path)

            if node_to_keep is None:
                map_of_paths[path] = node
                new_layer.append(node)
            else:
                self._redirect_out_arcs(node, node_to_keep)
                for arc in node.in_arcs:
                    dirty_parents[id(arc.parent_node)] = arc.parent_node
                node.in_arcs.clear()

        if len(new_layer) != len(layer):
            layer[:] = new_layer

        return dirty_parents

    def _redirect_in_arcs(self, node_to_remove: 'Node', node_to_keep: 'Node') -> None:
        '''
        Redirects the incoming arcs of one node to another node.

        Parameters:
        - node_to_remove: The node whose incoming arcs are redirected.
        - node_to_keep: The node to which the arcs are redirected.
        '''
        for arc in node_to_remove.in_arcs:
            arc.child_node = node_to_keep
            node_to_keep.in_arcs.append(arc)
        node_to_remove.in_arcs.clear()

    def _redirect_out_arcs(self, node_to_remove: 'Node', node_to_keep: 'Node') -> None:
        '''
        Redirects the outgoing arcs of one node to another node.

        Parameters:
        - node_to_remove: The node whose outgoing arcs are redirected.
        - node_to_keep: The node from which the arcs now leave.
        '''
        for arc in node_to_remove.out_arcs:
            arc.parent_node = node_to_keep
            node_to_keep.out_arcs.append(arc)
        node_to_remove.out_arcs.clear()

    def _adjust_nodes_id(self) -> None:
        '''
        Updates the names of the nodes in the graph.
        '''
        initial_node_number: int = 0
        for layer in self._graph.structure:
            for node in layer:
                node.set_id(initial_node_number)
                initial_node_number += 1

    def _print_graph(self) -> None:
        '''
        Prints the content of each layer of the graph.
        '''
        print("")
        variables = self._problem.ordered_variables
        for layer_idx, layer in enumerate(self._graph.structure):
            print("------------------------------------------------------")
            if 0 < layer_idx <= len(variables):
                print(f"[{variables[layer_idx - 1]}]", end="   ")
            for node in layer:
                in_arcs_str = ", ".join(arc.to_string() for arc in node.in_arcs)
                print("u" + node.to_string() + " " + self._problem.get_state_as_string(node.state) + "(" + in_arcs_str + ")", end="   ")
            print("")
