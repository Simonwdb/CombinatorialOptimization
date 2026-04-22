from .BaseSolver import BaseSolver
from .Solution import Solution, Day, Route

class FeasibleGreedySolver(BaseSolver):
    """
    Greedy solver that ensures tool availability constraints are satisfied.
    
    Strategy:
    - Deliver each request on the earliest possible day (fromDay)
    - If tool availability is exceeded, postpone delivery by one day
    - Repeat until no violation or toDay is reached
    - Each job gets its own route (no combining of jobs)
    """

    def solve(self, debug=False) -> Solution:
        solution = Solution()
        days = {}  # {day_number: Day}
        num_tools = len(self.instance.Tools)

        # Track tool usage per day: tool_use[tool_id][day]
        tool_use = [[0] * (self.instance.Days + 2) for _ in range(num_tools + 1)]

        if debug:
            print("\n" + "="*60)
            print("FeasibleGreedySolver - Debug output")
            print("="*60)

        sorted_requests = sorted(self.instance.Requests, key=lambda r: r.fromDay)
        for request in sorted_requests:
            delivery_day = request.fromDay
            original_day = request.fromDay

            if debug:
                print(f"\nProcessing request {request.ID} (tool {request.tool}, count {request.toolCount}, from {request.fromDay} to {request.toDay}, numDays {request.numDays})")

            # Postpone if tool availability is exceeded
            while delivery_day <= request.toDay:
                pickup_day = delivery_day + request.numDays

                # Check if adding this request causes a violation
                violation = False
                for d in range(delivery_day, pickup_day + 1):
                    current = tool_use[request.tool][d]
                    available = self.instance.Tools[request.tool - 1].amount
                    if current + request.toolCount > available:
                        if debug:
                            print(f"  Violation on day {d}: {current} + {request.toolCount} > {available} for tool {request.tool}")
                        violation = True
                        break

                if not violation:
                    if debug and delivery_day != original_day:
                        print(f"  Postponed from day {original_day} to day {delivery_day}")
                    elif debug:
                        print(f"  Planned on day {delivery_day} (no postponement needed)")
                    break

                delivery_day += 1

            # Check if we failed to plan the request
            if delivery_day > request.toDay:
                print(f"  WARNING: Request {request.ID} could not be planned within time window ({request.fromDay}-{request.toDay})!")
                continue

            # Update tool usage
            pickup_day = delivery_day + request.numDays
            for d in range(delivery_day, pickup_day + 1):
                tool_use[request.tool][d] += request.toolCount

            if debug:
                print(f"  Delivery day: {delivery_day}, Pickup day: {pickup_day}")
                print(f"  Tool {request.tool} usage after planning:")
                for d in range(delivery_day, pickup_day + 1):
                    print(f"    Day {d}: {tool_use[request.tool][d]}/{self.instance.Tools[request.tool-1].amount}")

            # Add delivery route
            if delivery_day not in days:
                days[delivery_day] = Day(delivery_day)
            delivery_route = Route()
            delivery_route.stops = [0, request.ID, 0]
            days[delivery_day].routes.append(delivery_route)

            # Add pickup route
            if pickup_day not in days:
                days[pickup_day] = Day(pickup_day)
            pickup_route = Route()
            pickup_route.stops = [0, -request.ID, 0]
            days[pickup_day].routes.append(pickup_route)

        if debug:
            print("\n" + "="*60)
            print("Final tool usage per day:")
            print(f"{'Day':<6}", end="")
            for t in range(1, num_tools + 1):
                print(f"{'Tool '+str(t):<15}", end="")
            print()
            for d in range(1, self.instance.Days + 1):
                print(f"{d:<6}", end="")
                for t in range(1, num_tools + 1):
                    in_use = tool_use[t][d]
                    available = self.instance.Tools[t-1].amount
                    exceeded = in_use > available
                    marker = " EXCEEDED" if exceeded else ""
                    print(f"{str(in_use)+'/'+str(available)+marker:<15}", end="")
                print()
            print("="*60 + "\n")

        # Convert dictionary to sorted list of days
        solution.days = [days[d] for d in sorted(days.keys())]

        return solution