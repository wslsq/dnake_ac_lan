import logging
from datetime import timedelta
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval, async_call_later
from homeassistant.components.cover import (
    CoverEntity,
    CoverEntityFeature
)
from .utils import make_api_request, fetch_devices

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
    scan_interval = entry.data.get("scan_interval", 30)
    
    async def async_update_devices(now=None):
        """更新所有设备状态."""
        _LOGGER.debug("Updating Dnake cover states")
        devices = await hass.async_add_executor_job(fetch_devices)
        for device in devices:
            if device.get("ty") == 514:  # 窗帘设备
                for cover in covers:
                    if cover._dev_no == device.get("nm") and cover._dev_ch == device.get("ch"):
                        current_level = device.get("level", 0)
                        cover._current_level = current_level
                        cover._is_closed = current_level == 0
                        cover.async_write_ha_state()

    # 首次更新
    await async_update_devices()
    
    # 设置定时更新
    async_track_time_interval(hass, async_update_devices, timedelta(seconds=scan_interval))

class DnakeCover(CoverEntity):
    """Representation of a Dnake Cover with position control."""

    def __init__(self, device):
        """Initialize the cover."""
        self._device = device
        self._name = device.get("na")
        self._current_level = device.get("level", 0)
        self._is_closed = self._current_level == 0
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
        return int((self._current_level / 254) * 100) if self._current_level is not None else None

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
        current_level = self.get_current_level()
        position = kwargs.get("position", 0)  # Position is 0-100
        level = int((position / 100) * 254)  # Convert to 0-254
        level = max(0, min(254, level))  # Ensure level is within range

        payload = {"cmd": "level", "action": "ctrlDev", "devNo": self._dev_no, "devCh": self._dev_ch, "level": level}
        response = make_api_request(payload=payload)
        if response is not None and response.get("result") == "ok":
            self._current_level = level
            self._is_opening = level > current_level
            self._is_closing = level < current_level
            self._is_closed = level == current_level

    def open_cover(self, **kwargs):
        """Open the cover."""
        self.set_cover_position(position=100)

    def close_cover(self, **kwargs):
        """Close the cover."""
        self.set_cover_position(position=0)

    def stop_cover(self, **kwargs):
        """Stop the cover."""
        payload = {"cmd": "stop", "action": "ctrlDev", "devNo": self._dev_no, "devCh": self._dev_ch}
        try:
            response = make_api_request(payload=payload)
            if response is not None and response.get("result") == "ok":
                current_level = self.get_current_level()
                self._current_level = current_level
                self._is_closed = current_level == 0
                self._is_opening = False
                self._is_closing = False 
        except Exception as ex:
            _LOGGER.error("Error stopping cover: %s", ex)


    async def async_update(self):
        """Fetch new state data for this light."""
        # 延迟 9 秒后执行实际更新逻辑
        async_call_later(self.hass, 9, self._async_delayed_update)

    def get_current_level(self):
        payload = {"action": "readDev", "devNo": self._dev_no, "devCh": self._dev_ch}
        try:
            response = make_api_request(payload=payload)
            if response is not None and response.get("result") == "ok":
                return response.get("level", 0)
        except Exception as ex:
            _LOGGER.error("Error getting cover level: %s", ex)
            return 0

    def _async_delayed_update(self, _):
        """Delayed update logic."""
        try:
            current_level = self.get_current_level()
            self._current_level = current_level
            self._is_closed = current_level == 0
            self._is_opening = False
            self._is_closing = False
        except Exception as ex:
            _LOGGER.error("Error updating cover state: %s", ex)