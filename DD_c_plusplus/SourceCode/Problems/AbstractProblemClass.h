#ifndef TEMPLATETYPE_ABSTRACTPROBLEMCLASS_H
#define TEMPLATETYPE_ABSTRACTPROBLEMCLASS_H

#include <vector>
#include <map>
#include <string>
#include <utility>
#include <stdexcept>

#include "../Exceptions/MyExceptions.h"


using namespace std;

/**
 * @brief Abstract class representing an optimization problem.
 * @tparam T Type of the Node state values
 */
template <typename T> class AbstractProblem {
public:
    /**
     * @brief Constructor for the AbstractProblem class.
     * @param initial_state Initial state of the problem.
     * @param variables Vector of pairs representing the problem variables and their domains.
     */
    AbstractProblem(T* initial_state, const vector<pair<string, vector<int>>>& variables);


    /**
     * @brief Transition function defining how to change from one state to another given a variable and its value.
     * @param previous_state Previous state.
     * @param variable_id Identifier of the variable to change.
     * @param variable_value Value of the variable.
     * @return Pair<T, bool> containing the resulting new state and a feasibility indicator.
     */
    virtual bool transition_function(const T* previous_state, const int variable_index, int variable_value, T* scratch_state) const = 0;

    /**
     * @brief Gets the priority for discarding a node from the decision diagram.
     * @param state State of the node to evaluate.
     * @return int Priority for discarding the node.
     */
    virtual int get_priority_for_discard_node(const T* state) const = 0;

    /**
     * @brief Gets the priority for merging nodes in the decision diagram.
     * @param node_id Identifier of the node to evaluate.
     * @param state State of the node to evaluate.
     * @return int Priority for merging the nodes.
     */
    virtual int get_priority_for_merge_nodes(const int node_id, const T* state) const = 0;

    /**
     * @brief Merge operator that combines two states into one.
     * @param state_one First state to merge.
     * @param state_two Second state to merge.
     * @return T New state resulting from the merge.
     */
    virtual T* merge_operator(const T* state_one, const T* state_two) const = 0;

    /**
    * @brief Gets the state as a string.
    * @return String representation of the state.
    */
    virtual string get_state_as_string(const T* state) const = 0;

    /**
     * @brief Returns the variable names in the desired processing order.
     * Override in derived classes to apply a custom ordering heuristic. It is called once, from
     * initialize_variable_order(), and must return a permutation of the variable names without
     * side effects: per-variable data must be reordered afterwards with reorder_to_dd_order().
     * @param variables Variables as provided to the constructor.
     * @return Variable names in the desired order.
     */
    virtual vector<string> sort_variables(const vector<pair<string, vector<int>>>& variables);

    /**
     * @brief Index of a variable in the original model, used to build dd_to_original_index().
     * Defaults to its position in the variables given to the constructor; override it when the
     * problem drops variables before calling the constructor (e.g. SOCKnapsack).
     * @param variable_name Name of the variable.
     * @param variable_position Position of the variable in the variables given to the constructor.
     * @return Index of the variable in the original model.
     */
    virtual int get_original_index(const string& variable_name, int variable_position) const;

    /**
     * @brief Reorders a vector aligned with the variables given to the constructor into the DD
     * order, so that it can be indexed with the variable_index received by the transition function.
     * @tparam V Type of the per-variable values.
     * @param values One value per variable, in the order given to the constructor.
     * @return The same values, one per DD position.
     */
    template <typename V>
    vector<V> reorder_to_dd_order(const vector<V>& values) const;

    /**
     * @brief Variable names in the order of the DD layers. Fixed once the order is initialized.
     */
    const vector<string>& ordered_variables() const;

    /**
     * @brief Map from variable name to its DD position (the variable_index of the transition function).
     */
    const map<string, int>& name_to_index() const;

    /**
     * @brief Map from DD position to variable name.
     */
    const map<int, string>& index_to_name() const;

    /**
     * @brief Maps each DD position to the index of the variable in the original model.
     */
    const vector<int>& dd_to_original_index() const;

    /**
     * @brief Gets the copy of the state.
     * @return Copy of the state.
     */
    virtual T* get_state_copy(const T* state) const = 0;

    /**
     * @brief Gets the final state of the problem.
     * @return Final state of the problem.
     * @note If not implementend, it will return de initial state.
     */
    virtual T* get_final_state();

    T* initial_state; /**< Initial state of the problem. */
    map<string, vector<int>> variables_domain; /**< Map containing the variables and their domains. */

    /**
     * @brief Destructor for the AbstractProblem class.
     */
    virtual ~AbstractProblem() = default;


protected:
    /**
     * @brief Fixes the variable order: sort_variables() if sort is true, the given order otherwise.
     * Call it once from the derived constructor, before reordering per-variable data; virtual calls
     * resolve to the class being constructed. Without this call the order is the given one.
     * @param variables Variables as provided to the constructor.
     * @param sort Whether to apply sort_variables().
     * @throws invalid_argument If sort_variables() does not return a permutation of the variable names.
     * @throws logic_error If the order was already initialized.
     */
    void initialize_variable_order(const vector<pair<string, vector<int>>>& variables, bool sort);

private:
    /**
     * @brief Gets the variables and their domains from the vector of pairs provided in the constructor.
     * @param variables Vector of pairs representing the problem variables and their domains.
     */
    void get_variables(const vector<pair<string, vector<int>>>& variables);

    /**
     * @brief Builds every ordering map from the given order.
     * @param variables Variables as provided to the constructor.
     * @param order Variable names in DD order.
     */
    void set_variable_order(const vector<pair<string, vector<int>>>& variables, const vector<string>& order);

    vector<string> _ordered_variables; /**< Variable names in DD order. */
    map<string, int> _name_to_index; /**< Variable name to DD position. */
    map<int, string> _index_to_name; /**< DD position to variable name. */
    vector<int> _dd_to_original_index; /**< DD position to index in the original model. */
    vector<int> _dd_to_position; /**< DD position to position in the variables given to the constructor. */
    bool _variable_order_initialized = false; /**< True once initialize_variable_order() ran. */
};
#include "AbstractProblemClass.tpp"
#endif //TEMPLATETYPE_ABSTRACTPROBLEMCLASS_H
