"""
Routing Optimizer — Geographic K-Means clustering + TSP.
Works for any destination worldwide.
Hotel acts as depot (start/end) for every day's route.
"""

import logging
import math
import numpy as np
from collections import defaultdict, Counter
from sklearn.cluster import KMeans

from app.schemas.itinerary import (
    GeocodedPlace, RouteSegment, DayPlan, ItineraryResponse,
)
from app.services.distance_matrix_service import get_distance_matrix
from app.services.directions_service import get_directions
from app.utils.google_maps_url import generate_directions_url

logger = logging.getLogger(__name__)

DAY_COLORS = [
    "#3B82F6",  # Blue
    "#10B981",  # Emerald
    "#F59E0B",  # Amber
    "#F43F5E",  # Rose
    "#8B5CF6",  # Violet
    "#06B6D4",  # Cyan
    "#EC4899",  # Pink
    "#14B8A6",  # Teal
    "#EF4444",  # Red
    "#A855F7",  # Purple
]


def _solve_tsp_ortools(duration_matrix: list[list[int]], depot: int = 0) -> list[int]:
    """Solve TSP using OR-Tools with hotel as depot."""
    try:
        from ortools.constraint_solver import routing_enums_pb2, pywrapcp
    except ImportError:
        logger.warning("OR-Tools not installed — using nearest-neighbor")
        return _solve_tsp_nearest_neighbor(duration_matrix, depot)

    n = len(duration_matrix)
    if n <= 2:
        route = list(range(n))
        route.append(depot)
        return route

    manager = pywrapcp.RoutingIndexManager(n, 1, depot)
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index, to_index):
        return duration_matrix[manager.IndexToNode(from_index)][manager.IndexToNode(to_index)]

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    search_parameters.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    search_parameters.time_limit.FromSeconds(5)

    solution = routing.SolveWithParameters(search_parameters)
    if not solution:
        return _solve_tsp_nearest_neighbor(duration_matrix, depot)

    route = []
    index = routing.Start(0)
    while not routing.IsEnd(index):
        route.append(manager.IndexToNode(index))
        index = solution.Value(routing.NextVar(index))
    route.append(manager.IndexToNode(index))

    logger.info(f"TSP solved: {n} nodes, cost={solution.ObjectiveValue()}s, route={route}")
    return route


def _solve_tsp_nearest_neighbor(duration_matrix: list[list[int]], depot: int = 0) -> list[int]:
    """Nearest-neighbor heuristic fallback."""
    n = len(duration_matrix)
    visited = {depot}
    route = [depot]
    current = depot

    while len(visited) < n:
        best_next, best_cost = -1, float("inf")
        for j in range(n):
            if j not in visited and duration_matrix[current][j] < best_cost:
                best_cost = duration_matrix[current][j]
                best_next = j
        if best_next == -1:
            break
        route.append(best_next)
        visited.add(best_next)
        current = best_next

    route.append(depot)
    return route


def _cluster_places(
    places: list[GeocodedPlace], num_days: int
) -> list[list[GeocodedPlace]]:
    """
    Cluster places into daily groups.
    Strategy: try region-based first, fall back to K-Means geographic clustering.
    """
    # If places <= num_days, one per day
    if len(places) <= num_days:
        clusters = [[p] for p in places]
        while len(clusters) < num_days:
            clusters.append([])
        return clusters

    # Try region-based clustering first
    region_groups: dict[str, list[GeocodedPlace]] = defaultdict(list)
    for p in places:
        region = p.district or "Other"
        region_groups[region].append(p)

    # If regions provide good clustering (reasonable number of groups)
    if 1 < len(region_groups) <= num_days * 2:
        # Merge regions into num_days clusters based on proximity
        return _merge_region_clusters(region_groups, num_days, places)

    # Fall back to K-Means geographic clustering
    return _cluster_kmeans(places, num_days)


