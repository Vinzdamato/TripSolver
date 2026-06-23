# astar_router.py
# ------------------------------------------------------------
# OBIETTIVO
#   Dato un sottoinsieme di POI (es. quelli assegnati a una giornata
#   dal modulo CSP), trovare l'ordine di visita che minimizza la
#   distanza totale percorsa -- classico problema del commesso
#   viaggiatore (TSP) con percorso aperto (non si torna al punto di
#   partenza), risolto come RICERCA IN SPAZIO DI STATI con A*.
#
# FORMULAZIONE DEL PROBLEMA (cfr. cap. 2 del programma)
#   - Stato:        (poi_corrente, frozenset(poi_visitati))
#   - Stato iniziale:(poi_partenza, {poi_partenza})
#   - Azioni:       spostarsi a un POI non ancora visitato
#   - Costo azione: distanza (in metri, formula di haversine) fra i due POI
#   - Stato goal:   tutti i POI sono stati visitati
#   - Euristica h: lunghezza del Minimum Spanning Tree (MST) sui nodi non
#     ancora visitati + costo minimo per raggiungerli dal nodo corrente.
#     E' una euristica AMMISSIBILE (non sovrastima mai il costo reale
#     residuo), quindi A* garantisce la soluzione ottima.
#
# NOTE SULLA SCALABILITA'
#   Lo spazio degli stati cresce come O(n * 2^n): per questo motivo
#   l'algoritmo va applicato a sottoinsiemi "di giornata" (tipicamente
#   4-8 POI), non all'intero dataset. Per istanze più grandi si
#   raccomanda di documentare esplicitamente il limite e, se necessario,
#   sostituire A* con una euristica costruttiva (nearest-neighbor + 2-opt)
#   discutendo il trade-off ottimalità/tempo nella documentazione.
# ------------------------------------------------------------

import heapq
import itertools
from math import radians, sin, cos, sqrt, atan2
from functools import lru_cache


def haversine_m(p1, p2):
    R = 6371000
    lat1, lon1 = p1
    lat2, lon2 = p2
    phi1, phi2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dlmb = radians(lon2 - lon1)
    a = sin(dphi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(dlmb / 2) ** 2
    return 2 * R * atan2(sqrt(a), sqrt(1 - a))


def build_distance_matrix(poi_coords: dict):
    """poi_coords: {poi_id: (lat, lon)} -> dict[(i,j)] = metri"""
    ids = list(poi_coords.keys())
    dist = {}
    for i in ids:
        for j in ids:
            if i != j:
                dist[(i, j)] = haversine_m(poi_coords[i], poi_coords[j])
    return dist


def _mst_cost(nodes, dist):
    """Costo del Minimum Spanning Tree (Prim) su un sottoinsieme di nodi.
    Usato come componente dell'euristica ammissibile."""
    nodes = list(nodes)
    if len(nodes) <= 1:
        return 0.0
    in_tree = {nodes[0]}
    rest = set(nodes[1:])
    total = 0.0
    while rest:
        best = None
        best_cost = float("inf")
        for a in in_tree:
            for b in rest:
                c = dist[(a, b)]
                if c < best_cost:
                    best_cost = c
                    best = b
        total += best_cost
        in_tree.add(best)
        rest.remove(best)
    return total


def heuristic(current, unvisited, dist):
    """h(stato) = MST(unvisited) + distanza minima da `current` a unvisited.
    Ammissibile: sottostima il costo per visitare tutti i nodi rimanenti."""
    if not unvisited:
        return 0.0
    mst = _mst_cost(unvisited, dist)
    min_edge_to_unvisited = min(dist[(current, u)] for u in unvisited)
    return mst + min_edge_to_unvisited


def astar_route(poi_coords: dict, start_id):
    """Ricerca A* nello spazio degli stati (corrente, visitati) per
    trovare l'ordine di visita a costo (distanza) minimo.

    Ritorna: (ordine_poi, costo_totale_metri)
    """
    dist = build_distance_matrix(poi_coords)
    all_ids = frozenset(poi_coords.keys())

    start_state = (start_id, frozenset([start_id]))
    g0 = 0.0
    h0 = heuristic(start_id, all_ids - {start_id}, dist)

    open_heap = [(g0 + h0, g0, start_state, [start_id])]
    best_g = {start_state: g0}

    while open_heap:
        f, g, (current, visited), path = heapq.heappop(open_heap)

        if visited == all_ids:
            return path, g

        if g > best_g.get((current, visited), float("inf")):
            continue  # stato già espanso con costo migliore

        unvisited = all_ids - visited
        for nxt in unvisited:
            new_g = g + dist[(current, nxt)]
            new_visited = visited | {nxt}
            new_state = (nxt, new_visited)
            if new_g < best_g.get(new_state, float("inf")):
                best_g[new_state] = new_g
                h = heuristic(nxt, all_ids - new_visited, dist)
                heapq.heappush(open_heap, (new_g + h, new_g, new_state, path + [nxt]))

    raise RuntimeError("Nessun percorso trovato (stato goal irraggiungibile).")


if __name__ == "__main__":
    # Mini esempio autonomo (5 POI fittizi) per verificare il modulo in isolamento.
    demo_coords = {
        "A": (41.1306, 16.8694),
        "B": (41.1275, 16.8711),
        "C": (41.1219, 16.8703),
        "D": (41.1255, 16.8775),
        "E": (41.1290, 16.8716),
    }
    order, cost = astar_route(demo_coords, start_id="A")
    print("Ordine di visita ottimo:", order)
    print(f"Distanza totale: {cost:.0f} m")
