from src.Validator.Solution import Day, Route


def _get_or_create_day(solution, day_number):
    for day in solution.days:
        if day.day_number == day_number:
            return day

    day = Day(day_number)
    solution.days.append(day)
    solution.days.sort(key=lambda d: d.day_number)
    return day


def _can_schedule_request(instance, state, request, delivery_day):
    pickup_day = delivery_day + request.numDays

    if pickup_day > instance.Days:
        return False

    for day in range(delivery_day, pickup_day + 1):
        used = state.tool_use[request.tool][day]
        available = instance.Tools[request.tool - 1].amount
        if used + request.toolCount > available:
            return False

    return True


def greedy_repair_operator(instance, state, removed_requests):
    """
    Simple greedy repair aligned with FeasibleGreedySolver:
    - Try earliest feasible delivery day in [fromDay, toDay]
    - Postpone day-by-day when tool availability is violated
    - Insert one delivery route and one pickup route per repaired request
    """
    repaired = []

    sorted_removed = sorted(
        removed_requests,
        key=lambda request_id: instance.Requests[request_id - 1].fromDay,
    )

    for request_id in sorted_removed:
        request = instance.Requests[request_id - 1]
        request_info = state.request_state[request_id]

        if request_info["scheduled"]:
            continue

        delivery_day = request.fromDay
        while delivery_day <= request.toDay and not _can_schedule_request(
            instance, state, request, delivery_day
        ):
            delivery_day += 1

        if delivery_day > request.toDay:
            continue

        pickup_day = delivery_day + request.numDays

        for day in range(delivery_day, pickup_day + 1):
            state.tool_use[request.tool][day] += request.toolCount

        delivery_route = Route()
        delivery_route.stops = [0, request_id, 0]
        _get_or_create_day(state.solution, delivery_day).routes.append(delivery_route)

        pickup_route = Route()
        pickup_route.stops = [0, -request_id, 0]
        _get_or_create_day(state.solution, pickup_day).routes.append(pickup_route)

        request_info["scheduled"] = True
        request_info["delivery_day"] = delivery_day
        request_info["pickup_day"] = pickup_day
        repaired.append(request_id)

    return repaired
