# debug.py
from __future__ import annotations
import logging
from typing import Dict

class Debug:
    _root_configured: bool = False          # class-level guard

    def __init__(self, *, log_to: str | None = None) -> None:
        """
        If `log_to` is given, messages also stream to that file.
        Multiple Debug() instances share the same root logger config.
        """
        if not Debug._root_configured:
            handlers: list[logging.Handler] = [logging.StreamHandler()]
            if log_to:
                handlers.append(logging.FileHandler(log_to, encoding="utf-8"))

            logging.basicConfig(
                level=logging.DEBUG,
                format="[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
                handlers=handlers,
            )
            Debug._root_configured = True

        self.logger = logging.getLogger("INOP")
        self.enabled = True        # global switch

        # default component map
        self.components: Dict[str, bool] = {
            "keyboard":   False,
            "plugboard":  False,
            "rotor":      False,
            "reflector":  False,
            "stepping":   False,
            "encipher":   False,
        }

    # ── logging API ──────────────────────────────────────────────
    def log(self, component: str, message: str) -> None:
        if self.enabled and self.components.get(component, False):
            self.logger.debug("[%s] %s", component.upper(), message)

    # ── component toggles ────────────────────────────────────────
    def enable(self, *components: str) -> None:
        for c in components:
            self._require(c)
            self.components[c] = True

    def disable(self, *components: str) -> None:
        for c in components:
            self._require(c)
            self.components[c] = False

    def toggle(self, component: str) -> None:
        self._require(component)
        self.components[component] = not self.components[component]

    def toggle_global(self, state: bool) -> None:
        """Switch every component on/off at once."""
        self.enabled = state

    def status(self) -> Dict[str, bool]:
        """Return a *copy* of the current component map."""
        return self.components.copy()

    # ── helpers ──────────────────────────────────────────────────
    def _require(self, component: str) -> None:
        if component not in self.components:
            raise ValueError(f"No such component: {component!r}")

    # nicety for `print(dbg)`
    def __repr__(self) -> str:
        active = [k for k, v in self.components.items() if v]
        return f"<Debug enabled={self.enabled} active={active}>"