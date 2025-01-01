"""Support for Aruba Instant On Access Points."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import TYPE_CHECKING, Any

import homeassistant.helpers.config_validation as cv
import httpx
import voluptuous as vol
from homeassistant.components.device_tracker import (
    DOMAIN,
    DeviceScanner,
)
from homeassistant.components.device_tracker import (
    PLATFORM_SCHEMA as DEVICE_TRACKER_PLATFORM_SCHEMA,
)
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.util import Throttle

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.typing import ConfigType
from ion_client import Client

from .consts import CONF_SITE_ID

_LOGGER = logging.getLogger(__name__)
MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=30)

PLATFORM_SCHEMA = DEVICE_TRACKER_PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Required(CONF_SITE_ID): cv.string,
    }
)


def get_scanner(
    _hass: HomeAssistant, config: ConfigType
) -> ArubaInstantOnDeviceScanner | None:
    """Validate the configuration and return a Aruba Instant On scanner."""
    scanner = ArubaInstantOnDeviceScanner(config[DOMAIN])

    return scanner if scanner.success_init else None


class ArubaInstantOnDeviceScanner(DeviceScanner):
    """Query the Aruba Instant On API for connected devices."""

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize the scanner."""
        self.client = Client(
            username=config[CONF_USERNAME],
            password=config[CONF_PASSWORD],
        )
        self.site_id = config[CONF_SITE_ID]
        self.last_results: dict[str, dict[str, str]] = {}
        self.success_init = self._update_info()

    def scan_devices(self) -> list[str]:
        """Scan for new devices and return a list with found device IDs."""
        self._update_info()
        return list(self.last_results)

    def get_device_name(self, device: str) -> str | None:
        """Return the name of the given device or None if we don't know."""
        return self.last_results.get(device, {}).get("name")

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def _update_info(self) -> bool:
        """
        Ensure the information from the Aruba Instant On API is up to date.

        Return true if scanning successful.
        """
        try:
            clients = self.client.json(f"/sites/{self.site_id}/clientSummary")
            self.last_results = {
                client["id"]: {"mac": client["id"], "name": client["name"]}
                for client in clients.get("elements", [])
            }
        except httpx.HTTPError as e:
            _LOGGER.exception("Aruba Instant On API error", exc_info=e)
            return False

        return True
