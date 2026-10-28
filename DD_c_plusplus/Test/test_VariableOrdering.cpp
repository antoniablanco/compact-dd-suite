#include <gtest/gtest.h>
#include "../../Examples/KnapsackInstance/KnapsackProblem.h"
#include "../../Examples/KnapsackInstance/KnapsackGurobiClass.h"
#include "../../SourceCode/DD.h"
#include "GraphAlgorithms/DDReducer/DDReducer.h"
#include "GraphAlgorithms/ShortestLongestPath/ShortestLongestPath.h"

#include <algorithm>
#include <numeric>
#include <stdexcept>
#include <string>
#include <vector>

using namespace std;


class KnapsackProblemSortedByWeight : public AbstractProblem<int> {
public:
    KnapsackProblemSortedByWeight(const KnapsackInstance& params, bool sort = true)
            : AbstractProblem(params.initial_state, params.variables),
              raw_weights(params.weights),
              capacity(params.right_side_of_restrictions)
    {
        initialize_variable_order(params.variables, sort);
        weights = reorder_to_dd_order(params.weights);
    }

    vector<string> sort_variables(const vector<pair<string, vector<int>>>& variables) override {
        vector<int> positions(variables.size());
        iota(positions.begin(), positions.end(), 0);
        stable_sort(positions.begin(), positions.end(),
            [this](int a, int b) { return raw_weights[a] > raw_weights[b]; });

        vector<string> names;
        for (int position : positions)
            names.push_back(variables[position].first);
        return names;
    }

    void initialize_variable_order_again(const vector<pair<string, vector<int>>>& variables) {
        initialize_variable_order(variables, true);
    }

    bool transition_function(const int* previous_state, const int variable_index, int variable_value, int* scratch_state) const override {
        *scratch_state = *previous_state + weights[variable_index] * variable_value;
        return *scratch_state <= capacity;
    }

    int get_priority_for_discard_node(const int* state) const override { return -*state; }
    int get_priority_for_merge_nodes(const int node_id, const int* state) const override { return -*state; }
    int* merge_operator(const int* state_one, const int* state_two) const override { return new int(min(*state_one, *state_two)); }
    string get_state_as_string(const int* state) const override { return to_string(*state); }
    int* get_state_copy(const int* state) const override { return new int(*state); }
    int* get_final_state() override { return new int(0); }

    vector<int> raw_weights;
    vector<int> weights;
    int capacity;
};


class KnapsackProblemNotPermutation : public AbstractProblem<int> {
public:
    KnapsackProblemNotPermutation(const KnapsackInstance& params) : AbstractProblem(params.initial_state, params.variables) {
        initialize_variable_order(params.variables, true);
    }

    vector<string> sort_variables(const vector<pair<string, vector<int>>>& variables) override {
        vector<string> names;
        for (size_t i = 0; i + 1 < variables.size(); ++i)
            names.push_back(variables[i].first);
        return names;
    }

    bool transition_function(const int*, const int, int, int*) const override { return true; }
    int get_priority_for_discard_node(const int*) const override { return 0; }
    int get_priority_for_merge_nodes(const int, const int*) const override { return 0; }
    int* merge_operator(const int* state_one, const int*) const override { return new int(*state_one); }
    string get_state_as_string(const int* state) const override { return to_string(*state); }
    int* get_state_copy(const int* state) const override { return new int(*state); }
};


class VariableOrderingTest : public ::testing::Test {
protected:
    void SetUp() override {
        variables = {
                make_pair("item_oro", vector<int>{0, 1}),
                make_pair("item_plata", vector<int>{0, 1}),
                make_pair("item_bronce", vector<int>{0, 1}),
                make_pair("item_hierro", vector<int>{0, 1})
        };
        knapsack_params = new KnapsackInstance(new int(0), variables, {3, 3, 4, 6}, vector<double>(objective_weights.begin(), objective_weights.end()), 6);
        problem_instance = new KnapsackProblemSortedByWeight(*knapsack_params);
    }

    void TearDown() override {
        delete problem_instance;
        delete knapsack_params;
    }

    double solve(AbstractProblem<int>& problem) {
        DD<int> dd_instance(problem);
        dd_instance.create_decision_diagram();
        dd_instance.reduce_decision_diagram();

        vector<double> weights;
        for (int weight : problem.reorder_to_dd_order(objective_weights))
            weights.push_back(weight);

        ShortestLongestPath<int> shortest_longest_path_instance(dd_instance);
        shortest_longest_path_instance.set_parameters(weights, "max");
        return shortest_longest_path_instance.solve().value;
    }