def _merge_region_clusters(
    region_groups: dict[str, list[GeocodedPlace]], 
    num_days: int,
    all_places: list[GeocodedPlace],
) -> list[list[GeocodedPlace]]:
    """Merge region groups into num_days clusters, keeping nearby regions together."""
    if len(region_groups) <= num_days:
        clusters = [places for places in region_groups.values()]
        while len(clusters) < num_days:
            # Split the largest cluster
            largest_idx = max(range(len(clusters)), key=lambda i: len(clusters[i]))
            if len(clusters[largest_idx]) > 1:
                mid = len(clusters[largest_idx]) // 2
                clusters.append(clusters[largest_idx][mid:])
                clusters[largest_idx] = clusters[largest_idx][:mid]
            else:
                clusters.append([])
        return clusters[:num_days]

    # More regions than days → use K-Means
    return _cluster_kmeans(all_places, num_days)


def _cluster_kmeans(places: list[GeocodedPlace], num_days: int) -> list[list[GeocodedPlace]]:
    """K-Means geographic clustering — works for any location."""
    if len(places) <= num_days:
        return [[p] for p in places] + [[] for _ in range(num_days - len(places))]

    coords = np.array([[p.lat, p.lng] for p in places])
    kmeans = KMeans(n_clusters=num_days, random_state=42, n_init=10)
    labels = kmeans.fit_predict(coords)

    clusters: list[list[GeocodedPlace]] = [[] for _ in range(num_days)]
    for i, label in enumerate(labels):
        clusters[label].append(places[i])

    # Sort clusters by centroid latitude (north to south)
    centroids = kmeans.cluster_centers_
    order = sorted(range(num_days), key=lambda i: -centroids[i][0])
    clusters = [clusters[i] for i in order]

    return clusters


def _get_cluster_name(places: list[GeocodedPlace]) -> str:
    """Determine the best name for a cluster based on place regions."""
    if not places:
        return ""
    regions = [p.district for p in places if p.district]
    if regions:
        # Use most common region
        counter = Counter(regions)
        return counter.most_common(1)[0][0]
    return ""


async def generate_itinerary(
    hotel: GeocodedPlace,
    places: list[GeocodedPlace],
    num_days: int,
) -> ItineraryResponse:
    """Main orchestrator — generates a complete multi-day optimized itinerary."""
    logger.info(
        f"Generating itinerary: hotel='{hotel.name}', "
        f"places={[p.name for p in places]}, days={num_days}"
    )

    clusters = _cluster_places(places, num_days)
    day_plans: list[DayPlan] = []

    for day_idx, cluster_places in enumerate(clusters):
        if not cluster_places:
            day_plans.append(DayPlan(
                day_number=day_idx + 1,
                color=DAY_COLORS[day_idx % len(DAY_COLORS)],
                district_name="",
                places=[],
                route_segments=[],
                total_distance_meters=0,
                total_duration_seconds=0,
            ))
            continue

        # Determine area name for this day
        area_name = _get_cluster_name(cluster_places)

        all_nodes = [hotel] + cluster_places
        duration_matrix, dist_matrix = await get_distance_matrix(all_nodes)
        optimal_order = _solve_tsp_ortools(duration_matrix, depot=0)

        ordered_places = [all_nodes[i] for i in optimal_order if i != 0]
        route_segments: list[RouteSegment] = []
        total_dist = total_dur = 0

        route_nodes = [all_nodes[i] for i in optimal_order]
        for seg_idx in range(len(route_nodes) - 1):
            from_p = route_nodes[seg_idx]
            to_p = route_nodes[seg_idx + 1]

            directions = await get_directions(from_p, to_p)
            gmaps_url = generate_directions_url(
                from_p.lat, from_p.lng, to_p.lat, to_p.lng, "transit",
            )

            segment = RouteSegment(
                from_place=from_p,
                to_place=to_p,
                distance_meters=directions["distance_meters"],
                duration_seconds=directions["duration_seconds"],
                route_geometry=directions["route_geometry"],
                google_maps_url=gmaps_url,
            )
            route_segments.append(segment)
            total_dist += directions["distance_meters"]
            total_dur += directions["duration_seconds"]

        day_plans.append(DayPlan(
            day_number=day_idx + 1,
            color=DAY_COLORS[day_idx % len(DAY_COLORS)],
            district_name=area_name,
            places=ordered_places,
            route_segments=route_segments,
            total_distance_meters=total_dist,
            total_duration_seconds=total_dur,
        ))

        logger.info(f"Day {day_idx + 1} [{area_name}]: {len(ordered_places)} places, {total_dist}m, {total_dur}s")

    return ItineraryResponse(hotel=hotel, days=day_plans, ai_explanation="")
