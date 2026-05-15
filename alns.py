import copy
import math
import os
import random
import sys

# Adaptive Large Neighborhood Search for the VeRoLog CVRPTWUI problem.
# Loop: take current solution -> destroy a few requests -> repair them ->
# decide whether to keep the new one (simulated annealing) -> repeat.
# Destroy ops are in destroy_operators.py, repair ops in repair_operators.py.

# Validator folder needs to be on sys.path because InstanceCVRPTWUI does
# `import baseCVRPTWUI` without a package prefix. TODO: fix this properly.
VALIDATOR_DIR = os.path.join(os.path.dirname(__file__), "src", "Validator")
if VALIDATOR_DIR not in sys.path:
    sys.path.insert(0, VALIDATOR_DIR)

from src.Validator.FeasibleGreedySolver import FeasibleGreedySolver
from src.Validator.Writer import write_solution
from src.Validator.InstanceCVRPTWUI import InstanceCVRPTWUI
from search_state import build_search_state
from destroy_operators import random_removal, worst_removal
from repair_operators import greedy_repair, random_day_repair, regret2_repair, regret3_repair


def _stop_node(instance, stop):
    if stop == 0:
        return instance.DepotCoordinate
    return instance.Requests[abs(stop) - 1].node


def _route_distance(instance, stops):
    d = 0
    for i in range(len(stops) - 1):
        d += instance.calcDistance[_stop_node(instance, stops[i])][_stop_node(instance, stops[i + 1])]
    return d


def solution_cost(instance, state):
    """
    Same cost formula the validator uses:
       peak_vehicles * VehicleCost
     + total_vehicle_days * VehicleDayCost
     + total_distance * DistanceCost
     + sum over tools of (peak_usage_of_tool * tool_cost)
    Peak vehicle count usually dominates so that's the biggest lever.
    """
    max_vehicles = 0
    vehicle_days = 0
    distance = 0
    for day in state.solution.days:
        n = len(day.routes)
        if n > max_vehicles:
            max_vehicles = n
        vehicle_days += n
        for route in day.routes:
            distance += _route_distance(instance, route.stops)

    tool_peaks = [max(state.tool_use[t + 1]) for t in range(len(instance.Tools))]

    cost = (
        max_vehicles * instance.VehicleCost
        + vehicle_days * instance.VehicleDayCost
        + distance * instance.DistanceCost
        + sum(p * instance.Tools[t].cost for t, p in enumerate(tool_peaks))
    )
    return cost, distance, max_vehicles, vehicle_days, tool_peaks


# Adaptive operator selection (Ropke & Pisinger style):
# - reward operators that produce good moves
# - update weights each segment with an EMA
# - keep a floor weight so nothing dies completely
SIGMA1 = 33        # new global best
SIGMA2 = 13        # better than current
SIGMA3 = 9         # worse but accepted by SA
REACTION = 0.1     # EMA reaction factor
SEGMENT_LEN = 100  # iterations per learning segment
WEIGHT_FLOOR = 0.2


class OperatorPool:
    """Operators with adaptive weights, picked via roulette wheel."""

    def __init__(self):
        self._ops = {}
        self._order = []
        self._weight = {}
        self._score = {}
        self._uses = {}

    def add(self, name, fn):
        self._ops[name] = fn
        self._order.append(name)
        self._weight[name] = 1.0
        self._score[name] = 0.0
        self._uses[name] = 0

    def pick(self, rng):
        weights = [self._weight[n] for n in self._order]
        name = rng.choices(self._order, weights=weights, k=1)[0]
        self._uses[name] += 1
        return name, self._ops[name]

    def reward(self, name, stars):
        self._score[name] += stars

    def end_segment(self):
        # EMA update: w <- (1-r)*w + r*(score/uses).
        # Then renormalize so the mean weight is 1.0. Without this, when SA
        # cools and almost nothing gets accepted every operator scores ~0,
        # the EMA pulls all weights to the floor and adaptive selection
        # basically becomes uniform random. Renormalising keeps the *ratios*
        # between operators even when the absolute scores collapse.
        for name in self._order:
            uses = self._uses[name]
            if uses > 0:
                avg = self._score[name] / uses
                self._weight[name] = (1 - REACTION) * self._weight[name] + REACTION * avg
            if self._weight[name] < WEIGHT_FLOOR:
                self._weight[name] = WEIGHT_FLOOR
            self._score[name] = 0.0
            self._uses[name] = 0
        total = sum(self._weight[n] for n in self._order)
        if total > 0:
            scale = len(self._order) / total
            for name in self._order:
                self._weight[name] *= scale

    def snapshot(self):
        return sorted(((n, self._weight[n]) for n in self._order), key=lambda x: -x[1])


