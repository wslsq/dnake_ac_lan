import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform
from .utils import set_credentials, set_iot_credentials

_LOGGER = logging.getLogger(__name__)

# 定义支持的平台
PLATFORMS = [Platform.LIGHT, Platform.COVER]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Dnake devices from a config entry."""
    # 设置全局配置
    ip_address = entry.data["ip_address"]
    auth_username = entry.data["auth_username"]
    auth_password = entry.data["auth_password"]
    set_credentials(ip_address, auth_username, auth_password)

    iot_device_name = entry.data["iot_device_name"]
    gw_iot_name = entry.data["gw_iot_name"]
    set_iot_credentials(iot_device_name, gw_iot_name)
    
    # 使用 async_forward_entry_setups 设置平台
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    # 卸载平台
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    return unload_ok