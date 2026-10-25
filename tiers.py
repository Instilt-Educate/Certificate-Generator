"""Award tier definitions, fetched from the Tutor-Timings API.

The Notion "Volunteer Hours Award Tiers" database is the source of truth. This
module only reads it (via /getAwardTiers) and never defines tiers itself.
"""
import logging
import os
import time

import requests

API_BASE = os.environ.get("TUTOR_TIMINGS_API_URL", "https://tutor-timings.vercel.app").rstrip("/")

CACHE_TTL_SECONDS = 60
REQUEST_TIMEOUT_SECONDS = 15

_cache = {"fetched_at": 0.0, "tiers": None}


class TiersUnavailable(Exception):
    """Raised when tiers cannot be loaded and there is no cached copy to fall back on."""


def _describe(tier):
    """Add display fields derived from the hour bounds.

    Minimum hours are inclusive and maximum hours exclusive, so a tier covering
    [50, 101) is shown as "50-100 hours". The top tier has no maximum.
    """
    low = tier["min_hours"]
    high = tier.get("max_hours")
    if high is None:
        hours = f"{low:g}+ hours"
    else:
        hours = f"{low:g}–{high - 1:g} hours"
    return {**tier, "hours_range": hours, "label": f"{tier['name']} ({hours})"}


def get_tiers(force_refresh=False):
    """Active tiers in sort order. Cached briefly; a stale copy is used if the API is down."""
    now = time.monotonic()
    fresh = _cache["tiers"] is not None and now - _cache["fetched_at"] < CACHE_TTL_SECONDS
    if fresh and not force_refresh:
        return _cache["tiers"]

    try:
        response = requests.get(f"{API_BASE}/getAwardTiers", timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        tiers = [_describe(t) for t in response.json() if t.get("key")]
        tiers.sort(key=lambda t: (t.get("sort_order") is None, t.get("sort_order") or 0))
    except (requests.RequestException, ValueError, KeyError, TypeError) as e:
        if _cache["tiers"] is not None:
            logging.warning(f"Could not refresh award tiers ({e}); using cached copy")
            return _cache["tiers"]
        raise TiersUnavailable(str(e)) from e

    _cache["tiers"] = tiers
    _cache["fetched_at"] = now
    return tiers


def get_tier(key):
    """The active tier with this key, or None. Keys are case-insensitive."""
    if not key:
        return None
    wanted = key.strip().lower()
    return next((t for t in get_tiers() if t["key"].lower() == wanted), None)
