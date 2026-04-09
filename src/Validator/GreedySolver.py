from BaseSolver import BaseSolver
from Solution import Solution, Day, Route

class GreedySolver(BaseSolver):
    """
    Greedy solver for the VeRoLog Solver Challenge 2017.
    
    Strategy:
    - Deliver each request on the earliest possible day (fromDay)
    - Pick up each request on the fixed pickup day (fromDay + numDays)
    - Each job gets its own route (no combining of jobs)
    
    This results in a feasible but not necessarily optimal solution.
    """
    
    def solve(self) -> Solution:
        solution = Solution()
        days = {}  # {day_number: Day}
        
        for request in self.instance.Requests:
            delivery_day = request.fromDay
            pickup_day = request.fromDay + request.numDays
            
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
        
        # Convert dictionary to sorted list of days
        solution.days = [days[d] for d in sorted(days.keys())]
        
        return solution