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

    pass