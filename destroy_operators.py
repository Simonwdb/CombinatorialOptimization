import random

def remove_stop_from_day(day, target_stop):
    """
    This function removes a pickup or delivery stops from the routes 
    and it removes the empty routes wherever necessary so everything stays valid. 
    """
    for route in day.routes[:]:
        if target_stop in route.stops:
            route.stops.remove(target_stop) #remove stop from route

            non_depot_stops = [s for s in route.stops if s != 0]
            if len(non_depot_stops) == 0:
                day.routes.remove(route)
            else:
                if route.stops[0] != 0:
                    route.stops.insert(0, 0)
                if route.stops[-1] != 0:
                    route.stops.append(0)
            return True
    return False

def remove_empty_days(solution):
    """
    This function removes days without routes from the solution
    """
    solution.days = [day for day in solution.days if len(day.routes) > 0]

def remove_request(instance, state, request_id):
    """
    This function first removes a delivery stop, then the pickup stop, the tool usage and the request state. 
    So it fully removes a request from the solution.
    """
    info = state.request_state[request_id]
    if not info["scheduled"]:
        return False

    delivery_day = info["delivery_day"]
    pickup_day = info["pickup_day"]

    if delivery_day is None or pickup_day is None:
        raise ValueError(f"Request {request_id} is scheduled partially.")

    delivery_removed = False
    pickup_removed = False

    #Stop removal from routes
    for day in state.solution.days:
        if day.day_number == delivery_day:
            delivery_removed = remove_stop_from_day(day, request_id)
        if day.day_number == pickup_day:
            pickup_removed = remove_stop_from_day(day, -request_id)

    if not delivery_removed:
        raise ValueError(f"Delivery stop for request {request_id} not found.")
    if not pickup_removed:
        raise ValueError(f"Pickup stop for request {request_id} not found.")

    #Tool usage update 
    req = instance.Requests[request_id - 1]

    for d in range(delivery_day, pickup_day + 1):
        state.tool_use[req.tool][d] -= req.toolCount
        if state.tool_use[req.tool][d] < 0:
            raise ValueError(f"Negative tool usage for tool {req.tool} on day {d}" )
   
    #Updates
    state.request_state[request_id]["scheduled"] = False
    state.request_state[request_id]["delivery_day"] = None
    state.request_state[request_id]["pickup_day"] = None

    remove_empty_days(state.solution)
    state.removal_log.append(request_id)
    return True

def random_removal(instance, state, q, rng=None):
    """
    This function randomly removes q requests from the solution.
    """
    #picking a random request to remove
    if rng is None:
        rng = random
    scheduled = [ rid for rid, info in state.request_state.items() if info["scheduled"]]

    if not scheduled:
        return []

    q = min(q, len(scheduled))
    to_remove = rng.sample(scheduled, q)

    for rid in to_remove:
        remove_request(instance, state, rid)

    return to_remove

def worst_removal(instance, state, q):
    """
    This function removes the q requests that contribute the most to the objective value. 
    """
    scheduled = [(rid, info) for rid, info in state.request_state.items() if info["scheduled"]]

    if not scheduled:
        return []

    contributions = []
    for rid, info in scheduled:
        delivery_day = info["delivery_day"]
        pickup_day = info["pickup_day"]

        req = instance.Requests[rid - 1]

        #The contribution to the objective value is based on the amount of tools, distance and the amount of days 
        tool_cost = req.toolCount * instance.Tools[req.tool - 1].cost
        distance_cost = instance.calcDistance[0][req.node] + instance.calcDistance[req.node][0]
        contribution = tool_cost + distance_cost
        contributions.append((rid, contribution))

    #Remove the requests with the highest contribution 
    contributions.sort(key=lambda x: x[1], reverse=True)
    to_remove = [rid for rid, _ in contributions[:q]]

    for rid in to_remove:
        remove_request(instance, state, rid)

    return to_remove




def shaw_relatedness( instance, state, request_id_1, request_id_2, w_distance=1.0, w_time=10.0, w_tool=100.0):
    """
    This function computes the Shaw relatedness score between two requests, the lower the score the more related they are. 
    """
    req1 = instance.Requests[request_id_1 - 1]
    req2 = instance.Requests[request_id_2 - 1]

    distance_score = instance.calcDistance[req1.node][req2.node]

    day1 = state.request_state[request_id_1]["delivery_day"]
    day2 = state.request_state[request_id_2]["delivery_day"]

    if day1 is None:
        day1 = req1.fromDay
    if day2 is None:
        day2 = req2.fromDay

    time_score = abs(day1 - day2)

    if req1.tool == req2.tool:
        tool_score = 0
    else:
        tool_score = 1

    return ((w_distance * distance_score) + (w_time * time_score) + (w_tool * tool_score))


def shaw_removal( instance, state, q, rng=None, randomness_power=6, w_distance=1.0, w_time=10.0, w_tool=100.0):
    """
    This function removes q requests from the solution based on their relatedness. 
    It starts with a random request and then iteratively removes other related requests based on the relatedness score.  
    """
    if rng is None:
        rng = random

    scheduled = [ rid for rid, info in state.request_state.items() if info["scheduled"] ]

    if not scheduled:
        return []

    q = min(q, len(scheduled))

    seed = rng.choice(scheduled)

    removed = [seed]
    remove_request(instance, state, seed)

    while len(removed) < q:
        candidates = [
            rid for rid, info in state.request_state.items()
            if info["scheduled"]]

        if not candidates:
            break

        relatedness_scores = []

        for candidate in candidates:
            best_relatedness = min(
                shaw_relatedness(instance,state, candidate,removed_request,w_distance=w_distance,w_time=w_time,w_tool=w_tool,
    )
                for removed_request in removed
            )

            relatedness_scores.append((candidate, best_relatedness))

        relatedness_scores.sort(key=lambda x: x[1])

        u = rng.random()
        index = int((u ** randomness_power) * len(relatedness_scores))
        index = min(index, len(relatedness_scores) - 1)

        chosen_request = relatedness_scores[index][0]

        remove_request(instance, state, chosen_request)
        removed.append(chosen_request)

    return removed