    vector<pair<string, vector<int>>> variables;
    vector<int> objective_weights = {-5, 1, 18, 15};
    KnapsackInstance* knapsack_params;
    KnapsackProblemSortedByWeight* problem_instance;
};


TEST_F(VariableOrderingTest, SortedMappings) {
    vector<string> expected_order = {"item_hierro", "item_bronce", "item_oro", "item_plata"};
    ASSERT_EQ(problem_instance->ordered_variables(), expected_order);
    ASSERT_EQ(problem_instance->dd_to_original_index(), (vector<int>{3, 2, 0, 1}));
    ASSERT_EQ(problem_instance->name_to_index().at("item_hierro"), 0);
    ASSERT_EQ(problem_instance->index_to_name().at(2), "item_oro");
    ASSERT_EQ(problem_instance->weights, (vector<int>{6, 4, 3, 3}));
}

TEST_F(VariableOrderingTest, SortedProblemSameSolution) {
    KnapsackProblemSortedByWeight unsorted_problem(*knapsack_params, false);
    ASSERT_EQ(solve(*problem_instance), solve(unsorted_problem));
}

TEST_F(VariableOrderingTest, OrderingCannotChange) {
    ASSERT_THROW(problem_instance->initialize_variable_order_again(variables), logic_error);
}

TEST_F(VariableOrderingTest, SortMustReturnPermutation) {
    ASSERT_THROW(KnapsackProblemNotPermutation problem(*knapsack_params), invalid_argument);
}

TEST_F(VariableOrderingTest, DomainsFollowOrdering) {
    vector<pair<string, vector<int>>> mixed_variables = {
            make_pair("x_1", vector<int>{0, 1}),
            make_pair("x_2", vector<int>{0, 1, 2})
    };
    KnapsackInstance params(new int(0), mixed_variables, {1, 5}, {0, 0}, 20);
    KnapsackProblemSortedByWeight problem(params);
    DD<int> dd_instance(problem);
    dd_instance.create_decision_diagram();

    vector<int> root_values;
    for (Arc<int>* arc : dd_instance.get_decision_diagram()->structure[0].front()->out_arcs)
        root_values.push_back(arc->variable_value);
    sort(root_values.begin(), root_values.end());
    ASSERT_EQ(root_values, (vector<int>{0, 1, 2}));
}

TEST_F(VariableOrderingTest, ReducerIgnoresArcOrder) {
    Node<int>* root = new Node<int>(0, new int(0));
    Node<int>* node_a = new Node<int>(1, new int(1));
    Node<int>* node_b = new Node<int>(2, new int(2));
    Node<int>* terminal = new Node<int>(3, new int(3));

    Graph<int>* graph = new Graph<int>(root);
    graph->add_new_layer();
    graph->add_node(node_a);
    graph->add_node(node_b);
    graph->add_new_layer();
    graph->add_node(terminal);

    vector<tuple<Node<int>*, Node<int>*, int>> arcs = {
            {root, node_a, 0}, {root, node_b, 1},
            {node_a, terminal, 0}, {node_a, terminal, 1},
            {node_b, terminal, 1}, {node_b, terminal, 0}
    };
    for (auto& [parent_node, child_node, value] : arcs) {
        Arc<int>* arc = new Arc<int>(parent_node, child_node, value);
        parent_node->out_arcs.push_back(arc);
        child_node->in_arcs.push_back(arc);
    }

    DDReducer<int>(graph, *problem_instance).reduce_decision_diagram(false);

    vector<size_t> layer_sizes;
    for (auto& layer : graph->structure)
        layer_sizes.push_back(layer.size());
    ASSERT_EQ(layer_sizes, (vector<size_t>{1, 1, 1}));
    delete graph;
}

TEST_F(VariableOrderingTest, GurobiValuesFollowDDOrder) {
    KnapsackGurobiClass gurobi_instance(*knapsack_params, true);
    auto [x_sol_dd, var_ids] = gurobi_instance.get_variable_values({0.1, 0.2, 0.3, 0.4}, problem_instance->dd_to_original_index());
    ASSERT_EQ(var_ids, (vector<int>{3, 2, 0, 1}));
    ASSERT_EQ(x_sol_dd, (vector<double>{0.4, 0.3, 0.1, 0.2}));
}
