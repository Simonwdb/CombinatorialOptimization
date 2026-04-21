from BaseSolver import BaseSolver
from Solution import Solution, Day, Route

class NearestNeighbourSolver(BaseSolver):
    """
    Nearest Neighbour solver for the VeRoLog Solver Challenge 2017.
    
    Strategy:
    - Use FeasibleGreedy approach to determine delivery and pickup days
    - For each day, plan deliveries first using Nearest Neighbour routing
    - Then plan pickups using Nearest Neighbour routing
    - Always choose the nearest feasible job given capacity and distance constraints
    """

    def _determine_days(self):
        """
        Determines delivery and pickup days for each request
        using the FeasibleGreedy approach (deliver on fromDay, postpone if needed).
        Returns two dicts: delivery_day and pickup_day per request ID.
        """
        num_tools = len(self.instance.Tools)
        tool_use = [[0] * (self.instance.Days + 2) for _ in range(num_tools + 1)]
        delivery_day = {}
        pickup_day = {}

        sorted_requests = sorted(self.instance.Requests, key=lambda r: r.fromDay)

        for request in sorted_requests:
            day = request.fromDay

            while day <= request.toDay:
                pickup = day + request.numDays
                violation = False
                for d in range(day, pickup + 1):
                    if tool_use[request.tool][d] + request.toolCount > self.instance.Tools[request.tool - 1].amount:
                        violation = True
                        break
                if not violation:
                    break
                day += 1

            if day > request.toDay:
                print(f"WARNING: Request {request.ID} could not be planned!")
                continue

            pickup = day + request.numDays
            for d in range(day, pickup + 1):
                tool_use[request.tool][d] += request.toolCount

            delivery_day[request.ID] = day
            pickup_day[request.ID] = pickup

        return delivery_day, pickup_day
