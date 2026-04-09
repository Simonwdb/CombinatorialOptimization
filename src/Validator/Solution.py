class Route:
    def __init__(self):
        self.stops = []  # e.g. [0, 1, 0] for delivery or [0, -1, 0] for pickup

class Day:
    def __init__(self, day_number):
        self.day_number = day_number
        self.routes = []  # list of Route objects

class Solution:
    def __init__(self):
        self.days = []  # list of Day objects