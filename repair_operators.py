import random

def calculate_insertion_cost(instance, route, position, stop_value):
    """
    Calculate the cost (distance increase) of inserting a stop at a specific position in a route.

    Args:
        instance: The problem instance
        route: The route (list of stops)
        position: Position to insert the stop (0 to len(route.stops))
        stop_value: The stop to insert (+request_id or -request_id)

    Returns:
        The increase in route distance
    """
    if position == 0:
        # Insert at beginning (after depot if it exists)
        if route.stops and route.stops[0] == 0:
            # Insert after depot
            prev_stop = 0
            next_stop = route.stops[0] if len(route.stops) > 1 else 0
        else:
            # Insert at very beginning
            prev_stop = 0
            next_stop = route.stops[0] if route.stops else 0
    elif position == len(route.stops):
        # Insert at end (before depot if it exists)
        if route.stops and route.stops[-1] == 0:
            # Insert before depot
            prev_stop = route.stops[-2] if len(route.stops) > 1 else 0
            next_stop = 0
        else:
            # Insert at very end
            prev_stop = route.stops[-1] if route.stops else 0
            next_stop = 0
    else:
        # Insert between existing stops
        prev_stop = route.stops[position - 1]
        next_stop = route.stops[position]

    # Convert stops to node indices
    def stop_to_node(stop):
        if stop == 0:
            return 0  # depot
        else:
            req_id = abs(stop)
            return instance.Requests[req_id - 1].node

    new_node = stop_to_node(stop_value)
    prev_node = stop_to_node(prev_stop)
    next_node = stop_to_node(next_stop)

    # Calculate distance change
    # Remove old distance: prev -> next
    old_distance = instance.calcDistance[prev_node][next_node]
    # Add new distances: prev -> new, new -> next
    new_distance = instance.calcDistance[prev_node][new_node] + instance.calcDistance[new_node][next_node]

    return new_distance - old_distance

def find_feasible_insertions(instance, state, request_id, day_num, stop_value):
    """
    Find all feasible positions to insert a stop (+request_id for delivery, -request_id for pickup)
    in the routes of a given day.

    Returns a list of (route_index, position, cost_increase) tuples.
    """
    day = None
    for d in state.solution.days:
        if d.day_number == day_num:
            day = d
            break

    if not day:
        return []

    feasible_insertions = []
    req = instance.Requests[request_id - 1]

    # Check tool availability for this day
    if stop_value > 0:  # delivery
        if state.tool_use[req.tool][day_num] + req.toolCount > instance.Tools[req.tool - 1].amount:
            return []  # No tool availability
    else:  # pickup - check if tools were used
        if state.tool_use[req.tool][day_num] < req.toolCount:
            return []  # Cannot pickup tools that weren't rented

    # For each route in the day
    for route_idx, route in enumerate(day.routes):
        # Try inserting at each position
        for pos in range(len(route.stops) + 1):
            # Calculate cost increase
            cost_increase = calculate_insertion_cost(instance, route, pos, stop_value)

            # Basic feasibility checks
            # TODO: Add capacity, time window, and other constraints

            feasible_insertions.append((route_idx, pos, cost_increase))

    return feasible_insertions

def insert_request_at_position(state, request_id, day_num, route_idx, position, stop_value):
    """
    Insert a stop (+request_id for delivery, -request_id for pickup) at the specified position.
    Ensures routes maintain proper depot stops.
    """
    day = None
    for d in state.solution.days:
        if d.day_number == day_num:
            day = d
            break

    if not day:
        return False

    route = day.routes[route_idx]
    route.stops.insert(position, stop_value)

    # Ensure route starts and ends with depot if it has non-depot stops
    non_depot_stops = [s for s in route.stops if s != 0]
    if non_depot_stops:
        if route.stops[0] != 0:
            route.stops.insert(0, 0)
        if route.stops[-1] != 0:
            route.stops.append(0)

    return True

def regret2_insertion(instance, state, rng=None):
    """
    Perform regret-2 insertion: for each unscheduled request, calculate insertion costs
    at all feasible positions for both delivery and pickup, compute regret as difference
    between best and second-best cost for each, and insert the request with highest
    total regret first.

    Returns the number of requests inserted.
    """
    if rng is None:
        rng = random

    inserted_count = 0

    while True:
        # Find all unscheduled requests
        unscheduled = [
            rid for rid, info in state.request_state.items()
            if not info["scheduled"]
        ]

        if not unscheduled:
            break

        # Calculate regret for each unscheduled request
        request_regrets = []

        for request_id in unscheduled:
            req = instance.Requests[request_id - 1]

            # Find feasible delivery positions (within pickup window)
            delivery_positions = []
            for day_num in range(req.fromDay, req.toDay + 1):
                positions = find_feasible_insertions(instance, state, request_id, day_num, request_id)
                delivery_positions.extend([(day_num, route_idx, pos, cost) for route_idx, pos, cost in positions])

            # Find feasible pickup positions (from delivery day + numDays onward)
            pickup_positions = []
            for day_num in range(req.fromDay + req.numDays, instance.Days + 1):
                positions = find_feasible_insertions(instance, state, request_id, day_num, -request_id)
                pickup_positions.extend([(day_num, route_idx, pos, cost) for route_idx, pos, cost in positions])

            if not delivery_positions or not pickup_positions:
                continue

            # Sort positions by cost
            delivery_positions.sort(key=lambda x: x[3])
            pickup_positions.sort(key=lambda x: x[3])

            # Calculate regret (second best - best, or just best if only one option)
            delivery_regret = (delivery_positions[1][3] - delivery_positions[0][3]) if len(delivery_positions) > 1 else delivery_positions[0][3]
            pickup_regret = (pickup_positions[1][3] - pickup_positions[0][3]) if len(pickup_positions) > 1 else pickup_positions[0][3]

            total_regret = delivery_regret + pickup_regret

            request_regrets.append((request_id, total_regret, delivery_positions[0], pickup_positions[0]))

        if not request_regrets:
            break

        # Sort by regret (highest first)
        request_regrets.sort(key=lambda x: x[1], reverse=True)

        # Insert the request with highest regret
        request_id, _, best_delivery, best_pickup = request_regrets[0]

        # Ensure delivery is before pickup
        delivery_day, _, _, _ = best_delivery
        pickup_day, _, _, _ = best_pickup

        if delivery_day >= pickup_day:
            continue  # Skip this request for now

        # Insert delivery
        day_num, route_idx, pos, _ = best_delivery
        insert_request_at_position(state, request_id, day_num, route_idx, pos, request_id)

        # Insert pickup
        day_num, route_idx, pos, _ = best_pickup
        insert_request_at_position(state, request_id, day_num, route_idx, pos, -request_id)

        # Update state
        req = instance.Requests[request_id - 1]
        state.request_state[request_id]["scheduled"] = True
        state.request_state[request_id]["delivery_day"] = delivery_day
        state.request_state[request_id]["pickup_day"] = pickup_day

        # Update tool usage for the rental period
        for d in range(delivery_day, pickup_day + 1):
            state.tool_use[req.tool][d] += req.toolCount

        inserted_count += 1

    return inserted_count