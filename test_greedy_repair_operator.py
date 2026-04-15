import unittest
from types import SimpleNamespace

from greedy_repair_operator import greedy_repair_operator
from search_state import build_search_state
from src.Validator.Solution import Day, Route, Solution


def _single_stop_route(stop):
    route = Route()
    route.stops = [0, stop, 0]
    return route


class GreedyRepairOperatorTests(unittest.TestCase):
    def test_repairs_with_postponement_when_tool_is_busy(self):
        instance = SimpleNamespace(
            Days=5,
            Tools=[SimpleNamespace(amount=1)],
            Requests=[
                SimpleNamespace(
                    ID=1, fromDay=1, toDay=1, numDays=1, tool=1, toolCount=1
                ),
                SimpleNamespace(
                    ID=2, fromDay=1, toDay=3, numDays=1, tool=1, toolCount=1
                ),
            ],
        )

        solution = Solution()
        d1 = Day(1)
        d1.routes = [_single_stop_route(1)]
        d2 = Day(2)
        d2.routes = [_single_stop_route(-1)]
        solution.days = [d1, d2]

        state = build_search_state(instance, solution)
        repaired = greedy_repair_operator(instance, state, [2])

        self.assertEqual(repaired, [2])
        self.assertTrue(state.request_state[2]["scheduled"])
        self.assertEqual(state.request_state[2]["delivery_day"], 3)
        self.assertEqual(state.request_state[2]["pickup_day"], 4)

        day3 = next(day for day in state.solution.days if day.day_number == 3)
        day4 = next(day for day in state.solution.days if day.day_number == 4)
        self.assertIn([0, 2, 0], [route.stops for route in day3.routes])
        self.assertIn([0, -2, 0], [route.stops for route in day4.routes])

    def test_skips_request_when_no_feasible_day_exists(self):
        instance = SimpleNamespace(
            Days=5,
            Tools=[SimpleNamespace(amount=1)],
            Requests=[
                SimpleNamespace(
                    ID=1, fromDay=1, toDay=1, numDays=2, tool=1, toolCount=1
                ),
                SimpleNamespace(
                    ID=2, fromDay=1, toDay=2, numDays=1, tool=1, toolCount=1
                ),
            ],
        )

        solution = Solution()
        d1 = Day(1)
        d1.routes = [_single_stop_route(1)]
        d3 = Day(3)
        d3.routes = [_single_stop_route(-1)]
        solution.days = [d1, d3]

        state = build_search_state(instance, solution)
        repaired = greedy_repair_operator(instance, state, [2])

        self.assertEqual(repaired, [])
        self.assertFalse(state.request_state[2]["scheduled"])
        self.assertIsNone(state.request_state[2]["delivery_day"])
        self.assertIsNone(state.request_state[2]["pickup_day"])
        self.assertEqual(
            sorted(day.day_number for day in state.solution.days),
            [1, 3],
        )


if __name__ == "__main__":
    unittest.main()
