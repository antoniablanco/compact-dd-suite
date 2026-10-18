import os
import sys
from bitarray import bitarray

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, os.pardir))
sys.path.append(parent_dir)

from SourceCode.Problems.AbstractProblemClass import AbstractProblem

class IndependentSetProblem(AbstractProblem):

    def __init__(self, params: 'IndependentSetStructure', sort: bool = True) -> None:
        '''
        Initialize the Independent Set Problem instance.

        Parameters:
        - params (IndependentSetStructure): Instance of the independent set problem, containing:
            * initial_state: initial bitset state.
            * variables (list[tuple[str, list[int]]]): variable names and their domains.
            * dict_node_neighbors (dict[str, list[int]]): adjacency list per node.
        - sort (bool): whether to sort variables by heuristic order.
        '''
        self._dict_node_neighbors = params.dict_node_neighbors
        super().__init__(params.initial_state, params.variables, sort)

        n = len(params.dict_node_neighbors)
        self.node_neighbors: list[bitarray] = [bitarray(n) for _ in range(n)]
        for bs in self.node_neighbors:
            bs.setall(False)

        for key, neighbors in params.dict_node_neighbors.items():
            var_index = self.name_to_index[key]
            for neighbor_num in neighbors:
                self.node_neighbors[var_index][self.name_to_index[f"x_{neighbor_num}"]] = True

        self.check_atributes(params.variables, params.dict_node_neighbors)

        # Semi DD: masks used by connection_function, computed for one connection position at a time.
        self._connection_position: int = None
        self._suffix_mask: bitarray = None
        self._prefix_neighbors: list[bitarray] = []


    def sort_variables(self, variables: list[tuple['Variable', 'Domain']]) -> list[str]:
        return sorted(
            [name for name, _ in variables],
            key=lambda name: len(self._dict_node_neighbors[name]),
            reverse=True
        )

    def check_atributes(self, variables: list[tuple['Variable', 'Domain']], dict_node_neighbors: dict[str, list[int]]) -> None:
        ''' 
        Check the attributes of the problem.

        Parameters:
        - variables (list[tuple['Variable', 'Domain']]): List of tuples with the variables and their domains.
        '''
        self.check_same_variables(variables,dict_node_neighbors)
        self.check_neighbors_must_be_integers(dict_node_neighbors)
        self.check_consistent_dictionary_of_neighbors(dict_node_neighbors)

    def check_same_variables(self, variables: list[tuple['Variable', 'Domain']], dict_node_neighbors: dict[str, list[int]]) -> None:
        '''
        Check if the variables are the same between the dictionary of neighbors and the list of variables.

        Parameters:
        - variables (list[tuple['Variable', 'Domain']]): List of tuples with the variables and their domains.
        '''
        assert dict(variables).keys() == dict_node_neighbors.keys(), "Variables must be the same between dictionaries"
    
    def check_neighbors_must_be_integers(self, dict_node_neighbors: dict[str, list[int]]) -> None:
        ''' 
        Check if the neighbors are integers.
        '''
        for key in dict_node_neighbors.keys():
            for value in dict_node_neighbors.get(key, []):
                assert isinstance(value, int), "Values must be integers"
    
    def check_consistent_dictionary_of_neighbors(self, dict_node_neighbors: dict[str, list[int]]) -> None:
        '''
        Check if the dictionary of neighbors is consistent.
        '''
        for key in dict_node_neighbors.keys():
            for value in dict_node_neighbors.get(key, []):
                assert int(key[2:]) in dict_node_neighbors.get("x_"+str(value), []), "Dictionary of neighbors must be consistent"

    def transition_function(self, previous_state: 'State', variable_index: int, variable_value: int, scratch_state: list) -> bool:
        if variable_value == 0:
            scratch_state[0][:] = previous_state
            if previous_state[variable_index]:
                scratch_state[0][variable_index] = False
            return True
        if not previous_state[variable_index]:
            return False
        scratch_state[0][:] = previous_state
        scratch_state[0] &= ~self.node_neighbors[variable_index]
        scratch_state[0][variable_index] = False
        return True

    def connection_function(self, forward_state: 'State', variable_index: int, variable_value: int, backward_state: 'State') -> bool:
        '''
        The backward state mirrors the forward one (default backward transition): the vertices still
        selectable given the suffix. The connection vertex must be selectable from both sides, and there
        is an edge between prefix and suffix iff some suffix vertex blocked by the prefix has all its
        prefix neighbors blocked by the suffix.
        '''
        if variable_value == 1 and not (forward_state[variable_index] and backward_state[variable_index]):
            return False
        if self._connection_position != variable_index:
            self._compute_connection_masks(variable_index)
        prefix_neighbors: list[bitarray] = self._prefix_neighbors
        for vertex in (~forward_state & self._suffix_mask).search(1):
            if not (prefix_neighbors[vertex] & backward_state).any():
                return False
        return True

    def _compute_connection_masks(self, connection_position: int) -> None:
        '''
        Computes the masks for a connection at the given position: the suffix (positions after it) and,
        for every vertex, its neighbors in the prefix (positions before it).

        Parameters:
        - connection_position (int): Position of the connection variable.
        '''
        n: int = len(self.node_neighbors)
        prefix_mask: bitarray = bitarray(n)
        prefix_mask.setall(False)
        prefix_mask[:connection_position] = True
        self._suffix_mask = bitarray(n)
        self._suffix_mask.setall(False)
        self._suffix_mask[connection_position + 1:] = True
        self._prefix_neighbors = [neighbors & prefix_mask for neighbors in self.node_neighbors]
        self._connection_position = connection_position

    def get_priority_for_discard_node(self, state: 'State') -> int:
        '''
        Get the priority for discard a node.

        Parameters:
        - state ('State'): State of the problem.

        Returns:
        - int: Priority for discard the node.
        '''
        return state.count(True)
    
    def get_priority_for_merge_nodes(self, node_id: int, state: 'State') -> int:
        '''
        Get the priority for merge two nodes.

        Parameters:
        - id (int): Id of the node.
        - state ('State'): State of the problem.

        Returns:
        - int: Priority for merge the nodes.
        '''
        return state.count(True)

    def merge_operator(self, state_one: 'State', state_two: 'State') -> 'State':
        '''
        Merge two states.

        Parameters:
        - state_one ('State'): First state.
        - state_two ('State'): Second state.

        Returns:
        - 'State': Merged state.
        '''
        return state_one | state_two
    
    def get_state_as_string(self, state: 'State') -> str:
        '''
        Get the state as a string.

        Parameters:
        - state ('State'): State of a node.

        Returns:
        - str: State as a string.
        '''
        return state.to01()
    
    def get_state_copy(self, state: 'State') -> 'State':
        '''
        Copy of a state.

        Parameters:
        - state(State): The state to copy. *READ IMPORTANT

        Returns:
        - State: A copy of the state.
        '''
        return state.copy()
    
    def get_final_state(self) -> 'State':
        '''
        Final state of the problem.

        Returns:
        - State: The final state of the problem.
        '''
        final_state: list[int] = [0] * len(self.node_neighbors)
        return self.convert_to_bitset(final_state, len(self.node_neighbors))

    def convert_to_bitset(self, vec, size):
        '''
        Convert a list to a bitset.
        '''
        bs: bitarray = bitarray(size)
        bs.setall(False)
        for value in vec:
            if value > 0:
                bs[value - 1] = True
        return bs
