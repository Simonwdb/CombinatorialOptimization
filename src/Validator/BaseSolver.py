from Solution import Solution

class BaseSolver:
    def __init__(self, instance):
        self.instance = instance  # InstanceCVRPTWUI object
    
    def solve(self) -> Solution:
        # To be implemented by subclasses
        raise NotImplementedError("solve() must be implemented by subclass")