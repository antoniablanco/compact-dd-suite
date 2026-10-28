#include "AbstractProblemClass.h"
#include <algorithm>

template <typename T>
AbstractProblem<T>::AbstractProblem(T* initial_state, const vector<pair<string, vector<int>>> &variables):
        initial_state(initial_state)
{
    get_variables(variables);
}

template <typename T>
void AbstractProblem<T>::get_variables(const vector<pair<std::string, vector<int>>> &variables) {
    for (const auto& [name, domain] : variables) {
        this->variables_domain[name] = domain;
    }
    set_variable_order(variables, AbstractProblem<T>::sort_variables(variables));
}

template <typename T>
void AbstractProblem<T>::initialize_variable_order(const vector<pair<string, vector<int>>>& variables, bool sort) {
    if (_variable_order_initialized) {
        throw logic_error("The variable order is fixed once initialized");
    }

    vector<string> order = sort ? sort_variables(variables) : AbstractProblem<T>::sort_variables(variables);

    vector<string> sorted_order = order;
    vector<string> sorted_names = AbstractProblem<T>::sort_variables(variables);
    std::sort(sorted_order.begin(), sorted_order.end());
    std::sort(sorted_names.begin(), sorted_names.end());
    if (sorted_order != sorted_names) {
        throw invalid_argument("sort_variables must return a permutation of the variable names");
    }

    set_variable_order(variables, order);
    _variable_order_initialized = true;
}

template <typename T>
void AbstractProblem<T>::set_variable_order(const vector<pair<string, vector<int>>>& variables, const vector<string>& order) {
    map<string, int> position_of;
    for (size_t i = 0; i < variables.size(); ++i) {
        position_of[variables[i].first] = static_cast<int>(i);
    }

    _ordered_variables = order;
    _name_to_index.clear();
    _index_to_name.clear();
    _dd_to_position.clear();
    _dd_to_original_index.clear();
    _dd_to_position.reserve(order.size());
    _dd_to_original_index.reserve(order.size());

    for (size_t i = 0; i < order.size(); ++i) {
        int position = position_of.at(order[i]);
        _name_to_index[order[i]] = static_cast<int>(i);
        _index_to_name[static_cast<int>(i)] = order[i];
        _dd_to_position.push_back(position);
        _dd_to_original_index.push_back(get_original_index(order[i], position));
    }
}

template <typename T>
int AbstractProblem<T>::get_original_index(const string& /*variable_name*/, int variable_position) const {
    return variable_position;
}

template <typename T>
template <typename V>
vector<V> AbstractProblem<T>::reorder_to_dd_order(const vector<V>& values) const {
    vector<V> reordered;
    reordered.reserve(_dd_to_position.size());
    for (int position : _dd_to_position) {
        reordered.push_back(values[position]);
    }
    return reordered;
}

template <typename T>
const vector<string>& AbstractProblem<T>::ordered_variables() const {
    return _ordered_variables;
}

template <typename T>
const map<string, int>& AbstractProblem<T>::name_to_index() const {
    return _name_to_index;
}

template <typename T>
const map<int, string>& AbstractProblem<T>::index_to_name() const {
    return _index_to_name;
}

template <typename T>
const vector<int>& AbstractProblem<T>::dd_to_original_index() const {
    return _dd_to_original_index;
}

template <typename T>
bool AbstractProblem<T>::transition_function(const T* previous_state, const int variable_index, int variable_value, T* scratch_state) const {
    throw NotImplementedError("Transition_function");
}

template <typename T>
int AbstractProblem<T>::get_priority_for_discard_node(const T* state) const {
    throw NotImplementedError("Get_priority_for_discard_node");
}

template <typename T>
int AbstractProblem<T>::get_priority_for_merge_nodes(const int node_id, const T* state) const {
    throw NotImplementedError("Get_priority_for_merge_nodes");
}

template <typename T>
T* AbstractProblem<T>::merge_operator(const T*state_one, const T* state_two) const {
    throw NotImplementedError("Merge_operator");
}

template <typename T>
string AbstractProblem<T>::get_state_as_string(const T* state) const {
    throw NotImplementedError("Get_state_as_string");
}

template <typename T>
T* AbstractProblem<T>::get_state_copy(const T* state) const {
    throw NotImplementedError("Get_state_copy");
}

template <typename T>
T* AbstractProblem<T>::get_final_state() {
    return this->initial_state;
}

template <typename T>
vector<string> AbstractProblem<T>::sort_variables(const vector<pair<string, vector<int>>>& variables) {
    vector<string> names;
    names.reserve(variables.size());
    for (const auto& [name, domain] : variables)
        names.push_back(name);
    return names;
}

