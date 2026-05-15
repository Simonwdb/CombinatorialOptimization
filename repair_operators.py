import random
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src", "Validator"))
from src.Validator.Solution import Day, Route

# REPAIR OPERATORS: the opposite of destroy operators. They take a request that we took out and try to 
# put it back in. ALNS calls these after every destroy step, to try to fix the damage.

def _stop_node(instance, stop):
    if stop == 0:
        return instance.DepotCoordinate
    return instance.Requests[abs(stop) - 1].node


def route_distance(instance, stops):
    """
    Calculates the distance between every pair of neighbouring stops.
    """
    d = 0
    for i in range(len(stops) - 1):
        d += instance.calcDistance[_stop_node(instance, stops[i])][_stop_node(instance, stops[i + 1])]
    return d


def route_is_capacity_feasible(instance, stops):
    """
    Checks if the truck fits everything it needs to carry at any moment on this trip.
    The truck is not allowed to weigh more than the truck's capacity.
    """
   
    load = 0
    for s in stops:
        if s > 0:  
            req = instance.Requests[s - 1]
            load += req.toolCount * instance.Tools[req.tool - 1].weight
    if load > instance.Capacity:
        return False  # if we can't leave the depot

    running = load
    for s in stops:
        if s == 0:
            continue  
        req = instance.Requests[abs(s) - 1]
        w = req.toolCount * instance.Tools[req.tool - 1].weight
        if s > 0:
            running -= w  # dropped a tool off -> truck gets lighter (subtract the weight)
        else:
            running += w  # picked a tool up  -> truck gets heavier (add the weight)
        if running > instance.Capacity:
            return False  # truck is too heavy at some point along the route
    return True


def route_has_depot_bookends(stops):
    non_depot = [s for s in stops if s != 0]  # checks if the route starts and ends at depot.
    if not non_depot:
        return True  # empty trip, nothing to check
    return stops[0] == 0 and stops[-1] == 0


def ensure_depot_bookends(stops):
    non_depot = [s for s in stops if s != 0]
    if not non_depot:
        return stops
    if stops[0] != 0:
        stops.insert(0, 0)
    if stops[-1] != 0:
        stops.append(0)
    return stops


def tool_available_for_rental(instance, state, request_id, delivery_day, pickup_day):
    req = instance.Requests[request_id - 1] 
    limit = instance.Tools[req.tool - 1].amount # total amount of tools available
    for d in range(delivery_day, pickup_day + 1):
        if state.tool_use[req.tool][d] + req.toolCount > limit:
            return False # not enough tools available on day d
    return True

def _best_insertion_in_route(instance, stops, stop_value):
    best_pos = None
    best_delta = None
    old_dist = route_distance(instance, stops)

    for pos in range(1, len(stops)):
        new_stops = stops[:pos] + [stop_value] + stops[pos:]
        if not route_is_capacity_feasible(instance, new_stops):
            continue  # truck would overflow
        new_dist = route_distance(instance, new_stops)
        if new_dist > instance.MaxDistance:
            continue  # trip would be too long
        delta = new_dist - old_dist # how much extra distance this insertion would add
        if best_delta is None or delta < best_delta:
            best_delta = delta
            best_pos = pos 
    return best_pos, best_delta 


def _new_route_cost(instance, stop_value):
    node = _stop_node(instance, stop_value)
    dist = instance.calcDistance[instance.DepotCoordinate][node] + instance.calcDistance[node][instance.DepotCoordinate]
    if dist > instance.MaxDistance:
        return None
    req = instance.Requests[abs(stop_value) - 1]
    w = req.toolCount * instance.Tools[req.tool - 1].weight # weight of the tools for this request
    if w > instance.Capacity:
        return None 
    return dist 


def _get_or_create_day(state, day_num):
    for d in state.solution.days:
        if d.day_number == day_num:
            return d
    day = Day(day_num)
    state.solution.days.append(day)
    return day


