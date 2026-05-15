import copy
import math
import os
import random
import sys

from src.Validator.FeasibleGreedySolver import FeasibleGreedySolver

# =============================================================================
# ALNS — "Adaptive Large Neighborhood Search"
#
# Pretend we're playing with a plan of deliveries. The plan is never
# perfect. ALNS plays this little game in a loop:
#
#   1. Take the current plan.
#   2. DESTROY: smash off a few pieces (remove some requests from the plan).
#   3. REPAIR: glue the pieces back on in a different way.
#   4. Decide whether to KEEP the new plan or THROW IT AWAY.
#        * Obvious case: if it's cheaper, keep it.
#        * Less obvious case: sometimes we keep a slightly-worse plan too,
#          so we don't get stuck in a dead end. This trick is called
#          "simulated annealing" and is explained down below.
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
from repair_operators import greedy_repair, random_day_repair, regret2_repair, regret3_repair


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


# =============================================================================
# OPERATOR POOL — the "adaptive" part of adaptive LNS
#
# Think of each destroy op and each repair op as a tool in a toolbox. At the
# start we don't know which tools are good for this puzzle, so we give them
# all an equal chance. But we reward tools that lead to good solutions:
#
#   * found a brand new best plan        -> BIG gold star (SIGMA1)
#   * made the plan cheaper than current -> medium star   (SIGMA2)
#   * new plan was worse but we kept it  -> small star    (SIGMA3)
#   * new plan was trash, we threw away  -> no star
#
# After every SEGMENT_LEN rounds we look at how many stars each tool earned
# and make the good tools a bit more likely to be picked next time. We also
# smooth with REACTION so weights don't flip violently.
#
# To add a new operator later: just call pool.add(name, fn). Done.
# =============================================================================

SIGMA1 = 33   # stars for a new best solution
SIGMA2 = 9    # stars for improving current
SIGMA3 = 13   # stars for accepting a worse plan (means we escaped a dead-end)
REACTION = 0.1  # how fast weights react to new scores (0=never, 1=instantly)
SEGMENT_LEN = 100  # how many iters per learning round


class OperatorPool:
    """
    A bag of (name, function) pairs with weights that update over time.
    Call `add(name, fn)` to register an operator. Call `pick(rng)` to choose
    one weighted by its current score. Call `reward(name, stars)` to tell
    the pool how the last choice worked out. Call `end_segment()` once per
    learning round to recompute weights.
    """

    def __init__(self):
        self._ops = {}       # name -> function
        self._order = []     # name order, so indexing is stable
        self._weight = {}    # name -> current weight (higher = picked more)
        self._score = {}     # name -> stars earned this segment
        self._uses = {}      # name -> times picked this segment

    def add(self, name, fn):
        # Register a new operator. New operators start with weight 1.0 so
        # they immediately get a fair share of tries.
        self._ops[name] = fn
        self._order.append(name)
        self._weight[name] = 1.0
        self._score[name] = 0.0
        self._uses[name] = 0

    def pick(self, rng):
        # Pick one operator, weighted by its current weight.
        names = self._order
        weights = [self._weight[n] for n in names]
        name = rng.choices(names, weights=weights, k=1)[0]
        self._uses[name] += 1
        return name, self._ops[name]

    def reward(self, name, stars):
        # Give this operator some stars for the last time we picked it.
        self._score[name] += stars

    def end_segment(self):
        # Learning step: new_weight = (1-r) * old_weight + r * (stars / uses).
        # Then reset scores & uses so the next segment starts fresh.
        for name in self._order:
            uses = self._uses[name]
            if uses > 0:
                avg = self._score[name] / uses
                self._weight[name] = (1 - REACTION) * self._weight[name] + REACTION * avg
            # If uses==0 we just keep the old weight (no info to learn from).
            # Tiny floor so a bad round can't starve an operator forever.
            if self._weight[name] < 0.05:
                self._weight[name] = 0.05
            self._score[name] = 0.0
            self._uses[name] = 0

    def snapshot(self):
        # Small helper for logging: sorted list of (name, weight).
        return sorted(((n, self._weight[n]) for n in self._order), key=lambda x: -x[1])


