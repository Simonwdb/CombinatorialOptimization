from BaseSolver import BaseSolver
from Solution import Solution, Day, Route

class NearestNeighbourSolverV2(BaseSolver):
    """
    Nearest Neighbour solver V2 for the VeRoLog Solver Challenge 2017.
    
    Strategy:
    - Use FeasibleGreedy approach to determine delivery and pickup days
    - For each day, build routes that first deliver, then pick up
    - Within each route: first plan deliveries using NN, then pickups using NN
    - This allows combining deliveries and pickups in one route
    """

    def _determine_days(self):
        """
        Determines delivery and pickup days for each request
        using the FeasibleGreedy approach.
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

    def _plan_day_with_nn(self, deliveries, pickups):
        """
        Plans routes for a single day using Nearest Neighbour heuristic.
        Each route first delivers, then picks up.
        Returns a list of Route objects.
        """
        remaining_deliveries = list(deliveries)
        remaining_pickups = list(pickups)
        depot = self.instance.DepotCoordinate
        capacity = self.instance.Capacity
        max_distance = self.instance.MaxDistance
        routes = []

        while remaining_deliveries or remaining_pickups:
            route = Route()
            route.stops = [0]
            current_node = depot
            current_load = 0
            current_distance = 0

            # Phase 1: deliveries
            while remaining_deliveries:
                feasible_jobs = [
                    r for r in remaining_deliveries
                    if current_load + r.toolCount * self.instance.Tools[r.tool - 1].weight <= capacity
                    and current_distance + self.instance.calcDistance[current_node][r.node] + self.instance.calcDistance[r.node][depot] <= max_distance
                ]

                if not feasible_jobs:
                    break

                beste_job = min(feasible_jobs, key=lambda r: self.instance.calcDistance[current_node][r.node])
                weight = beste_job.toolCount * self.instance.Tools[beste_job.tool - 1].weight

                route.stops.append(beste_job.ID)
                current_load += weight
                current_distance += self.instance.calcDistance[current_node][beste_job.node]
                current_node = beste_job.node
                remaining_deliveries.remove(beste_job)

            # Reset load after deliveries (vehicle is now empty)
            current_load = 0

            # Phase 2: pickups
            while remaining_pickups:
                feasible_jobs = [
                    r for r in remaining_pickups
                    if current_load + r.toolCount * self.instance.Tools[r.tool - 1].weight <= capacity
                    and current_distance + self.instance.calcDistance[current_node][r.node] + self.instance.calcDistance[r.node][depot] <= max_distance
                ]

                if not feasible_jobs:
                    break

                beste_job = min(feasible_jobs, key=lambda r: self.instance.calcDistance[current_node][r.node])
                weight = beste_job.toolCount * self.instance.Tools[beste_job.tool - 1].weight

                route.stops.append(-beste_job.ID)
                current_load += weight
                current_distance += self.instance.calcDistance[current_node][beste_job.node]
                current_node = beste_job.node
                remaining_pickups.remove(beste_job)

            route.stops.append(0)
            routes.append(route)

        return routes