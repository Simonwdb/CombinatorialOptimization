import copy
from Solution import Solution, Day, Route
from Validate import SolutionCVRPTWUI
from BaseSolver import BaseSolver
from NearestNeighbourSolverV2 import NearestNeighbourSolverV2
# from FeasibleGreedySolver import FeasibleGreedySolver   

class ALNSSolver(BaseSolver):
    def __init__(self, instance):
        super().__init__(instance)
        self.destroy_operators = [WorstRemoval(instance), RandomRemoval(instance)]

    def solve(self) -> Solution:
        # Use Nearest Neighbour as initial solution
        initial_solver = NearestNeighbourSolverV2(self.instance)
        solution = initial_solver.solve()

        # Apply destroy operators for demonstration
        for destroy_op in self.destroy_operators:
            solution = destroy_op.destroy(solution)

        return solution

class DestroyOperator:
    def __init__(self, instance):
        self.instance = instance

    def destroy(self, solution: Solution) -> Solution:
        # To be implemented by subclasses
        raise NotImplementedError

class WorstRemoval(DestroyOperator):
    def destroy(self, solution: Solution) -> Solution:
        # Remove the route with the highest distance

        if not solution.days:
            return solution

        max_distance = -1
        route_to_remove = None

        for day in solution.days:
            for i, route in enumerate(day.routes):
                distance = self._calculate_route_distance(route)
                if distance > max_distance:
                    max_distance = distance
                    route_to_remove = (day.day_number, i)

        if route_to_remove:
            day_num, route_idx = route_to_remove
            for day in solution.days:
                if day.day_number == day_num:
                    day.routes.pop(route_idx)
                    break
            # Remove empty days
            solution.days = [d for d in solution.days if d.routes]

        return solution

    def _calculate_route_distance(self, route: Route) -> float:
        distance = 0
        last_node = 0
        for node in route.stops[1:]:
            if node == 0:
                break
            from_coord = self.instance.DepotCoordinate if last_node == 0 else self.instance.Requests[abs(last_node)-1].node
            to_coord = self.instance.Requests[abs(node)-1].node
            distance += self.instance.calcDistance[from_coord][to_coord]
            last_node = node
        # Add return to depot
        if last_node != 0:
            from_coord = self.instance.Requests[abs(last_node)-1].node
            distance += self.instance.calcDistance[from_coord][self.instance.DepotCoordinate]
        return distance

class RandomRemoval(DestroyOperator):
    def destroy(self, solution: Solution) -> Solution:
        # Randomly remove a route
        import random
        if not solution.days:
            return solution

        # Collect all routes
        routes = []
        for day in solution.days:
            for i in range(len(day.routes)):
                routes.append((day.day_number, i))

        if not routes:
            return solution

        day_num, route_idx = random.choice(routes)
        new_solution = copy.deepcopy(solution)
        for day in new_solution.days:
            if day.day_number == day_num:
                day.routes.pop(route_idx)
                break
        # Remove empty days
        new_solution.days = [d for d in new_solution.days if d.routes]
        return new_solution