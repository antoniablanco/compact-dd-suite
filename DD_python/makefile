# ── Testing ───────────────────────────────────────────────────────────────────

.PHONY: test pytest coverage report html \
        main_knapsack main_independent_set main_set_cover main_socknapsack main_sequencing \
        gurobi_knapsack gurobi_independent_set gurobi_set_cover gurobi_socknapsack gurobi_sequencing \
        cuts_knapsack cuts_independent_set cuts_set_cover cuts_socknapsack cuts_sequencing \
        main_knapsack_semi main_independent_set_semi main_set_cover_semi main_socknapsack_semi main_sequencing_semi \
        cuts_knapsack_semi \
        main_knapsack_semi_restricted main_independent_set_semi_restricted main_set_cover_semi_restricted main_socknapsack_semi_restricted main_sequencing_semi_restricted \
        main_knapsack_semi_relax main_independent_set_semi_relax main_set_cover_semi_relax main_socknapsack_semi_relax main_sequencing_semi_relax

test:
	python -m unittest discover -v -s ./Test -p "test_*.py" -b

pytest:
	pytest ./Test -v

coverage:
	coverage run -m unittest discover -s ./Test -p "test_*.py"

report:
	coverage report -m

html:
	coverage html


# ── main.py ───────────────────────────────────────────────────────────────────

main_knapsack:
	python main.py ../DataInstances/Knapsack/Standard/f4_l-d_kp_4_11.txt -Knapsack -Exact -Output_results.csv -Max -Export

main_independent_set:
	python main.py ../DataInstances/IndependentSet/Custom/independent_set_instance_v5_d3_seed2.txt -IndependentSet -Restricted -Output_results.csv -Max -Width_4 -Reduce -NoSort -Export

main_set_cover:
	python main.py ../DataInstances/SetCover/Custom/set_cover_v6_r3_seed1.txt -SetCover -Exact -Output_results.csv -Min -Width_20000 -NoSort -Export 

main_socknapsack:
	python main.py ../DataInstances/SOCKnapsack/knapsack_n5m2o1b5_1.txt -SOCKnapsack -Exact -Output_results.csv -Max -Width_20 -Export 

main_sequencing:
	python main.py ../DataInstances/Sequencing/Custom/sequencing_n3_s100_seed2.txt -Sequencing -Exact -Output_results.csv -Min -Export -Verbose


# ── main_gurobi.py ────────────────────────────────────────────────────────────

gurobi_knapsack:
	python main_gurobi.py ../DataInstances/Knapsack/Custom/knapsack_instance_v4_d4_seed1.txt -Knapsack -Output_resultsGurobi.csv

gurobi_independent_set:
	python main_gurobi.py ../DataInstances/IndependentSet/Custom/independent_set_instance_v5_d3_seed2.txt -IndependentSet -Output_resultsGurobi.csv

gurobi_set_cover:
	python main_gurobi.py ../DataInstances/SetCover/Custom/set_cover_v6_r3_seed1.txt -SetCover -Output_resultsGurobi.csv

gurobi_socknapsack:
	python main_gurobi.py ../DataInstances/SOCKnapsack/knapsack_n5m2o1b5_1.txt -SOCKnapsack -Output_resultsGurobiSock.csv

gurobi_sequencing:
	python main_gurobi.py ../DataInstances/Sequencing/Custom/sequencing_n5_s025_seed1.txt -Sequencing


# ── main_cuts.py ──────────────────────────────────────────────────────────────

cuts_knapsack:
	python main_cuts.py ../DataInstances/Knapsack/Custom/knapsack_instance_v4_d4_seed1.txt -Knapsack -JointFlowCuts -Verbose -Strength -Output_resultCuts.csv -Continuous

cuts_independent_set:
	python main_cuts.py ../DataInstances/IndependentSet/Custom/independent_set_instance_v5_d3_seed2.txt -IndependentSet -FlowCuts -Verbose -Strength -Output_resultCuts.csv -Continuous

cuts_set_cover:
	python main_cuts.py ../DataInstances/SetCover/Custom/set_cover_v50_r30_seed1.txt -SetCover -TargetCuts -Verbose -Strength -Output_resultCuts.csv -Continuous

