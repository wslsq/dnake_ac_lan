import logging
from datetime import timedelta
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval, async_call_later
from homeassistant.components.light import (
    LightEntity,
    ColorMode,
)
from .utils import make_api_request, fetch_devices

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    """Set up Dnake lights from a config entry."""
    devices = await hass.async_add_executor_job(fetch_devices)
    if not devices:
        _LOGGER.error("No devices found")
        return

    lights = []
    for device in devices:
        if device.get("ty") == 256:  # 灯具设备
            lights.append(DnakeLight(device))

    async_add_entities(lights)

    # 定时刷新设备状态
    scan_interval = entry.data.get("scan_interval", 30)
    
    async def async_update_devices(now=None):
        """更新所有设备状态."""
        _LOGGER.debug("Updating Dnake light states")
        devices = await hass.async_add_executor_job(fetch_devices)
        for device in devices:
            if device.get("ty") == 256:  # 灯具设备
                for light in lights:
                    if light._dev_no == device.get("nm") and light._dev_ch == device.get("ch"):
                        light._is_on = device.get("state") == 1
                        light.async_write_ha_state()

    # 首次更新
    await async_update_devices()
    
    # 设置定时更新
    async_track_time_interval(hass, async_update_devices, timedelta(seconds=scan_interval))

class DnakeLight(LightEntity):
    """Representation of a Dnake Light."""

    def __init__(self, device):
        """Initialize the light."""
        self._device = device
        self._name = device.get("na")
        self._is_on = device.get("state") == 1
        self._dev_no = device.get("nm")
        self._dev_ch = device.get("ch")
        self._attr_supported_color_modes = {ColorMode.ONOFF}
        self._attr_color_mode = ColorMode.ONOFF

    @property
    def name(self):
        """Return the display name of this light."""
        return self._name

    @property
    def unique_id(self):
        """Return a unique ID for this light."""
        return f"dnake_{self._dev_ch}_{self._dev_no}"

    @property
    def is_on(self):
        """Return true if light is on."""
        return self._is_on

    @property
    def supported_color_modes(self):
        """Return supported color modes."""
        return self._attr_supported_color_modes

    @property
    def color_mode(self):
        """Return the current color mode."""
        return self._attr_color_mode

    def turn_on(self, **kwargs):
        """Instruct the light to turn on."""
        payload = {"cmd": "on", "action": "ctrlDev", "devNo": self._dev_no, "devCh": self._dev_ch}
        response = make_api_request(payload=payload)
        if response is not None and response.get("result") == "ok":
            self._is_on = True

    def turn_off(self, **kwargs):
        """Instruct the light to turn off."""
        payload = {"cmd": "off", "action": "ctrlDev", "devNo": self._dev_no, "devCh": self._dev_ch}
        response = make_api_request(payload=payload)
        if response is not None and response.get("result") == "ok":
            self._is_on = False

    async def async_update(self):
        """Fetch new state data for this light."""
        # 延迟 2 秒后执行实际更新逻辑
        async_call_later(self.hass, 2, self._async_delayed_update)

    def _async_delayed_update(self, _):
        """Delayed update logic."""
        payload = {"action": "readDev", "devNo": self._dev_no, "devCh": self._dev_ch}
        try:
            response = make_api_request(payload=payload)
            if response is not None and response.get("result") == "ok":
                self._is_on = response.get("state") == 1
        except Exception as ex:
            _LOGGER.error("Error updating light state: %s", ex)
