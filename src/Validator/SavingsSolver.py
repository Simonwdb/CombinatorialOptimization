from BaseSolver import BaseSolver
from Solution import Solution, Day, Route


class SavingsSolver(BaseSolver):
    """
    Improves a feasible solution using the Clarke & Wright savings algorithm.

    Strategy:
    - For each day, compute savings for all pairs of single-stop routes:
      s(i,j) = d(depot, i) + d(depot, j) - d(i, j)
    - Merge routes in descending order of savings
    - Only merge if capacity and max distance constraints are satisfied
    - Savings are computed once at the start (classic Clarke & Wright)

    The input solution is not modified; a new Solution is returned.
    """

    def __init__(self, instance, solution):
        super().__init__(instance)
        self.initial_solution = solution

    def solve(self, debug=False) -> Solution:
        dist = self.instance.calcDistance
        depot = self.instance.DepotCoordinate

        new_solution = Solution()

        for day in self.initial_solution.days:
            improved_day = self._improve_day(day, dist, depot, debug)
            new_solution.days.append(improved_day)

        return new_solution

    def _improve_day(self, day, dist, depot, debug):
        """Apply Clarke & Wright savings to all routes on a given day."""
        routes = [list(route.stops) for route in day.routes]

        # Compute savings once for all pairs of single-stop routes
        savings = self._compute_savings(routes, dist, depot)
        savings.sort(key=lambda x: x[0], reverse=True)

        if debug:
            print(f"\nDag {day.day_number}: {len(routes)} routes, {len(savings)} savings-paren")

        merged_count = 0

        for saving, i, j in savings:
            if saving <= 0:
                break

            # Skip if either route has already been merged into another
            if routes[i] is None or routes[j] is None:
                continue

            inner_i = routes[i][1:-1]
            inner_j = routes[j][1:-1]

            merged = None
            for candidate in [[0] + inner_i + inner_j + [0], [0] + inner_j + inner_i + [0]]:
                if self._is_feasible(candidate, dist, depot):
                    merged = candidate
                    break

            if merged is not None:
                if debug:
                    print(f"  Saving {saving}: merge {routes[i]} + {routes[j]} -> {merged}")
                routes[i] = merged
                routes[j] = None
                merged_count += 1
            else:
                if debug:
                    print(f"  Saving {saving}: {routes[i]} + {routes[j]} NIET feasible")

        if debug:
            remaining = [r for r in routes if r is not None]
            print(f"  Resultaat: {merged_count} merges, {len(remaining)} routes over")

        # Build the new Day with remaining routes
        new_day = Day(day.day_number)
        for stops in routes:
            if stops is not None:
                r = Route()
                r.stops = stops
                new_day.routes.append(r)

        return new_day