cuts_socknapsack:
	python main_cuts.py ../DataInstances/SOCKnapsack/knapsack_n5m2o1b5_1.txt -SOCKnapsack -JointFlowCuts -Verbose -Strength -Output_resultCutsSock.csv -Continuous

cuts_sequencing:
	python main_cuts.py ../DataInstances/Sequencing/Custom/sequencing_n5_s025_seed1.txt -Sequencing -TargetCuts -Verbose -Output_resultCuts.csv -Continuous


# ── sMDD (semi) ───────────────────────────────────────────────────────────────
# Construcción exacta del sMDD (-Exact -Semi). Sin -ConnectLayer_<k> se usa el default ceil(N/2).

main_knapsack_semi:
	python main.py ../DataInstances/Knapsack/Standard/f4_l-d_kp_4_11.txt -Knapsack -Exact -Semi -ConnectLayer_3 -Output_results_semi.csv -Max -Export

main_independent_set_semi:
	python main.py ../DataInstances/IndependentSet/Custom/independent_set_instance_v5_d3_seed2.txt -IndependentSet -Exact -Semi -Output_results_semi.csv -Max -Reduce -Export

main_set_cover_semi:
	python main.py ../DataInstances/SetCover/Custom/set_cover_v6_r3_seed1.txt -SetCover -Exact -Semi -Output_results_semi.csv -Min -Export -Reduce

main_socknapsack_semi:
	python main.py ../DataInstances/SOCKnapsack/knapsack_n5m2o1b5_1.txt -SOCKnapsack -Exact -Semi -Output_results_semi.csv -Max -Export -Reduce

main_sequencing_semi:
	python main.py ../DataInstances/Sequencing/Custom/sequencing_n3_s100_seed2.txt -Sequencing -Exact -Semi -Output_results_semi.csv -Min -Export

# sMDD restringido (-Restricted -Semi): mismo ancho en el grafo superior e inferior.

main_knapsack_semi_restricted:
	python main.py ../DataInstances/Knapsack/Standard/f1_l-d_kp_10_269.txt -Knapsack -Restricted -Width_4 -Semi -Output_results_semi.csv -Max -Export

main_independent_set_semi_restricted:
	python main.py ../DataInstances/IndependentSet/Custom/independent_set_instance_v5_d3_seed2.txt -IndependentSet -Restricted -Width_4 -Semi -Output_results_semi.csv -Max -Export

main_set_cover_semi_restricted:
	python main.py ../DataInstances/SetCover/Custom/set_cover_v6_r3_seed1.txt -SetCover -Restricted -Width_2 -Semi -Output_results_semi.csv -Min -Export

main_socknapsack_semi_restricted:
	python main.py ../DataInstances/SOCKnapsack/knapsack_n5m2o5b5_2.txt -SOCKnapsack -Restricted -Width_2 -Semi -Output_results_semi.csv -Max -Export

main_sequencing_semi_restricted:
	python main.py ../DataInstances/Sequencing/Custom/sequencing_n10_s025_seed1.txt -Sequencing -Restricted -Width_4 -Semi -Output_results_semi.csv -Min -Export

# sMDD relajado (-RelaxPriority -Semi): mismo ancho en el grafo superior e inferior.

main_knapsack_semi_relax:
	python main.py ../DataInstances/Knapsack/Standard/f1_l-d_kp_10_269.txt -Knapsack -RelaxPriority -Width_4 -Semi -Output_results_semi.csv -Max -Export

main_independent_set_semi_relax:
	python main.py ../DataInstances/IndependentSet/Custom/independent_set_instance_v5_d3_seed2.txt -IndependentSet -RelaxPriority -Width_4 -Semi -Output_results_semi.csv -Max -Export

main_set_cover_semi_relax:
	python main.py ../DataInstances/SetCover/Custom/set_cover_v6_r3_seed1.txt -SetCover -RelaxPriority -Width_2 -Semi -Output_results_semi.csv -Min -Export

main_socknapsack_semi_relax:
	python main.py ../DataInstances/SOCKnapsack/knapsack_n5m2o5b5_2.txt -SOCKnapsack -RelaxPriority -Width_2 -Semi -Output_results_semi.csv -Max -Export

main_sequencing_semi_relax:
	python main.py ../DataInstances/Sequencing/Custom/sequencing_n10_s025_seed1.txt -Sequencing -RelaxPriority -Width_4 -Semi -Output_results_semi.csv -Min -Export