def _insert_stop(state, day_num, stop_value):
    day = _get_or_create_day(state, day_num)

    # (1) Find the best existing trip to slot into.
    best_route_idx = None
    best_pos = None
    best_delta = None
    for idx, route in enumerate(day.routes):
        pos, delta = _best_insertion_in_route(state._instance, route.stops, stop_value)
        if pos is None:
            continue
        if best_delta is None or delta < best_delta:
            best_delta = delta
            best_pos = pos
            best_route_idx = idx

    # (2) How expensive would a new route be?
    new_route_delta = _new_route_cost(state._instance, stop_value)

    # (3) Prefer reusing an existing trip if it's at least as cheap.
    if best_delta is not None and (new_route_delta is None or best_delta <= new_route_delta):
        day.routes[best_route_idx].stops.insert(best_pos, stop_value)
        return best_delta

    if new_route_delta is not None:
        r = Route()
        r.stops = [0, stop_value, 0] 
        day.routes.append(r)
        return new_route_delta

    return None  # nowhere feasible to put it

def _apply_request_insertion(instance, state, rid, delivery_day, pickup_day):
    state._instance = instance 

    # Drop-off first
    delta_d = _insert_stop(state, delivery_day, rid)
    if delta_d is None:
        return False 

    # Then the pick-up
    delta_p = _insert_stop(state, pickup_day, -rid)
    if delta_p is None:
        _remove_stop_internal(state, delivery_day, rid)  # undo the drop-off
        return False

    req = instance.Requests[rid - 1]
    for d in range(delivery_day, pickup_day + 1):
        state.tool_use[req.tool][d] += req.toolCount
    state.request_state[rid]["scheduled"] = True
    state.request_state[rid]["delivery_day"] = delivery_day
    state.request_state[rid]["pickup_day"] = pickup_day
    return True


def _remove_stop_internal(state, day_num, stop_value):
    for day in state.solution.days:
        if day.day_number != day_num:
            continue
        for route in day.routes[:]:
            if stop_value in route.stops:
                route.stops.remove(stop_value)
                non_depot = [s for s in route.stops if s != 0]
                if not non_depot:
                    day.routes.remove(route)  # trip became empty -> drop it
                else:
                    ensure_depot_bookends(route.stops)
                return True
    return False


def _feasible_day_windows(instance, req):
    """
    Every legal (delivery, pickup) pair.
    """
    for d in range(req.fromDay, req.toDay + 1):
        p = d + req.numDays
        if p > instance.Days + 1:
            break 
        yield d, p

# ---------------------------------------------------------------------------
# The actual repair operators that ALNS calls.
# ---------------------------------------------------------------------------

def greedy_repair(instance, state):
    """
    For each request that is not yet scheduled, scan its allowed days from earliest to latest 
    and drop it into the cheapest feasible spot on the first day where the tool inventory is available.
    """
    inserted = 0
    for rid in list(state.request_state.keys()):
        if state.request_state[rid]["scheduled"]:
            continue
        for d, p in _feasible_day_windows(instance, instance.Requests[rid - 1]):
            if not tool_available_for_rental(instance, state, rid, d, p):
                continue
            if _apply_request_insertion(instance, state, rid, d, p):
                inserted += 1
                break  
    state.solution.days.sort(key=lambda x: x.day_number)
    return inserted


def random_day_repair(instance, state, rng=None):
    """
    Same idea as greedy_repair but we shuffle the order of the requests AND the order of candidate days. 
    That way ALNS explores different shapes of solution instead of always landing on the same greedy plan.
    """
    if rng is None:
        rng = random

    inserted = 0
    rids = [rid for rid, info in state.request_state.items() if not info["scheduled"]]
    rng.shuffle(rids)

    for rid in rids:
        req = instance.Requests[rid - 1]
        candidates = list(_feasible_day_windows(instance, req))
        rng.shuffle(candidates)
        for d, p in candidates:
            if not tool_available_for_rental(instance, state, rid, d, p):
                continue
            if _apply_request_insertion(instance, state, rid, d, p):
                inserted += 1
                break
    state.solution.days.sort(key=lambda x: x.day_number)
    return inserted


