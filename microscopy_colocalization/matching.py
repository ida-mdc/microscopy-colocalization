"""Point-matching primitives shared by p2p and p2c, from fish_colocalization. compare_spot_sets
drops an unnecessary deepcopy (see inline comment); get_spots_distances fixes a
bilinear-interpolation bug (see inline comment).
"""
import numpy as np
from scipy import spatial


def compare_spot_sets(set1, set2, min_dist):
    """Greedily match the closest pair of points between two sets, repeating until no pair
    is within min_dist. Returns (matched_set1, matched_set2, distances, mean_distance).
    """
    distances = []

    removed_items = True
    euc_dist = 0

    used_spots_gt = []
    used_spots_detected = []

    while removed_items and len(set2) != 0 and len(set1) != 0:

        min_dist_curr = 10000
        min_index_set1 = -1
        min_index_set2 = -1
        counter = 0
        # KDTree only reads its input; set2 is already a fresh array after np.delete, so no
        # copy is needed here (the original deepcopy was pure overhead).
        kdtree = spatial.KDTree(set2)

        for item in set1:
            distance, index = kdtree.query(item)

            if distance < min_dist_curr:
                min_dist_curr = distance
                min_index_set1 = counter
                min_index_set2 = index

            counter = counter + 1

        if min_dist_curr < min_dist:

            used_spots_gt.append(set1[min_index_set1])
            used_spots_detected.append(set2[min_index_set2])

            set2 = np.delete(set2, min_index_set2, axis=0)
            set1 = np.delete(set1, min_index_set1, axis=0)
            removed_items = True
            distances.append(min_dist_curr)

        else:
            removed_items = False

    if len(distances) > 0:
        distances = np.around(np.asarray(distances), 4)
        euc_dist = np.mean(distances)

    return np.asarray(used_spots_gt), np.asarray(used_spots_detected), distances, euc_dist


def get_spots_distances(spots, dist_map):
    """Bilinearly interpolate each spot's distance from a precomputed distance map."""
    distances = []

    for x, y in spots:
        x1, y1 = int(np.floor(x)), int(np.floor(y))
        # x2/y2 must be a distinct neighboring pixel even when x/y is already an integer
        # (using ceil() here would collapse x2==x1, zeroing out every interpolation weight).
        x2 = min(x1 + 1, dist_map.shape[0] - 1)
        y2 = min(y1 + 1, dist_map.shape[1] - 1)
        frac_x, frac_y = x - x1, y - y1

        q11 = dist_map[x1, y1]
        q12 = dist_map[x1, y2]
        q21 = dist_map[x2, y1]
        q22 = dist_map[x2, y2]

        interpolated_value = (q11 * (1 - frac_x) * (1 - frac_y) +
                              q21 * frac_x * (1 - frac_y) +
                              q12 * (1 - frac_x) * frac_y +
                              q22 * frac_x * frac_y)

        distances.append(interpolated_value)

    return distances