def alns(
    instance,
    iterations=200,
    q=5,
    seed=0,
    verbose=True,
    # Simulated-annealing knobs (see the block comment in the loop below):
    start_temp_ratio=0.05,  # T0 chosen so a 5%-worse move has ~50% chance at start
    end_temp=1.0,           # temperature at the final iteration
):
    """
    Run the whole ALNS.
      instance          - the puzzle we're solving (tools, houses, days, ...)
      iterations        - how many destroy+repair tries we make
      q                 - how many requests to rip out each round
      seed              - so we can re-run the same game later
      start_temp_ratio  - controls how "warm" the search starts. Higher means
                          we'll accept bigger cost jumps at the beginning.
      end_temp          - temperature at the last iteration (near-zero means
                          we stop accepting worse moves near the end).
    """
    rng = random.Random(seed)

    # Step 0: build a starting plan. Nearest-neighbour gives us something
    # feasible, then Clark-Wright savings tries to merge routes cheaply.
    solution = FeasibleGreedySolver(instance).solve()
    #solution = SavingsSolver(instance, initialSolution).solve()
    state = build_search_state(instance, solution)

    best_cost, init_dist, init_v, init_vd, _ = solution_cost(instance, state)
    current_cost = best_cost
    best_state = copy.deepcopy(state)  # remember this in case nothing beats it
    if verbose:
        print(f"init | cost {best_cost:>14d} | dist {init_dist} | vehicles {init_v} | veh-days {init_vd}")

    # -------------------------------------------------------------------------
    # Register operators into pools.
    # Adding a new operator later is a one-liner — pools.add("name", lambda ...)
    # -------------------------------------------------------------------------
    destroy_pool = OperatorPool()
    destroy_pool.add("random_removal",  lambda inst, s: random_removal(inst, s, q, rng))
    destroy_pool.add("worst_removal",   lambda inst, s: worst_removal(inst, s, q))

    repair_pool = OperatorPool()
    repair_pool.add("greedy_repair",      lambda inst, s: greedy_repair(inst, s))
    repair_pool.add("random_day_repair",  lambda inst, s: random_day_repair(inst, s, rng))
    repair_pool.add("regret2_repair",     lambda inst, s: regret2_repair(inst, s, rng))
    repair_pool.add("regret3_repair",     lambda inst, s: regret3_repair(inst, s, rng))

    # -------------------------------------------------------------------------
    # Simulated annealing temperature schedule
    #
    # Imagine a hot metal cooling down. When it's hot, its atoms jiggle a lot
    # (we accept big jumps in cost). As it cools, it settles into shape (we
    # only accept small jumps, then nothing).
    #
    # Rule: a worse candidate with cost delta Δ is accepted with probability
    #       p = exp(-Δ / T)
    # We pick a starting T0 so that a move costing `start_temp_ratio * cost`
    # has ~50% acceptance probability at the very beginning, then we
    # geometrically cool T down to `end_temp` by the last iteration.
    # -------------------------------------------------------------------------
    if best_cost > 0 and iterations > 1:
        T = -(start_temp_ratio * best_cost) / math.log(0.5)
        # cooling factor alpha such that T * alpha**(iterations-1) == end_temp
        alpha = (end_temp / T) ** (1.0 / (iterations - 1))
    else:
        T = 1.0
        alpha = 1.0

    if verbose:
        print(f"sa   | T0={T:.2f} alpha={alpha:.6f} end_T={end_temp}")

    # Main loop.
    for it in range(iterations):
        # Make a copy so we can try stuff without wrecking the current plan.
        candidate = copy.deepcopy(state)

        # Pick a destroy and a repair move (weighted random).
        d_name, d_op = destroy_pool.pick(rng)
        r_name, r_op = repair_pool.pick(rng)
        d_op(instance, candidate)   # rip some requests out
        r_op(instance, candidate)   # try to put them back

        # If any request is still not placed, this candidate is broken —
        # throw it away and try again next round. No stars.
        if any(not info["scheduled"] for info in candidate.request_state.values()):
            T *= alpha
            continue

        cand_cost, cand_dist, cand_v, _, _ = solution_cost(instance, candidate)

        # -----------------------------------------------------------------
        # Decide whether to accept this candidate.
        # -----------------------------------------------------------------
        stars = 0
        accepted = False
        if cand_cost < current_cost:
            # It's strictly better — always accept.
            accepted = True
            stars = SIGMA2
            if cand_cost < best_cost:
                # Brand new best ever — accept AND remember.
                best_state = candidate  # candidate is fresh; no extra deepcopy needed
                best_cost = cand_cost
                stars = SIGMA1
                if verbose:
                    print(f"iter {it:5d} | {d_name:15s} + {r_name:18s} | cost {cand_cost:>14d} (new best, dist={cand_dist}, veh={cand_v}) T={T:.1f}")
        else:
            # It's worse. Flip a biased coin using the SA rule.
            delta = cand_cost - current_cost
            accept_prob = math.exp(-delta / T) if T > 1e-9 else 0.0
            if rng.random() < accept_prob:
                accepted = True
                stars = SIGMA3

        if accepted:
            state = candidate
            current_cost = cand_cost

        # Hand out stars to both operators we used.
        destroy_pool.reward(d_name, stars)
        repair_pool.reward(r_name, stars)

        # Cool down a tick.
        T *= alpha

        # End of a learning segment — let each pool update its weights.
        if (it + 1) % SEGMENT_LEN == 0:
            destroy_pool.end_segment()
            repair_pool.end_segment()
            if verbose:
                dw = ", ".join(f"{n}:{w:.2f}" for n, w in destroy_pool.snapshot())
                rw = ", ".join(f"{n}:{w:.2f}" for n, w in repair_pool.snapshot())
                print(f"seg  | iter {it+1:5d} | destroy[{dw}] | repair[{rw}]")

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
    instance_file = os.path.join(VALIDATOR_DIR, "challenge_r10d10_1.txt")
    instance = InstanceCVRPTWUI(instance_file, "txt")
    instance.calculateDistances()

    best_state, best_cost = alns(instance, iterations=10000, q=10, seed=0)

    print(f"Best cost: {best_cost}")
    print("Solution written to ALNSSolution.txt")
