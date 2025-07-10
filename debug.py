import logging
from typing import Dict

class Debug:
    def __init__(self):
        logging.basicConfig(
            level=logging.DEBUG,
            format='[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.logger = logging.getLogger("INOP")
        self.enabled: bool = True
        self.components: Dict[str, bool] = {
            "keyboard": False,
            "plugboard": False,
            "rotor": False,
            "reflector": False,
            "stepping": False,
            "encypher": False,
        }

    def log(self, component: str, message: str) -> None:
        if self.enabled and self.components.get(component, False):
            self.logger.debug(f"[{component.upper()}] {message}")

    def enable(self, component: str) -> None:
        if component not in self.components:
            raise ValueError(f"No such component: '{component}'")
        self.components[component] = True

    def disable(self, component: str) -> None:
        if component not in self.components:
            raise ValueError(f"No such component: '{component}'")
        self.components[component] = False

    def toggle(self, component: str) -> None:
        if component not in self.components:
            raise ValueError(f"No such component: '{component}'")
        self.components[component] = not self.components[component]

    def toggle_global(self, state: bool) -> None:
        self.enabled = state

    def status(self) -> Dict[str, bool]:
        """Return the status of all debug components."""
        return self.components.copy()