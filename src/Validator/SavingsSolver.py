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