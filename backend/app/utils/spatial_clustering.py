"""
Spatial clustering utilities using DBSCAN
"""
from sklearn.cluster import DBSCAN
import numpy as np
from typing import List, Tuple
import logging

logger = logging.getLogger(__name__)


def cluster_locations_dbscan(
    coordinates: List[Tuple[float, float]],
    eps_km: float = 0.5,
    min_samples: int = 3
) -> np.ndarray:
    """
    Cluster geographic coordinates using DBSCAN with Haversine distance

    Args:
        coordinates: List of (latitude, longitude) tuples
        eps_km: Maximum distance between two samples in kilometers (default 0.5km)
        min_samples: Minimum number of samples in a neighborhood (default 3)

    Returns:
        numpy array of cluster labels (-1 for noise/outliers)
    """
    if len(coordinates) < min_samples:
        logger.warning(f"Not enough coordinates ({len(coordinates)}) for clustering (min {min_samples})")
        return np.array([-1] * len(coordinates))

    # Convert coordinates to numpy array and radians for Haversine
    coords_array = np.array(coordinates)
    coords_rad = np.radians(coords_array)

    # DBSCAN with Haversine metric
    # eps is in radians: eps_km / Earth's radius (6371 km)
    eps_radians = eps_km / 6371.0

    clustering = DBSCAN(
        eps=eps_radians,
        min_samples=min_samples,
        metric='haversine',
        algorithm='ball_tree'
    )

    labels = clustering.fit_predict(coords_rad)

    # Log clustering results
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise = list(labels).count(-1)
    logger.info(f"DBSCAN found {n_clusters} clusters and {n_noise} noise points from {len(coordinates)} locations")

    return labels


def get_cluster_center(coordinates: List[Tuple[float, float]]) -> Tuple[float, float]:
    """
    Calculate the centroid of a cluster of coordinates

    Args:
        coordinates: List of (latitude, longitude) tuples

    Returns:
        (lat, lon) tuple representing the cluster center
    """
    if not coordinates:
        return (0.0, 0.0)

    lats = [c[0] for c in coordinates]
    lons = [c[1] for c in coordinates]

    return (sum(lats) / len(lats), sum(lons) / len(lons))


def calculate_cluster_radius(
    coordinates: List[Tuple[float, float]],
    center: Tuple[float, float]
) -> float:
    """
    Calculate the maximum distance from cluster center to any point

    Args:
        coordinates: List of (latitude, longitude) tuples
        center: (lat, lon) tuple of cluster center

    Returns:
        Maximum distance in kilometers
    """
    from geopy.distance import geodesic

    if not coordinates:
        return 0.0

    max_distance = 0.0
    for coord in coordinates:
        distance = geodesic(center, coord).kilometers
        max_distance = max(max_distance, distance)

    return max_distance
