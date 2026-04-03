# Client Ollama dedie.
# Ce module isole la logique reseau/cache pour reduire la charge CPU/RAM.

from __future__ import annotations

import hashlib
import subprocess
import sys
from typing import Any

try:
    import requests
except ModuleNotFoundError:
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "requests"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=120,
        )
    except Exception:
        pass
    try:
        import requests
    except Exception:
        requests = None


class OllamaClient:
    # Gestion centralisee des appels modele (JARVIS et NEO).
    def __init__(self, base_url: str, model: str, tags_url: str, low_resource_mode: bool = False):
        self.base_url = base_url
        self.tags_url = tags_url
        self.model = model
        self.low_resource_mode = bool(low_resource_mode)
        # Session HTTP re-utilisee pour eviter les couts de connexion repetes.
        self._session = requests.Session() if requests is not None else None
        # Cache court en memoire pour eviter de recalculer des prompts identiques.
        self._response_cache: dict[str, str] = {}
        self._response_cache_order: list[str] = []
        self._cache_limit = 48

    def set_model(self, model: str) -> None:
        self.model = model

    def set_low_resource_mode(self, enabled: bool) -> None:
        self.low_resource_mode = bool(enabled)

    def check_connection(self) -> tuple[bool, str]:
        if self._session is None:
            return False, "Dependency 'requests' missing for Ollama HTTP client."
        try:
            res = self._session.get(self.tags_url, timeout=3)
            res.raise_for_status()
            return True, ""
        except Exception as exc:
            return False, str(exc)

    def list_models(self) -> list[str]:
        if self._session is None:
            return []
        try:
            res = self._session.get(self.tags_url, timeout=5)
            res.raise_for_status()
            data: dict[str, Any] = res.json()
            return [m.get("name") for m in data.get("models", []) if m.get("name")]
        except Exception:
            return []

    def generate(self, prompt: str) -> str:
        if self._session is None:
            raise RuntimeError("Dependency 'requests' missing. Install with: python -m pip install requests")
        prompt = str(prompt or "")
        cache_key = hashlib.sha1((self.model + "|" + prompt).encode("utf-8", errors="ignore")).hexdigest()
        cached = self._response_cache.get(cache_key)
        if cached:
            return cached

        # Parametres plus legers en mode low_resource_mode.
        options = {
            "temperature": 0.35 if self.low_resource_mode else 0.55,
            "num_predict": 220 if self.low_resource_mode else 320,
            "num_ctx": 1536 if self.low_resource_mode else 2304,
            "top_k": 24 if self.low_resource_mode else 40,
        }
        timeout_s = 75 if self.low_resource_mode else 110

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": options,
        }
        res = self._session.post(self.base_url, json=payload, timeout=timeout_s)
        res.raise_for_status()
        out = res.json().get("response", "")
        if out:
            self._response_cache[cache_key] = out
            self._response_cache_order.append(cache_key)
            if len(self._response_cache_order) > self._cache_limit:
                old_key = self._response_cache_order.pop(0)
                self._response_cache.pop(old_key, None)
        return out