def regret2_repair(instance, state, rng=None):
    """
    Regret-2 repair — a little smarter than pure greedy.

    The idea: some requests only have ONE nice day to be placed. If we wait
    too long, something else takes that slot and we regret it. So on every
    step we:
      1. Look at each un-placed request.
      2. Score each of its legal (delivery, pickup) days by how cheap it is.
      3. Work out the "regret": (cost of 2nd-best day) - (cost of best day).
      4. Place the request with the biggest regret FIRST, at its best spot.
    Repeat until every request is placed (or nothing feasible remains).
    """
    if rng is None:
        rng = random

    inserted = 0
    while True:
        unscheduled = [rid for rid, info in state.request_state.items() if not info["scheduled"]]
        if not unscheduled:
            break  

        best_rid = None
        best_regret = None
        best_choice = None  

        for rid in unscheduled:
            req = instance.Requests[rid - 1]
            options = []
            for d, p in _feasible_day_windows(instance, req):
                if not tool_available_for_rental(instance, state, rid, d, p):
                    continue
                cost_d = _estimate_insertion_cost(instance, state, d, rid)
                cost_p = _estimate_insertion_cost(instance, state, p, -rid)
                if cost_d is None or cost_p is None:
                    continue
                options.append((cost_d + cost_p, d, p))
            if not options:
                continue
            options.sort(key=lambda x: x[0])  
            best = options[0][0]
            # If there is no "second best", pretend the regret is tiny.
            second = options[1][0] if len(options) > 1 else best + 1
            regret = second - best
            # Pick the request with the biggest regret; ties break by cheapest.
            if (best_regret is None
                or regret > best_regret
                or (regret == best_regret and options[0][0] < best_choice[0])):
                best_regret = regret
                best_rid = rid
                best_choice = (options[0][0], options[0][1], options[0][2])

        if best_rid is None:
            break  

        _, d, p = best_choice
        if _apply_request_insertion(instance, state, best_rid, d, p):
            inserted += 1
        else:
            break

    state.solution.days.sort(key=lambda x: x.day_number)
    return inserted


def regret3_repair(instance, state, rng=None):
    """
    Regret-3 repair — similar to regret-2 but considers the third-best option.
    The idea: prioritize requests where the difference between the best and third-best insertion cost 
    is large, indicating higher opportunity cost of not placing it optimally.
    """
    if rng is None:
        rng = random

    inserted = 0
    while True:
        unscheduled = [rid for rid, info in state.request_state.items() if not info["scheduled"]]
        if not unscheduled:
            break 

        best_rid = None
        best_regret = None
        best_choice = None 

        for rid in unscheduled:
            req = instance.Requests[rid - 1]
        
            options = []
            for d, p in _feasible_day_windows(instance, req):
                if not tool_available_for_rental(instance, state, rid, d, p):
                    continue
                cost_d = _estimate_insertion_cost(instance, state, d, rid)
                cost_p = _estimate_insertion_cost(instance, state, p, -rid)
                if cost_d is None or cost_p is None:
                    continue
                options.append((cost_d + cost_p, d, p))
            if not options:
                continue
            options.sort(key=lambda x: x[0])  
            best = options[0][0]
            # Regret-3: difference between third-best and best
            if len(options) >= 3:
                third = options[2][0]
            elif len(options) == 2:
                third = options[1][0]  # fallback to regret-2
            else:
                third = best + 1  # small regret if only one option
            regret = third - best
            # Pick the request with the biggest regret; ties break by cheapest.
            if (best_regret is None
                or regret > best_regret
                or (regret == best_regret and options[0][0] < best_choice[0])):
                best_regret = regret
                best_rid = rid
                best_choice = (options[0][0], options[0][1], options[0][2])

        if best_rid is None:
            break  # none of the remaining requests can be placed

        _, d, p = best_choice
        if _apply_request_insertion(instance, state, best_rid, d, p):
            inserted += 1
        else:
            break

    state.solution.days.sort(key=lambda x: x.day_number)
    return inserted


def _estimate_insertion_cost(instance, state, day_num, stop_value):
    """
    The cheapest way to add this stop on this day. Returns the extra distance it would add, 
    or None if it's not feasible.
    """
    day = None
    for d in state.solution.days:
        if d.day_number == day_num:
            day = d
            break

    candidates = []
    if day is not None:
        state._instance = instance
        for route in day.routes:
            _, delta = _best_insertion_in_route(instance, route.stops, stop_value)
            if delta is not None:
                candidates.append(delta)

    nr = _new_route_cost(instance, stop_value)
    if nr is not None:
        candidates.append(nr)

    return min(candidates) if candidates else None
