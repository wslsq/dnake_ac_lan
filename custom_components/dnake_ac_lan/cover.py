import logging
from datetime import timedelta
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.components.cover import (
    CoverEntity,
    CoverEntityFeature
)
from .device_discovery import fetch_devices
from .utils import make_api_request

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    """Set up Dnake covers from a config entry."""
    devices = await hass.async_add_executor_job(fetch_devices)
    if not devices:
        _LOGGER.error("No devices found")
        return

    covers = []
    for device in devices:
        if device.get("ty") == 514:  # 窗帘设备
            covers.append(DnakeCover(device))

    async_add_entities(covers)

    # 定时刷新设备状态
    scan_interval = timedelta(seconds=entry.data.get("scan_interval", 30))

    @callback
    def refresh_devices(event_time):
        """Refresh the state of all devices."""
        for cover in covers:
            cover.schedule_update_ha_state(force_refresh=True)

    # 注册定时任务
    entry.async_on_unload(
        async_track_time_interval(hass, refresh_devices, scan_interval)
    )

class DnakeCover(CoverEntity):
    """Representation of a Dnake Cover with position control."""

    def __init__(self, device):
        """Initialize the cover."""
        self._device = device
        self._name = device.get("na")
        self._current_position = device.get("level", 0)
        self._is_closed = self._current_position == 0
        self._is_opening = False
        self._is_closing = False
        self._dev_no = device.get("nm")
        self._dev_ch = device.get("ch")

    @property
    def name(self):
        """Return the display name of this cover."""
        return self._name

    @property
    def unique_id(self):
        """Return a unique ID for this cover."""
        return f"dnake_{self._dev_ch}_{self._dev_no}"
        
    @property
    def is_closed(self):
        """Return true if the cover is closed."""
        return self._is_closed

    @property
    def is_opening(self):
        """Return true if the cover is opening."""
        return self._is_opening

    @property
    def is_closing(self):
        """Return true if the cover is closing."""
        return self._is_closing

    @property
    def current_cover_position(self):
        """Return the current position of the cover."""
        return int((self._current_position / 254) * 100) if self._current_position is not None else None

    @property
    def supported_features(self):
        """Flag supported features."""
        return (
            CoverEntityFeature.OPEN 
            | CoverEntityFeature.CLOSE 
            | CoverEntityFeature.STOP 
            | CoverEntityFeature.SET_POSITION
        )

    def set_cover_position(self, **kwargs):
        """Move the cover to a specific position."""
        position = kwargs.get("position", 0)  # Position is 0-100
        level = int((position / 100) * 254)  # Convert to 0-254
        level = max(0, min(254, level))  # Ensure level is within range

        payload = {
            "cmd": "level", 
            "action": "ctrlDev", 
            "devNo": self._dev_no, 
            "devCh": self._dev_ch, 
            "level": level
        }
        response = make_api_request(payload=payload)
        if response is not None and response.get("result") == "ok":
            self._current_position = level
            self._is_opening = level > (self._current_position or 0)
            self._is_closing = level < (self._current_position or 254)
            self._is_closed = level == 0

    def open_cover(self, **kwargs):
        """Open the cover."""
        self.set_cover_position(position=100)

    def close_cover(self, **kwargs):
        """Close the cover."""
        self.set_cover_position(position=0)

    def stop_cover(self, **kwargs):
        """Stop the cover."""
        # 获取当前位置并保持在该位置
        current_position = self._current_position
        self.set_cover_position(position=int((current_position / 254) * 100))

    async def async_update(self):
        """Fetch new state data for this light."""
        # 延迟 6 秒后执行实际更新逻辑
        async_call_later(self.hass, 6, self._async_delayed_update)

    async def _async_delayed_update(self, _):
        """Delayed update logic."""
        devices = await self.hass.async_add_executor_job(fetch_devices)
        for device in devices:
            if device.get("nm") == self._dev_no and device.get("ch") == self._dev_ch:
                self._current_position = device.get("level", 0)
                self._is_closed = device.get("level", 0) == 0
                break