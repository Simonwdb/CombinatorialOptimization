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

    pass