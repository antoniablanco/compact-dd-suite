#ifndef DD_OPTIMIZATION_PROGRAM_SEQUENCINGPATHSOLVER_H
#define DD_OPTIMIZATION_PROGRAM_SEQUENCINGPATHSOLVER_H

#include "DD.h"
#include "GraphAlgorithms/ShortestLongestPath/PathStructure.h"
#include "SequencingProblem.h"
#include "SequencingState.h"

#include <string>
#include <vector>
#include <limits>
#include <chrono>
#include <cstdint>

using namespace std;

/**
 * @brief Shortest-path solver for Sequencing, drop-in for ShortestLongestPath.
 * Σ w_j C_j is charged per arc as (setup + p[job]) * (W_total - already scheduled);
 * both terms depend on the path. The setup only depends on the last job, so each
 * node keeps one label per last job (see NodeDP::labels); the scheduled weight is a
 * node range and its arcs take the extreme that keeps the bound (relaxed under, the
 * rest over).
 */
class SequencingPathSolver {
public:
    explicit SequencingPathSolver(DD<SequencingState>& dd);

    void set_parameters(const vector<double>& weights, const string& objective);

    PathStructureSolution<SequencingState> solve();

    PathStructureSolution<SequencingState> get_solution() const;
    string get_time() const;

private:
    /// Best cost reaching a node with a given last job, and how to get there.
    struct Label {
        int                     last_job;          // -1 = depot
        double                  cost;
        Arc<SequencingState>*   arc;               // arc reaching the node (nullptr at the root)
        int                     parent_last_job;   // label of the parent the arc comes from
    };

    /// One label per possible last job plus the range its paths span, which prices
    /// the outgoing arcs. The last job prices the setup exactly, so nodes merged by
    /// the reduction (same scheduled set, different last job) stay exact.
    struct NodeDP {
        vector<Label> labels;                // insertion order, at most n + 1
        uint64_t seen_jobs           = 0;   // bit j set if some path here scheduled job j
        int      scheduled_weight_hi = 0;   // largest weight already scheduled among those paths
        int      scheduled_weight_lo = 0;   // smallest weight already scheduled among those paths
        bool     valid               = false;
    };

    Graph<SequencingState>*        graph_;
    const SequencingProblem*       problem_;
    bool                          relaxed_;   // diagram built by a relaxed builder
    string                        objective_;
    PathStructureSolution<SequencingState> solution_;
    chrono::duration<double>      time_;

    void run_dp();
    void initialize_dp_tables(vector<NodeDP>& dp_data);
    void forward_pass(vector<NodeDP>& dp_data, double cost_sign);
    NodeDP describe_node(const Node<SequencingState>* node, const vector<NodeDP>& dp_data,
                         int total_weight) const;
    static const Label* find_label(const NodeDP& node_dp, int last_job);
    void extract_solution(const vector<NodeDP>& dp_data);
    void backtrack_optimal_path(const vector<NodeDP>& dp_data, int terminal_id, int last_job);
};

#endif //DD_OPTIMIZATION_PROGRAM_SEQUENCINGPATHSOLVER_H
