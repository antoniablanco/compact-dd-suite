import time
from SourceCode.GraphAlgorithms.ShortestLongestPath.PathStructure import PathStructureSolution


class _NodeDP:
    """Best cost reaching a node for each possible last job (-1 = depot), plus the
    range its paths span for pricing the outgoing arcs: weight already scheduled
    (hi/lo) and jobs seen. The last job prices the setup exactly, so nodes merged by
    the reduction (same scheduled set, different last job) stay exact."""

    __slots__ = ("cost_by_last_job", "scheduled_weight_hi", "scheduled_weight_lo",
                 "seen_jobs")

    def __init__(self, cost_by_last_job, scheduled_weight_hi, scheduled_weight_lo,
                 seen_jobs):
        self.cost_by_last_job = cost_by_last_job
        self.scheduled_weight_hi = scheduled_weight_hi
        self.scheduled_weight_lo = scheduled_weight_lo
        self.seen_jobs = seen_jobs


class SequencingPathSolver:
    """Shortest/longest path solver for Sequencing, drop-in for ShortestLongestPath.
    Σ w_j C_j is charged per arc as (setup + p[job]) * (W_total - already scheduled);
    both terms depend on the path. The setup only depends on the last job, so each
    node keeps one label per last job (`_NodeDP.cost_by_last_job`); the scheduled
    weight is a node range and its arcs take the extreme that keeps the bound
    (relaxed under, the rest over).
    """

    def __init__(self, dd: 'DD'):
        self._graph = dd.get_decision_diagram()
        self._problem = dd.problem
        self._relaxed: bool = dd.get_dd_kind() == 'relaxed'
        self._time: float = 0
        self._solution: PathStructureSolution = PathStructureSolution()
        self._objective: str = ""

    def set_parameters(self, weights: list, objective: str) -> None:
        self._objective = objective

    def get_time(self) -> str:
        return str(self._time)

    def get_solution(self) -> PathStructureSolution:
        return self._solution

    def solve(self) -> PathStructureSolution:
        print("\nStarting the process to solve the shortest or longest path in the graph...")
        start = time.time()
        self._run_dp()
        self._time = time.time() - start
        print("Shortest/longest path algorithm completed.")
        return self._solution

    def _run_dp(self) -> None:
        cost_sign = -1 if self._objective == "max" else 1
        dp_data, dp_arcs = self._initialize_dp_tables()
        self._forward_pass(dp_data, dp_arcs, cost_sign)
        self._extract_solution(dp_data, dp_arcs)

    def _initialize_dp_tables(self):
        total_nodes = self._graph.get_node_count()
        dp_data: list = [None] * total_nodes
        # Per node: last job -> (arc reaching it, last job of the parent label).
        dp_arcs: list = [None] * total_nodes
        root_id = self._graph.structure[0][0].get_id()
        # Nothing is scheduled yet and the previous job is the depot.
        dp_data[root_id] = _NodeDP({-1: 0}, 0, 0, 0)
        dp_arcs[root_id] = {}
        return dp_data, dp_arcs

    def _describe_node(self, incoming, total_weight) -> _NodeDP:
        """Merge into one range everything the incoming paths can look like."""
        node_dp = _NodeDP({}, 0, float("inf"), 0)
        for arc, parent in incoming:
            job_id = arc.variable_value
            job_bit = 1 << job_id
            job_weight = self._problem.weights[job_id]
            node_dp.seen_jobs |= parent.seen_jobs | job_bit
            # A job already seen adds no weight, and the total is capped at W_total.
            node_dp.scheduled_weight_hi = max(
                node_dp.scheduled_weight_hi,
                min(total_weight, parent.scheduled_weight_hi + job_weight))
            node_dp.scheduled_weight_lo = min(
                node_dp.scheduled_weight_lo,
                parent.scheduled_weight_lo
                + (0 if parent.seen_jobs & job_bit else job_weight))
        return node_dp

    def _forward_pass(self, dp_data, dp_arcs, cost_sign) -> None:
        total_weight = sum(self._problem.weights)
        setup_times = self._problem.setup_times
        processing_times = self._problem.processing_times
        maximising = cost_sign < 0
        # Relaxed may not overcharge, the rest may not undercharge; max swaps it.
        charge_most = (self._relaxed == maximising)
        for layer in self._graph.structure[1:]:
            for node in layer:
                node_id = node.get_id()
                incoming = [(arc, dp_data[arc.parent_node.get_id()])
                            for arc in node.in_arcs
                            if dp_data[arc.parent_node.get_id()] is not None]
                if not incoming:
                    continue

                node_dp = self._describe_node(incoming, total_weight)
                cost_by_last_job = node_dp.cost_by_last_job
                best_arcs = {}

                for arc, parent in incoming:
                    job_id = arc.variable_value
                    # (W_total - already_scheduled), taking the end of the range
                    # that keeps the bound.
                    scheduled = parent.scheduled_weight_lo if charge_most \
                        else parent.scheduled_weight_hi
                    remaining_weight = total_weight - scheduled
                    for last_job, parent_cost in parent.cost_by_last_job.items():
                        duration = setup_times[last_job + 1][job_id] + processing_times[job_id]
                        candidate_cost = parent_cost + cost_sign * duration * remaining_weight
                        if candidate_cost < cost_by_last_job.get(job_id, float("inf")):
                            cost_by_last_job[job_id] = candidate_cost
                            best_arcs[job_id] = (arc, last_job)

                dp_data[node_id] = node_dp
                dp_arcs[node_id] = best_arcs

    def _extract_solution(self, dp_data, dp_arcs) -> None:
        terminal_id = self._graph.structure[-1][0].get_id()
        if dp_data[terminal_id] is None:
            # No root-terminal path (e.g. an empty restricted sMDD): same value as ShortestLongestPath.
            self._solution.value = float("-inf") if self._objective == "max" else float("inf")
            self._solution.path_arcs, self._solution.path_print = [], ""
            return
        cost_by_last_job = dp_data[terminal_id].cost_by_last_job
        last_job = min(cost_by_last_job, key=cost_by_last_job.get)
        optimal_cost = cost_by_last_job[last_job]
        if self._objective == "max":
            optimal_cost = -optimal_cost
        self._solution.value = optimal_cost
        self._solution.path_arcs, self._solution.path_print = self._backtrack_optimal_path(dp_arcs, terminal_id, last_job)

    def _backtrack_optimal_path(self, dp_arcs, terminal_id, last_job):
        path_arcs = []
        path_string = ""
        current_id = terminal_id
        while last_job in dp_arcs[current_id]:
            arc, last_job = dp_arcs[current_id][last_job]
            path_string = f"-> {arc.to_string()}" + path_string
            path_arcs.insert(0, arc)
            current_id = arc.parent_node.get_id()
        return path_arcs, path_string[2:]
