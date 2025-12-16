import csv
import os
import re
from collections import defaultdict
from functools import lru_cache
from typing import Dict, List, Optional


def _normalize_name(name: str) -> str:
    """Return a comparable subway stop key."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


class GTFSData:
    """Utility for loading stop + trip metadata from the static GTFS snapshot."""

    def __init__(self, root: Optional[str] = None) -> None:
        default_root = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "FinalProj",
            "gtfs_subway",
        )
        self.root = root or os.environ.get("GTFS_SUBWAY_DIR", default_root)

        self.stops_by_id: Dict[str, Dict[str, str]] = {}
        self.routes_by_id: Dict[str, Dict[str, str]] = {}
        self.trips_by_route: Dict[str, List[str]] = defaultdict(list)
        self.stop_sequences: Dict[str, List[str]] = {}

        self._loaded = False

    def _open_csv(self, filename: str):
        return open(os.path.join(self.root, filename), newline="", encoding="utf-8")

    def load(self) -> None:
        if self._loaded:
            return

        self._load_stops()
        self._load_routes()
        self._load_trips()
        self._load_stop_times()
        self._loaded = True

    def _load_stops(self) -> None:
        with self._open_csv("stops.txt") as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.stops_by_id[row["stop_id"]] = row

    def _load_routes(self) -> None:
        with self._open_csv("routes.txt") as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.routes_by_id[row["route_id"]] = row

    def _load_trips(self) -> None:
        with self._open_csv("trips.txt") as f:
            reader = csv.DictReader(f)
            for row in reader:
                route_id = row["route_id"]
                self.trips_by_route[route_id].append(row["trip_id"])

    def _load_stop_times(self) -> None:
        sequences: Dict[str, List[str]] = defaultdict(list)
        with self._open_csv("stop_times.txt") as f:
            reader = csv.DictReader(f)
            for row in reader:
                trip_id = row["trip_id"]
                stop_id = row["stop_id"]
                sequences[trip_id].append((int(row["stop_sequence"]), stop_id))

        for trip_id, seq in sequences.items():
            seq.sort(key=lambda item: item[0])
            self.stop_sequences[trip_id] = [stop_id for _, stop_id in seq]

    def _display_name(self, stop_id: str) -> Optional[str]:
        stop = self.stops_by_id.get(stop_id)
        if not stop:
            return None
        parent_station = stop.get("parent_station")
        if parent_station:
            parent = self.stops_by_id.get(parent_station)
            if parent:
                return parent.get("stop_name")
        return stop.get("stop_name")

    @lru_cache(maxsize=256)
    def stop_sequence_for_route(
        self,
        route_short_name: str,
        origin_name: str,
        destination_name: str,
    ) -> Optional[List[str]]:
        """Attempt to pull the stop list from the GTFS snapshot."""

        self.load()
        route_short = _normalize_name(route_short_name)
        origin_key = _normalize_name(origin_name)
        destination_key = _normalize_name(destination_name)

        if not route_short or not origin_key or not destination_key:
            return None

        candidates = [
            route_id
            for route_id, route in self.routes_by_id.items()
            if _normalize_name(route.get("route_short_name", "")) == route_short
        ]
        if not candidates:
            return None

        for route_id in candidates:
            for trip_id in self.trips_by_route.get(route_id, []):
                stops = self.stop_sequences.get(trip_id)
                if not stops:
                    continue

                names = [self._display_name(stop_id) or stop_id for stop_id in stops]
                normalized = [_normalize_name(n) for n in names]

                try:
                    start_idx = normalized.index(origin_key)
                    end_idx = normalized.index(destination_key)
                except ValueError:
                    continue

                if start_idx < end_idx:
                    return names[start_idx : end_idx + 1]

        return None

    def list_all_stops(self) -> List[str]:
        self.load()
        return sorted({stop.get("stop_name") for stop in self.stops_by_id.values() if stop.get("stop_name")})