def alns(
    instance,
    iterations=200,
    q=5,
    seed=0,
    verbose=True,
    start_temp_ratio=0.05,  # at T0 a move costing 5% of init cost has ~50% accept prob
    end_temp=1.0,
):
    rng = random.Random(seed)

    # Initial feasible solution.
    solution = FeasibleGreedySolver(instance).solve()
    state = build_search_state(instance, solution)

    best_cost, init_dist, init_v, init_vd, _ = solution_cost(instance, state)
    current_cost = best_cost
    best_state = copy.deepcopy(state)
    if verbose:
        print(f"init | cost {best_cost:>14d} | dist {init_dist} | vehicles {init_v} | veh-days {init_vd}")

    # Register operators. Add new ones with pool.add(name, fn).
    destroy_pool = OperatorPool()
    destroy_pool.add("random_removal", lambda inst, s: random_removal(inst, s, q, rng))
    destroy_pool.add("worst_removal",  lambda inst, s: worst_removal(inst, s, q))

    repair_pool = OperatorPool()
    repair_pool.add("greedy_repair",     lambda inst, s: greedy_repair(inst, s))
    repair_pool.add("random_day_repair", lambda inst, s: random_day_repair(inst, s, rng))
    repair_pool.add("regret2_repair",    lambda inst, s: regret2_repair(inst, s, rng))
    repair_pool.add("regret3_repair",    lambda inst, s: regret3_repair(inst, s, rng))

    # Simulated annealing: accept worse moves with p = exp(-Δ / T).
    # Pick T0 so a move of `start_temp_ratio * cost` has 50% acceptance,
    # then cool geometrically so T hits `end_temp` at the last iteration.
    if best_cost > 0 and iterations > 1:
        T = -(start_temp_ratio * best_cost) / math.log(0.5)
        alpha = (end_temp / T) ** (1.0 / (iterations - 1))
    else:
        T = 1.0
        alpha = 1.0

    if verbose:
        print(f"sa   | T0={T:.2f} alpha={alpha:.6f} end_T={end_temp}")

    for it in range(iterations):
        candidate = copy.deepcopy(state)

        d_name, d_op = destroy_pool.pick(rng)
        r_name, r_op = repair_pool.pick(rng)
        d_op(instance, candidate)
        r_op(instance, candidate)

        # Repair didn't manage to schedule everything -> throw it away.
        if any(not info["scheduled"] for info in candidate.request_state.values()):
            T *= alpha
            continue

        cand_cost, cand_dist, cand_v, _, _ = solution_cost(instance, candidate)

        stars = 0
        accepted = False
        if cand_cost < current_cost:
            accepted = True
            stars = SIGMA2
            if cand_cost < best_cost:
                best_state = candidate
                best_cost = cand_cost
                stars = SIGMA1
                if verbose:
                    print(f"iter {it:5d} | {d_name:15s} + {r_name:18s} | cost {cand_cost:>14d} (new best, dist={cand_dist}, veh={cand_v}) T={T:.1f}")
        else:
            delta = cand_cost - current_cost
            accept_prob = math.exp(-delta / T) if T > 1e-9 else 0.0
            if rng.random() < accept_prob:
                accepted = True
                stars = SIGMA3

        if accepted:
            state = candidate
            current_cost = cand_cost

        destroy_pool.reward(d_name, stars)
        repair_pool.reward(r_name, stars)

        T *= alpha

        if (it + 1) % SEGMENT_LEN == 0:
            destroy_pool.end_segment()
            repair_pool.end_segment()
            if verbose:
                dw = ", ".join(f"{n}:{w:.2f}" for n, w in destroy_pool.snapshot())
                rw = ", ".join(f"{n}:{w:.2f}" for n, w in repair_pool.snapshot())
                print(f"seg  | iter {it+1:5d} | destroy[{dw}] | repair[{rw}]")

    write_solution(best_state.solution, instance, "ALNSSolution.txt")

    final_cost, final_dist, final_v, final_vd, tool_peaks = solution_cost(instance, best_state)
    if verbose:
        print(f"done | cost {final_cost} | dist {final_dist} | vehicles {final_v} | veh-days {final_vd} | tool_peaks {tool_peaks}")

    return best_state, best_cost


if __name__ == "__main__":
    instance_file = os.path.join(VALIDATOR_DIR, "challenge_r10d10_1.txt")
    instance = InstanceCVRPTWUI(instance_file, "txt")
    instance.calculateDistances()

    best_state, best_cost = alns(instance, iterations=10000, q=10, seed=0)

    print(f"Best cost: {best_cost}")
    print("Solution written to ALNSSolution.txt")
