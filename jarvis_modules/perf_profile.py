# Profil performance runtime.
# Ce module calcule les intervalles en fonction du mode leger.

from __future__ import annotations

from typing import Any


def build_runtime_intervals(config: dict[str, Any], low_resource_mode: bool, auto_monitor_interval_ms_default: int) -> dict[str, int]:
    # Valeurs par defaut plus douces pour les machines modestes.
    default_monitor_ms = 30000 if low_resource_mode else auto_monitor_interval_ms_default
    default_netmap_refresh_ms = 60000 if low_resource_mode else 30000
    default_netmap_anim_ms = 500 if low_resource_mode else 250

    auto_monitor_ms = max(8000, int(config.get("auto_monitor_interval_ms", default_monitor_ms)))
    netmap_refresh_ms = max(15000, int(config.get("netmap_refresh_interval_ms", default_netmap_refresh_ms)))
    netmap_anim_ms = max(180, int(config.get("netmap_anim_interval_ms", default_netmap_anim_ms)))

    return {
        "auto_monitor_interval_ms": auto_monitor_ms,
        "netmap_refresh_interval_ms": netmap_refresh_ms,
        "netmap_anim_interval_ms": netmap_anim_ms,
    }
