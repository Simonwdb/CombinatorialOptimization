import random

def remove_stop_from_day(day, target_stop):
    """
    This function removes a specific stop (either pickup or delivery) from the routes of a given day.
    It also ensures that the routes remain valid by removing empty routes and adding depot stops if necessary.

    Returns:
        True if removed, False otherwise.
    """
    for route in day.routes[:]:
        if target_stop in route.stops:
            route.stops.remove(target_stop)

            #remove empty or trivial routes
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
    This one removes any days from the solution that have no routes, which can happen after removing requests.
    """
    solution.days = [day for day in solution.days if len(day.routes) > 0]



def remove_request(instance, state, request_id):
    """
    Takes in a request ID and uses build_search_state to find the delivery and pickup days for that request, then it removes...
    - delivery stop (+request_id)
    - pickup stop (-request_id)
    - tool usage from delivery_day to pickup_day inclusive
    - request_state bookkeeping

    Returns:
        True if request was removed, False if it was not scheduled.
    """
    info = state.request_state[request_id]

    if not info["scheduled"]:
        return False

    delivery_day = info["delivery_day"]
    pickup_day = info["pickup_day"]

    if delivery_day is None or pickup_day is None:
        raise ValueError(f"Request {request_id} is partially scheduled.")

    delivery_removed = False
    pickup_removed = False

    # Remove stops from routes
    for day in state.solution.days:
        if day.day_number == delivery_day:
            delivery_removed = remove_stop_from_day(day, request_id)
        if day.day_number == pickup_day:
            pickup_removed = remove_stop_from_day(day, -request_id)

    if not delivery_removed:
        raise ValueError(f"Delivery stop for request {request_id} not found.")
    if not pickup_removed:
        raise ValueError(f"Pickup stop for request {request_id} not found.")

    # Update tool usage
    req = instance.Requests[request_id - 1]

    for d in range(delivery_day, pickup_day + 1):
        state.tool_use[req.tool][d] -= req.toolCount

        if state.tool_use[req.tool][d] < 0:
            raise ValueError(
                f"Negative tool usage for tool {req.tool} on day {d}"
            )

    # Update request state
    state.request_state[request_id]["scheduled"] = False
    state.request_state[request_id]["delivery_day"] = None
    state.request_state[request_id]["pickup_day"] = None

    # Clean up empty days
    remove_empty_days(state.solution)
    state.removal_log.append(request_id)

    return True




def random_removal(instance, state, q, rng=None):
    """
    Randomly remove q scheduled requests.

    Returns:
        list of removed request IDs
    """
    if rng is None:
        rng = random

    scheduled = [
        rid for rid, info in state.request_state.items()#rid is request ID, info is the dict with scheduled, delivery_day, pickup_day
        if info["scheduled"]
    ]

    if not scheduled:
        return []

    q = min(q, len(scheduled))

    to_remove = rng.sample(scheduled, q)

    for rid in to_remove:
        remove_request(instance, state, rid)

    return to_remove

def worst_removal(instance, state, q):
    """
    Remove the q requests that contribute most to the current cost.

    Returns:
        list of removed request IDs
    """
    scheduled = [
        (rid, info) for rid, info in state.request_state.items()
        if info["scheduled"]
    ]

    if not scheduled:
        return []

    # Calculate contribution to cost for each scheduled request
    contributions = []
    for rid, info in scheduled:
        delivery_day = info["delivery_day"]
        pickup_day = info["pickup_day"]

        req = instance.Requests[rid - 1]

        # ?? the contribution to the objective value will be the tool cost * how many tools + distance of specific route?? 
        tool_cost = req.toolCount * instance.Tools[req.tool - 1].cost
        distance_cost = instance.distance(0, rid) + instance.distance(rid, 0)  # depot to delivery and back
        contribution = tool_cost + distance_cost
        contributions.append((rid, contribution))

    # Sort by contribution and select top q
    contributions.sort(key=lambda x: x[1], reverse=True)
    to_remove = [rid for rid, _ in contributions[:q]]

    for rid in to_remove:
        remove_request(instance, state, rid)

    return to_remove