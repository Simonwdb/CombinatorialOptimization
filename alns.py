import copy
import os
import random
import sys

# =============================================================================
# ALNS — "Adaptive Large Neighborhood Search"
#
# Pretend we're playing with a plan of deliveries. The plan is never
# perfect. ALNS plays this little game in a loop:
#
#   1. Take the current plan.
#   2. DESTROY: smash off a few pieces (remove some requests from the plan).
#   3. REPAIR: glue the pieces back on in a different way.
#   4. If the new plan is cheaper, keep it. Otherwise throw it away.
#   5. Repeat many times.
#
# The "destroy" ops live in destroy_operators.py.
# The "repair" ops live in repair_operators.py.
# This file is the referee that keeps score.
# =============================================================================

# Make the Validator folder importable (InstanceCVRPTWUI uses `import baseCVRPTWUI`
# without a package prefix, so the folder must be on sys.path because my computer is broken atm ).
# PLEASE change this so its less messy
VALIDATOR_DIR = os.path.join(os.path.dirname(__file__), "src", "Validator")
if VALIDATOR_DIR not in sys.path:
    sys.path.insert(0, VALIDATOR_DIR)

from src.Validator.FeasibleGreedySolver import FeasibleGreedySolver
from src.Validator.Writer import write_solution
from src.Validator.InstanceCVRPTWUI import InstanceCVRPTWUI
from search_state import build_search_state
from destroy_operators import random_removal, worst_removal
from repair_operators import greedy_repair, random_day_repair, regret2_repair


def _stop_node(instance, stop):
    # 0 in a stop list means "the depot" (home base). Anything else is a
    # request; look up which house it lives at.
    if stop == 0:
        return instance.DepotCoordinate
    return instance.Requests[abs(stop) - 1].node


def _route_distance(instance, stops):
    # Add up the distance for the whole little trip.
    d = 0
    for i in range(len(stops) - 1):
        d += instance.calcDistance[_stop_node(instance, stops[i])][_stop_node(instance, stops[i + 1])]
    return d


def solution_cost(instance, state):
    """
    Calculate how "bad" (expensive) the current plan is. This is the SAME
    formula the official validator uses, so that whatever we minimise here is
    what they grade us on.

      cost = (how many trucks we used at peak)  * VehicleCost
           + (total truck-days across all days) * VehicleDayCost
           + (total kilometres driven)          * DistanceCost
           + for every tool type t:
                (most of tool t needed on any one day) * tool_cost_t

    The first term usually dominates, so shrinking the peak number of trucks
    is the biggest lever we have.
    """
    max_vehicles = 0   # worst day, how many trucks were on the road
    vehicle_days = 0   # total truck-days used over the whole horizon
    distance = 0       # total driving
    for day in state.solution.days:
        n = len(day.routes)
        if n > max_vehicles:
            max_vehicles = n
        vehicle_days += n
        for route in day.routes:
            distance += _route_distance(instance, route.stops)

    # For each tool type, the "peak" = the worst day's usage.
    tool_peaks = [max(state.tool_use[t + 1]) for t in range(len(instance.Tools))]

    cost = (
        max_vehicles * instance.VehicleCost
        + vehicle_days * instance.VehicleDayCost
        + distance * instance.DistanceCost
        + sum(p * instance.Tools[t].cost for t, p in enumerate(tool_peaks))
    )
    return cost, distance, max_vehicles, vehicle_days, tool_peaks


def alns(instance, iterations=200, q=5, seed=0, verbose=True):
    """
    Run the whole ALNS.
      instance   - the puzzle we're solving (tools, houses, days, ...)
      iterations - how many destroy+repair tries we make
      q          - how many requests to rip out each round
      seed       - so we can re-run the same game later
    """
    rng = random.Random(seed)

    # Step 0: build a starting plan with the simple feasible greedy solver.
    solution = FeasibleGreedySolver(instance).solve()
    state = build_search_state(instance, solution)

    best_cost, init_dist, init_v, init_vd, _ = solution_cost(instance, state)
    current_cost = best_cost
    best_state = copy.deepcopy(state)  # remember this in case nothing beats it
    if verbose:
        print(f"init | cost {best_cost:>14d} | dist {init_dist} | vehicles {init_v} | veh-days {init_vd}")

    # Our toolbox of destroy and repair moves. Each round we pick one of each
    # at random. Every lambda is just call the real function with the right
    # extra arguments filled in so we need to add the other destroy and repair ops in here.
    destroy_ops = [
        ("random_removal", lambda inst, s: random_removal(inst, s, q, rng)),
        ("worst_removal",  lambda inst, s: worst_removal(inst, s, q)),
    ]
    repair_ops = [
        ("greedy_repair",     lambda inst, s: greedy_repair(inst, s)),
        ("random_day_repair", lambda inst, s: random_day_repair(inst, s, rng)),
        ("regret2_repair",    lambda inst, s: regret2_repair(inst, s, rng)),
    ]

    # Main loop.
    for it in range(iterations):
        # Make a copy so we can try stuff without wrecking the current plan.
        candidate = copy.deepcopy(state)

        # Pick a random destroy move and a random repair move.
        d_name, d_op = rng.choice(destroy_ops)
        r_name, r_op = rng.choice(repair_ops)
        d_op(instance, candidate)   # rip some requests out
        r_op(instance, candidate)   # try to put them back

        # If any request is still not used after repair, this
        # candidate is broken so throw it away and try again next round.
        if any(not info["scheduled"] for info in candidate.request_state.values()):
            continue

        cand_cost, cand_dist, cand_v, _, _ = solution_cost(instance, candidate)

        # Simple accept rule: only keep the new plan if it's cheaper.
        if cand_cost < current_cost:
            state = candidate
            current_cost = cand_cost
            if cand_cost < best_cost:
                # `candidate` is a fresh deepcopy and nothing else points at
                # it, so we can just hand the reference to `best_state` —
                # no second deepcopy needed.
                best_state = candidate
                best_cost = cand_cost
                if verbose:
                    print(f"iter {it:4d} | {d_name:15s} + {r_name:18s} | cost {cand_cost:>14d} (new best, dist={cand_dist}, veh={cand_v})")

    # Write the best plan we ever saw to disk in the format the validator
    # expects.
    write_solution(best_state.solution, instance, "ALNSSolution.txt")

    final_cost, final_dist, final_v, final_vd, tool_peaks = solution_cost(instance, best_state)
    if verbose:
        print(f"done | cost {final_cost} | dist {final_dist} | vehicles {final_v} | veh-days {final_vd} | tool_peaks {tool_peaks}")

    return best_state, best_cost


if __name__ == "__main__":
    # Pick an instance file to solve, load it, pre-compute the distance
    # table, then run ALNS.
    instance_file = os.path.join(VALIDATOR_DIR, "B1.txt")
    instance = InstanceCVRPTWUI(instance_file, "txt")
    instance.calculateDistances()

    best_state, best_cost = alns(instance, iterations=300, q=10, seed=0)

    print(f"Best cost: {best_cost}")
    print("Solution written to ALNSSolution.txt")
