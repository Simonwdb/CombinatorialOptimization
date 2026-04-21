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

    pass