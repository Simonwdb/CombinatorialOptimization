class SearchState:
    def __init__(self, solution, tool_use, request_state):
        self.solution = solution
        self.tool_use = tool_use
        self.request_state = request_state
        self.removal_log = []



"""
i think it's best the build_search_state function is separate from the SearchState class, 
since it involves logic for validating a solution state. The SearchState 
class can be focused on just holding the data, while the build_search_state function 
can handle the logic of creating a consistent state from a given solution.
"""
def build_search_state(instance, solution):
    """
    This function takes an existing Solution and constructs the SearchState (more info) for ALNS, which includes:
        - tool usage per day
        - request scheduling status (scheduled, delivery day, pickup day)

    Returns:
        SearchState with:
        - solution
        - tool_use[tool_id][day]
        - request_state[request_id] = {
              "scheduled": bool,
              "delivery_day": int or None,
              "pickup_day": int or None,
          }
    Okay! we can use this for initializing the search state from a given solution, and also for validating that the solution is consistent with the instance data (e.g., no request is scheduled multiple times, delivery before pickup, etc.).
    Copilot keeps finishing my sentences but it is accurate.
    """
    num_tools = len(instance.Tools)

    tool_use = [[0] * (instance.Days + 2) for _ in range(num_tools + 1)]

    request_state = {
        req.ID: {
            "scheduled": False,
            "delivery_day": None,
            "pickup_day": None,
        }
        for req in instance.Requests
    }

    for day in solution.days:#this loop counts the number of tools used per day, and checks for consistency of the solution
        d = day.day_number
        for route in day.routes:
            for stop in route.stops:
                if stop == 0:#this is the depot stop, it can be ingored
                    continue

                request_id = abs(stop)

                if stop > 0:#this is a delivery stop
                    if request_state[request_id]["delivery_day"] is not None:
                        raise ValueError(f"Request {request_id} has multiple delivery stops in solution.")#raises on invalid solution where a request is scheduled multiple times
                    request_state[request_id]["scheduled"] = True
                    request_state[request_id]["delivery_day"] = d
                else:#this is a pickup stop
                    if request_state[request_id]["pickup_day"] is not None:
                        raise ValueError(f"Request {request_id} has multiple pickup stops in solution.")#ditto
                    request_state[request_id]["scheduled"] = True
                    request_state[request_id]["pickup_day"] = d

    # Rebuild tool usage from request assignments
    for req in instance.Requests:#looks at all requests in the solution, and updates the tool usage for the days between delivery and pickup
        info = request_state[req.ID]
        if not info["scheduled"]:
            continue

        delivery_day = info["delivery_day"]
        pickup_day = info["pickup_day"]

        if delivery_day is None or pickup_day is None:
            raise ValueError(f"Request {req.ID} is partially scheduled in solution.")#existence check

        if pickup_day < delivery_day:
            raise ValueError(f"Request {req.ID} has pickup day before delivery day.")#consistency check

        for d in range(delivery_day, pickup_day + 1):
            tool_use[req.tool][d] += req.toolCount#updates tool usage for days between delivery and pickup

    return SearchState(solution, tool_use, request_state)