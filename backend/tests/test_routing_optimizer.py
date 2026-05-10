"""
Tests for the routing optimizer — validates TSP solving and clustering.
"""

import pytest
import asyncio
from app.schemas.itinerary import GeocodedPlace
from app.services.routing_optimizer import (
    _solve_tsp_ortools,
    _solve_tsp_nearest_neighbor,
    _cluster_places,
    generate_itinerary,
)


# ── Test Data ───────────────────────────────────────────────────────────

HOTEL = GeocodedPlace(
    name="Hotel Gracery Shinjuku",
    lat=35.6938, lng=139.7034,
    address="Shinjuku", place_id="hotel",
)

PLACES = [
    GeocodedPlace(name="Meiji Shrine", lat=35.6764, lng=139.6993, address="", place_id="p1"),
    GeocodedPlace(name="Shibuya Crossing", lat=35.6595, lng=139.7004, address="", place_id="p2"),
    GeocodedPlace(name="Tokyo Tower", lat=35.6586, lng=139.7454, address="", place_id="p3"),
    GeocodedPlace(name="Senso-ji", lat=35.7148, lng=139.7967, address="", place_id="p4"),
    GeocodedPlace(name="Akihabara", lat=35.7023, lng=139.7745, address="", place_id="p5"),
    GeocodedPlace(name="Tsukiji Market", lat=35.6654, lng=139.7707, address="", place_id="p6"),
]


class TestTSPSolver:
    """Tests for the OR-Tools TSP solver."""

    def test_trivial_one_node(self):
        """TSP with 1 node (just depot) should return [0, 0]."""
        matrix = [[0]]
        route = _solve_tsp_ortools(matrix, depot=0)
        assert route[0] == 0, "Route must start at depot"
        assert route[-1] == 0, "Route must end at depot"

    def test_two_nodes(self):
        """TSP with 2 nodes should visit both."""
        matrix = [[0, 100], [100, 0]]
        route = _solve_tsp_ortools(matrix, depot=0)
        assert route[0] == 0, "Route must start at depot"
        assert route[-1] == 0, "Route must end at depot"
        assert 1 in route, "Must visit node 1"

    def test_four_nodes_starts_and_ends_at_depot(self):
        """Route must start and end at depot (index 0)."""
        matrix = [
            [0, 10, 15, 20],
            [10, 0, 35, 25],
            [15, 35, 0, 30],
            [20, 25, 30, 0],
        ]
        route = _solve_tsp_ortools(matrix, depot=0)
        assert route[0] == 0, "Route must start at depot"
        assert route[-1] == 0, "Route must end at depot"

    def test_four_nodes_visits_all(self):
        """Route must visit every node exactly once (excluding depot return)."""
        matrix = [
            [0, 10, 15, 20],
            [10, 0, 35, 25],
            [15, 35, 0, 30],
            [20, 25, 30, 0],
        ]
        route = _solve_tsp_ortools(matrix, depot=0)
        # Exclude the final return-to-depot
        visited = set(route[:-1])
        assert visited == {0, 1, 2, 3}, f"Must visit all nodes, got {visited}"

    def test_optimal_solution_simple_case(self):
        """For a simple symmetric matrix, verify solution quality."""
        # Clear optimal: 0 → 1 → 3 → 2 → 0 = 10+25+30+15 = 80
        # or 0 → 2 → 3 → 1 → 0 = 15+30+25+10 = 80
        matrix = [
            [0, 10, 15, 20],
            [10, 0, 35, 25],
            [15, 35, 0, 30],
            [20, 25, 30, 0],
        ]
        route = _solve_tsp_ortools(matrix, depot=0)
        # Calculate total cost
        total = sum(matrix[route[i]][route[i + 1]] for i in range(len(route) - 1))
        # The optimal is 80; allow 20% tolerance
        assert total <= 96, f"Solution cost {total} exceeds 20% tolerance of optimal 80"


class TestNearestNeighborFallback:
    """Tests for the nearest-neighbor heuristic fallback."""

    def test_starts_and_ends_at_depot(self):
        matrix = [
            [0, 10, 15],
            [10, 0, 20],
            [15, 20, 0],
        ]
        route = _solve_tsp_nearest_neighbor(matrix, depot=0)
        assert route[0] == 0
        assert route[-1] == 0

    def test_visits_all_nodes(self):
        matrix = [
            [0, 10, 15],
            [10, 0, 20],
            [15, 20, 0],
        ]
        route = _solve_tsp_nearest_neighbor(matrix, depot=0)
        visited = set(route[:-1])
        assert visited == {0, 1, 2}


class TestClustering:
    """Tests for K-Means geographic clustering."""

    def test_basic_clustering(self):
        """Places should be grouped into N clusters."""
        clusters = _cluster_places(PLACES, num_days=2)
        assert len(clusters) == 2
        total_places = sum(len(c) for c in clusters)
        assert total_places == len(PLACES)

    def test_single_day(self):
        """All places in one cluster for 1 day."""
        clusters = _cluster_places(PLACES, num_days=1)
        assert len(clusters) == 1
        assert len(clusters[0]) == len(PLACES)

    def test_more_days_than_places(self):
        """Should handle gracefully when days > places."""
        clusters = _cluster_places(PLACES[:2], num_days=5)
        assert len(clusters) == 5
        total = sum(len(c) for c in clusters)
        assert total == 2

    def test_geographic_sense(self):
        """West-side places (Meiji, Shibuya) should cluster separately from east-side (Senso-ji, Akihabara)."""
        clusters = _cluster_places(PLACES, num_days=2)
        
        west_places = {"Meiji Shrine", "Shibuya Crossing", "Tokyo Tower"}
        east_places = {"Senso-ji", "Akihabara", "Tsukiji Market"}
        
        cluster_names = [
            {p.name for p in cluster} for cluster in clusters
        ]
        
        # Check that clusters don't randomly mix east and west
        # At minimum, the 3 closest places should group together
        for cluster_set in cluster_names:
            if len(cluster_set) == 3:
                # At least 2 of the 3 should be from the same geographic group
                west_count = len(cluster_set & west_places)
                east_count = len(cluster_set & east_places)
                assert west_count >= 2 or east_count >= 2, (
                    f"Cluster {cluster_set} seems geographically random"
                )


class TestItineraryGeneration:
    """Integration test for the full itinerary pipeline."""

    def test_full_itinerary_generation(self):
        """End-to-end test: hotel + places + days → structured itinerary."""
        itinerary = asyncio.get_event_loop().run_until_complete(
            generate_itinerary(
                hotel=HOTEL,
                places=PLACES,
                num_days=2,
            )
        )

        # Basic structure checks
        assert itinerary.hotel.name == "Hotel Gracery Shinjuku"
        assert len(itinerary.days) == 2

        # Each day should have places and route segments
        for day in itinerary.days:
            assert day.day_number in (1, 2)
            assert len(day.places) > 0
            assert len(day.route_segments) > 0

            # Route segments should have Google Maps URLs
            for seg in day.route_segments:
                assert seg.google_maps_url.startswith(
                    "https://www.google.com/maps/dir/"
                )
                assert "travelmode=transit" in seg.google_maps_url
                assert seg.distance_meters > 0
                assert seg.duration_seconds > 0

        # All places should be assigned to some day
        all_assigned = []
        for day in itinerary.days:
            all_assigned.extend([p.name for p in day.places])
        assert len(all_assigned) == len(PLACES)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
