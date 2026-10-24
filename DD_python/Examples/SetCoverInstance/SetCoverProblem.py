from SourceCode.Problems.AbstractProblemClass import AbstractProblem
from Exceptions.MyExceptions import InfeasibleInstance
from bitarray import bitarray

class SetCoverProblem(AbstractProblem):

    def __init__(self, params: 'SetCoverStructure', sort: bool = True):
        '''
        Initialize the Set Cover Problem instance.

        Parameters:
        - params (SetCoverStructure): Instance of the set cover problem, containing:
            * initial_state: initial bitset state.
            * variables (list[tuple[str, list[int]]]): variable names and their domains.
            * matrix_of_weight (list[list[int]]): coverage matrix (rows=restrictions, cols=variables).
            * right_side_of_restrictions (list[int]): right-hand side of each restriction.
        - sort (bool): whether to sort variables by heuristic order.
        '''
        self._raw_matrix = params.matrix_of_weight
        super().__init__(params.initial_state, params.variables, sort)

        self.right_side_of_restrictions = self.convert_to_bitset(params.right_side_of_restrictions, len(params.matrix_of_weight))

        self.matrix_of_weight = [
            self.convert_to_bitset(self.reorder_to_dd_order(row), len(row))
            for row in params.matrix_of_weight
        ]
        self.matrix_of_weight_transpose = []

        self.check_atributes(params.variables, params.initial_state)
        self.create_transpose_matrix_of_weights(self.matrix_of_weight)
        self.calculate_row_max_index()
        self.calculate_row_min_index()

    def sort_variables(self, variables: list[tuple['Variable', 'Domain']]) -> list[str]:
        n_restrictions = len(self._raw_matrix)
        coverage = [
            sum(self._raw_matrix[row][i] for row in range(n_restrictions))
            for i in range(len(variables))
        ]
        sorted_positions = sorted(range(len(variables)), key=lambda i: -coverage[i])
        return [variables[i][0] for i in sorted_positions]

    def check_atributes(self, variables: list[tuple['Variable', 'Domain']], initial_state: 'State') -> None:
        '''
        Check the attributes of the problem.

        Parameters:
        - variables (list[tuple['Variable', 'Domain']]): List of tuples with the variables and their domains.
        - initial_state ('State'): Initial state of the problem.
        '''
        self.check_same_len_matrix_and_right_side(initial_state)
        self.check_same_len_rows_matrix_and_variables(variables)
        self.check_every_restriction_is_coverable()
    
    def check_same_len_matrix_and_right_side(self, initial_state: 'State') -> None:
        '''
        Check if the matrix of weight and the right side of restrictions have the same length.

        Parameters:
        - initial_state ('State'): Initial state of the problem.
        '''
        assert len(self.matrix_of_weight) == len(self.right_side_of_restrictions), "matrix_of_weight and right_side_of_restrictions must have the same length"
        assert len(initial_state) == len(self.right_side_of_restrictions) or len(initial_state) == 2*len(self.right_side_of_restrictions), "matrix_of_weight and right_side_of_restrictions must have the same length"
    
    def check_same_len_rows_matrix_and_variables(self, variables: list[tuple['Variable', 'Domain']]) -> None:
        '''
        Check if the rows of the matrix of weight and the right side of restrictions have the same length of the variables.

        Parameters:
        - variables (list[tuple['Variable', 'Domain']]): List of tuples with the variables and their domains.
        '''
        for row in range(len(self.matrix_of_weight)):
            assert len(self.matrix_of_weight[row]) == len(variables), "rows of matrix_of_weight and right_side_of_restrictions must have the same length of variables"

    def check_every_restriction_is_coverable(self) -> None:
        '''
        Check that every restriction (row) is covered by at least one variable. Otherwise the
        instance has no feasible solution.
        '''
        uncoverable_rows: list[int] = [row for row, coverage in enumerate(self.matrix_of_weight) if not coverage.any()]
        if uncoverable_rows:
            raise InfeasibleInstance(f"Set cover restrictions {uncoverable_rows} are not covered by any variable")

    def convert_to_bitset(self, vec, size):
        '''
        Convert a vector to a bitarray of a given size.

        Parameters:
        - vec (list[int]): Vector to convert. Values greater than 0 are set to True.
        - size (int): Size of the resulting bitarray.

        Returns:
        - bitarray: Bitarray representation of the vector.
        '''
        bs: bitarray = bitarray(size)
        bs.setall(False)
        for i, value in enumerate(vec):
            if value > 0:
                bs[i] = True
        return bs

    def create_transpose_matrix_of_weights(self, vector_matrix_of_weight: list[list[int]]) -> None:
        '''
        Build the transpose of the weight matrix as a list of bitarrays.

        Parameters:
        - vector_matrix_of_weight (list[list[int]]): Original weight matrix where each row
          represents a restriction and each column represents a variable.
        '''
        rows = len(vector_matrix_of_weight)
        var_num = len(vector_matrix_of_weight[0])

        self.matrix_of_weight_transpose = [bitarray(rows) for i in range(var_num) ]

        for i in range(rows):
            for j in range(var_num):
                if vector_matrix_of_weight[i][j] == 1:
                    self.matrix_of_weight_transpose[j][i] = True
    
    def calculate_row_max_index(self) -> None:
        '''
        Populates self.max_indices, where entry i is the bitarray of the restrictions whose last
        covering variable is at position <= i: once variable i is set to 0, those restrictions can
        no longer be covered by the remaining variables.
        '''
        rows: int = len(self.matrix_of_weight)
        covered_by_suffix: bitarray = bitarray(rows)
        covered_by_suffix.setall(False)
        self.max_indices: list[bitarray] = [None] * len(self.matrix_of_weight_transpose)
        for variable_index in range(len(self.matrix_of_weight_transpose) - 1, -1, -1):
            self.max_indices[variable_index] = ~covered_by_suffix
            covered_by_suffix |= self.matrix_of_weight_transpose[variable_index]

    def calculate_row_min_index(self) -> None:
        '''
        Mirror of calculate_row_max_index for the backward pass of a semi decision diagram.

        Populates self.min_indices, where entry i is the bitarray of the restrictions whose
        first covering variable is at position >= i: once the backward pass skips variable i, those
        restrictions can no longer be covered by the prefix.
        '''
        rows: int = len(self.matrix_of_weight)
        covered_by_prefix: bitarray = bitarray(rows)
        covered_by_prefix.setall(False)
        prefix_covers: list[bitarray] = []
        for column in self.matrix_of_weight_transpose:
            prefix_covers.append(covered_by_prefix.copy())
            covered_by_prefix |= column

        self.min_indices: list[bitarray] = [~prefix_cover for prefix_cover in prefix_covers]

    def transition_function(self, previous_state: 'State', variable_index: int, variable_value: int, scratch_state: list) -> bool:
        if variable_value == 0:
            if (previous_state & self.max_indices[variable_index]).any():
                return False
            scratch_state[0][:] = previous_state
            return True
        scratch_state[0][:] = previous_state
        scratch_state[0] &= ~self.matrix_of_weight_transpose[variable_index]
        return True
    
    def backward_transition_function(self, next_state: 'State', variable_index: int, variable_value: int, scratch_state: list) -> bool:
        if variable_value == 0:
            if (next_state & self.min_indices[variable_index]).any():
                return False
            scratch_state[0][:] = next_state
            return True
        scratch_state[0][:] = next_state
        scratch_state[0] &= ~self.matrix_of_weight_transpose[variable_index]
        return True

    def connection_function(self, forward_state: 'State', variable_index: int, variable_value: int, backward_state: 'State') -> bool:
        '''
        No restriction may stay uncovered by both the prefix (with the connection variable) and the suffix.
        '''
        uncovered: bitarray = forward_state & backward_state
        if variable_value == 1:
            uncovered &= ~self.matrix_of_weight_transpose[variable_index]
        return not uncovered.any()

    def get_priority_for_discard_node(self, state: 'State') -> int:
        '''
        Get the priority for discard a node.

        Parameters:
        - state ('State'): State of the problem.

        Returns:
        - int: Priority for discard the node.
        '''
        return state.count(True)

    def get_backward_priority_for_discard_node(self, state: 'State') -> int:
        '''
        Get the priority for discard a node of the lower graph: the suffixes that cover the most
        restrictions are discarded first. The upper graph keeps the prefixes that cover the most,
        so the lower one keeps the suffixes that leave the most to the prefix (the cheapest ones);
        keeping the ones that cover the most in both halves covers most restrictions twice.

        Parameters:
        - state ('State'): Restrictions not covered by the suffix.

        Returns:
        - int: Priority for discard the node.
        '''
        return -state.count(True)

    def get_priority_for_merge_nodes(self, node_id: int, state: 'State') -> int:
        '''
        Get the priority for merge two nodes.

        Parameters:
        - id (int): Id of the node.

        Returns:
        - int: Priority for merge the nodes.
        '''
        return state.count()

    def get_backward_priority_for_merge_nodes(self, node_id: int, state: 'State') -> int:
        '''
        Get the priority for merge two nodes of the lower graph: the suffixes that cover the most
        restrictions are merged first. Merging the ones that cover the least (the cheapest ones)
        hands them the coverage of the others, and the dual bound falls to the trivial 0.

        Parameters:
        - node_id (int): Id of the node.
        - state ('State'): Restrictions not covered by the suffix.

        Returns:
        - int: Priority for merge the nodes.
        '''
        return -state.count(True)

    def merge_operator(self, state_one: 'State', state_two: 'State') -> 'State':
        '''
        Merge operator of the problem.

        Parameters:
        - state_one ('State'): First state.
        - state_two ('State'): Second state.

        Returns:
        - 'State': Merged state.
        '''
        return state_one & state_two
    
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
        final_state = [0] * len(self.matrix_of_weight)
        return self.convert_to_bitset(final_state, len(self.matrix_of_weight))
