from abc import ABC, abstractmethod
import math


class AbstractProblem(ABC):
    '''
    This class provides an interface for users to implement their own Problem classes.
    These can be used with the provided DD class to solve decision diagrams.

    *IMPORTANT: Whenever 'state' is mentioned, it must follow the same type as given in initial_state.

    *SEMI DD (sMDD): connection_function is optional, but it must be implemented to build any
    semi decision diagram. backward_transition_function defaults to transition_function.
    '''

    def __init__(self, initial_state: 'State', variables: list[tuple['Variable', 'Domain']], sort: bool = True) -> None:
        '''
        Constructor for the AbstractProblem class.

        Parameters:
        - initial_state (State): The initial state of the problem, which can be a list, int,
        string, etc., depending on what is required for the problem.
        - variables (list[tuple['Variable', 'Domain']]): A list of tuples containing the
        variables of the problem and their domain.
        - sort (bool): Whether to order the variables with sort_variables. The ordering is fixed
        here, before any construction, and cannot be changed afterwards.
        '''
        self.initial_state: 'State' = initial_state
        self.variables_domain: dict[str, list[int]] = dict(variables)

        variable_names: list[str] = [name for name, _ in variables]
        ordered_variables: list[str] = list(self.sort_variables(variables)) if sort else variable_names
        self._check_ordering(ordered_variables, variable_names)

        position_of: dict[str, int] = {name: i for i, name in enumerate(variable_names)}
        self._ordered_variables: list[str] = ordered_variables
        self._dd_to_position: list[int] = [position_of[name] for name in ordered_variables]
        self._dd_to_original_index: list[int] = [
            self.get_original_index(name, position_of[name]) for name in ordered_variables
        ]

        # Bidirectional mapping between variable names and their position index (0-based).
        # Use these instead of parsing names (e.g. int("x_3"[2:]) - 1) anywhere in the code.
        self._name_to_index: dict[str, int] = {name: i for i, name in enumerate(ordered_variables)}
        self._index_to_name: dict[int, str] = {i: name for i, name in enumerate(ordered_variables)}

        self._connect_layer: int = math.ceil(len(variables) / 2)

    @property
    def ordered_variables(self) -> list[str]:
        '''
        Variable names in the order of the DD layers. Fixed at construction.

        Returns:
        - list[str]: The ordered variable names.
        '''
        return self._ordered_variables

    @property
    def name_to_index(self) -> dict[str, int]:
        '''
        Maps each variable name to its position in the DD (0-based). This position is the
        variable_id received by the transition functions. Fixed at construction.

        Returns:
        - dict[str, int]: Variable name to DD position.
        '''
        return self._name_to_index

    @property
    def index_to_name(self) -> dict[int, str]:
        '''
        Maps each DD position (0-based) to its variable name. Fixed at construction.

        Returns:
        - dict[int, str]: DD position to variable name.
        '''
        return self._index_to_name

    @property
    def dd_to_original_index(self) -> list[int]:
        '''
        Maps each DD position to the index of the variable in the original model (e.g. the
        Gurobi model or the objective weights read from the instance). Fixed at construction.

        Returns:
        - list[int]: Original index of the variable in each DD position.
        '''
        return self._dd_to_original_index

    def _check_ordering(self, ordered_variables: list[str], variable_names: list[str]) -> None:
        '''
        Checks that the ordering is a permutation of the variable names.

        Parameters:
        - ordered_variables (list[str]): Ordering returned by sort_variables.
        - variable_names (list[str]): Variable names in the order given to the constructor.
        '''
        if len(ordered_variables) != len(variable_names) or set(ordered_variables) != set(variable_names):
            raise ValueError("sort_variables must return a permutation of the variable names")

    def get_original_index(self, variable_name: str, variable_position: int) -> int:
        '''
        Defines the index of a variable in the original model, used to build dd_to_original_index.
        Defaults to its position in the variables given to the constructor; override it when the
        problem drops variables before calling the constructor (e.g. SOCKnapsack).

        Parameters:
        - variable_name (str): Name of the variable.
        - variable_position (int): Position of the variable in the variables given to the constructor.

        Returns:
        - int: Index of the variable in the original model.
        '''
        return variable_position

    def reorder_to_dd_order(self, values: list) -> list:
        '''
        Reorders a list aligned with the variables given to the constructor into the DD order,
        so that the result can be indexed with the variable_id received by the transition functions.
        Every problem with per-variable data must store it in DD order.

        Parameters:
        - values (list): One value per variable, in the order given to the constructor.

        Returns:
        - list: The same values, one per DD position.
        '''
        return [values[position] for position in self._dd_to_position]

    @property
    def connect_layer(self) -> int:
        '''
        Layer where the upper and lower graphs of a semi decision diagram are connected.
        The connection arcs belong to the variable in position connect_layer (1-based), so they
        go from layer connect_layer - 1 (last upper layer) to layer connect_layer (first lower layer).
        Defaults to ceil(N/2), with N the number of variables.

        Returns:
        - int: The connection layer, in [1, N].
        '''
        return self._connect_layer

    @connect_layer.setter
    def connect_layer(self, layer: int) -> None:
        '''
        Sets the connection layer of the semi decision diagram.

        Parameters:
        - layer (int): The connection layer. Must be an int in [1, N], with N the number of variables.
        '''
        number_of_variables: int = len(self.ordered_variables)
        if not isinstance(layer, int) or isinstance(layer, bool):
            raise TypeError(f"connect_layer must be an int, got {type(layer).__name__}")
        if not 1 <= layer <= number_of_variables:
            raise ValueError(f"connect_layer must be in [1, {number_of_variables}], got {layer}")
        self._connect_layer = layer

    def sort_variables(self, variables: list[tuple['Variable', 'Domain']], **kwargs) -> list[str]:
        '''
        Override to define a custom variable ordering. Called once during __init__, before any
        construction, and must return a permutation of the variable names. It must not have side
        effects: the mappings (name_to_index, dd_to_original_index, ...) are derived from the returned
        ordering, and per-variable data must be reordered after __init__ with reorder_to_dd_order.
        Subclasses may use self attributes set before calling super().__init__ or **kwargs.

        Parameters:
        - variables (list[tuple['Variable', 'Domain']]): The original variable list.
        - **kwargs: Any additional data the subclass needs to compute the ordering.

        Returns:
        - list[str]: Variable names in the desired processing order.
        '''
        return [name for name, _ in variables]

    @abstractmethod
    def transition_function(self, previous_state: 'State', variable_id: int, variable_value: int, scratch_state: list) -> bool:
        '''
        Abstract method to define the transition function.

        Writes the new state into scratch_state[0] and returns True if the transition is feasible.
        scratch_state[0] must not be read on a False return.

        Parameters:
        - previous_state('State'): The previous state. *READ IMPORTANT
        - variable_id(int): The identifier of the variable being modified.
        - variable_value(int): The value of the variable being modified.
        - scratch_state(list): Single-element list used as a scratch buffer; set scratch_state[0] to the new state.

        Returns:
        - bool: True if the new state is feasible, False otherwise.
        '''
        raise NotImplementedError("The method transition_function has not been implemented yet")
    
   
    def get_priority_for_discard_node(self, state: 'State') -> int:
        '''
        Abstract method to define the priority function for discarding nodes, i.e., 
        the node with the highest priority will be discarded first.

        Parameters:
        - state('State'): The state of the node to order. *READ IMPORTANT

        Returns:
        - int: The priority value of the state.
        '''
        raise NotImplementedError("The method get_priority_for_discard_node has not been implemented yet")

   
    def get_priority_for_merge_nodes(self, node_id: int, state: 'State') -> int:
        '''
        Abstract method to define the priority function for merging nodes. 
        After ordering them, the two nodes with the highest priorities will be merged.

        Parameters:
        - node_id(int): The identifier of the node to order.
        - state('State'): The state of the node to order. *READ IMPORTANT

        Returns:
        - int: The priority value of the node.
        '''
        raise NotImplementedError("The method get_priority_for_merge_nodes has not been implemented yet")

    
    def merge_operator(self, state_one: 'State', state_two:'State') -> 'State':
        '''
        Abstract method to define a new state when two nodes are merged.

        Parameters:
        - state_one(State): The first state to merge. *READ IMPORTANT
        - state_two(State): The second state to merge. *READ IMPORTANT

        Returns:
        - State: The resulting state from the merge.
        '''
        raise NotImplementedError("The method merge_operator has not been implemented yet")
    
    @abstractmethod
    def get_state_as_string(self, state: 'State') -> str:
        '''
        Abstract method to define a string representation of the state.

        Parameters:
        - state(State): The state to represent as a string. *READ IMPORTANT

        Returns:
        - str: The string representation of the state.
        '''
        raise NotImplementedError("The method get_state_as_string has not been implemented yet")
    
    @abstractmethod
    def get_state_copy(self, state: 'State') -> 'State':
        '''
        Abstract method to define a copy of a state.

        Parameters:
        - state(State): The state to copy. *READ IMPORTANT

        Returns:
        - State: A copy of the state.
        '''
        raise NotImplementedError("The method get_state_copy has not been implemented yet")
    
    def get_final_state(self) -> 'State':
        '''
        Abstract method to define the final state of the problem.

        Returns:
        - State: The final state of the problem.
        '''
        return self.initial_state

    def get_initial_backward_state(self) -> 'State':
        '''
        Defines the state of the terminal node, where the backward construction of a semi
        decision diagram starts. Defaults to a copy of the initial state; override it when the
        backward pass needs a different starting point. The backward state may carry different
        information than the forward one (e.g. a longer bitarray), as long as get_state_as_string
        and get_state_copy accept it; the backward pass uses its own scratch buffer, built from it.

        Returns:
        - State: The initial backward state of the problem.
        '''
        return self.get_state_copy(self.initial_state)

    def backward_transition_function(self, next_state: 'State', variable_id: int, variable_value: int, scratch_state: list) -> bool:
        '''
        Defines the backward transition function, used to build the lower graph of a semi
        decision diagram from the terminal node upwards. Defaults to transition_function;
        override it when the backward state does not evolve like the forward state.

        Writes the new state into scratch_state[0] and returns True if the transition is feasible.
        scratch_state[0] must not be read on a False return.

        Parameters:
        - next_state('State'): The state of the node in the following layer. *READ IMPORTANT
        - variable_id(int): The identifier of the variable being assigned.
        - variable_value(int): The value of the variable being assigned.
        - scratch_state(list): Single-element list used as a scratch buffer; set scratch_state[0] to the new state.

        Returns:
        - bool: True if the new state is feasible, False otherwise.
        '''
        return self.transition_function(next_state, variable_id, variable_value, scratch_state)

    def connection_function(self, forward_state: 'State', variable_id: int, variable_value: int, backward_state: 'State') -> bool:
        '''
        Defines whether a node of the upper graph can be connected to a node of the lower graph
        through an arc of the connection layer. Required by every semi DD builder.

        For a relaxed sMDD it must be monotone with respect to merge_operator (forward state) and
        backward_merge_operator (backward state): if any of the merged states connects, the merged
        state must connect too.

        Parameters:
        - forward_state('State'): State of the node in the last layer of the upper graph. *READ IMPORTANT
        - variable_id(int): The identifier of the connection variable.
        - variable_value(int): The value of the connection variable.
        - backward_state('State'): State of the node in the first layer of the lower graph. *READ IMPORTANT

        Returns:
        - bool: True if the prefix and suffix can be joined with that value, False otherwise.
        '''
        raise NotImplementedError("The method connection_function has not been implemented yet")

    def get_backward_priority_for_discard_node(self, state: 'State') -> int:
        '''
        Defines the priority for discarding nodes of the lower graph of a restricted semi decision
        diagram. Defaults to get_priority_for_discard_node; override it when that priority is not
        meaningful for the backward state.

        Parameters:
        - state('State'): The backward state of the node to order. *READ IMPORTANT

        Returns:
        - int: The priority value of the state.
        '''
        return self.get_priority_for_discard_node(state)

    def get_backward_priority_for_merge_nodes(self, node_id: int, state: 'State') -> int:
        '''
        Defines the priority for merging nodes of the lower graph of a relaxed semi decision
        diagram. Defaults to get_priority_for_merge_nodes; override it when that priority is not
        meaningful for the backward state.

        Parameters:
        - node_id(int): The identifier of the node to order.
        - state('State'): The backward state of the node to order. *READ IMPORTANT

        Returns:
        - int: The priority value of the node.
        '''
        return self.get_priority_for_merge_nodes(node_id, state)

    def backward_merge_operator(self, state_one: 'State', state_two: 'State') -> 'State':
        '''
        Defines a new backward state when two nodes of the lower graph of a relaxed semi decision
        diagram are merged. Defaults to merge_operator; override it when the backward state does
        not merge like the forward state. The merged state must keep every suffix feasible for any
        of the two states.

        Parameters:
        - state_one(State): The first backward state to merge. *READ IMPORTANT
        - state_two(State): The second backward state to merge. *READ IMPORTANT

        Returns:
        - State: The resulting backward state from the merge.
        '''
        return self.merge_operator(state_one, state_two)
