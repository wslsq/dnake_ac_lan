import voluptuous as vol
from homeassistant import config_entries
from .utils import set_credentials, get_iot_info
import logging

_LOGGER = logging.getLogger(__name__)

class DnakeConfigFlow(config_entries.ConfigFlow, domain="dnake_ac_lan"):
    """Handle a config flow for Dnake."""
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        default_values = {
            "ip_address": "192.168.1.8",
            "auth_username": "admin",
            "auth_password": "123456",
            "scan_interval": 30
        }

        if user_input is not None:
            # 验证用户输入
            ip_address = user_input["ip_address"]
            auth_username = user_input["auth_username"]
            auth_password = user_input["auth_password"]

            # 设置全局配置
            set_credentials(ip_address, auth_username, auth_password)

            # 测试连接
            iot_info = await self.hass.async_add_executor_job(get_iot_info)
            if iot_info != {}:
                user_input["iot_device_name"] = iot_info.get("iot_device_name")
                user_input["gw_iot_name"] = iot_info.get("gw_iot_name")
                return self.async_create_entry(title="Dnake Devices", data=user_input)
            else:
                errors["base"] = "cannot_connect"

        # 显示配置表单
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("ip_address", default=default_values["ip_address"]): str,
                vol.Required("auth_username", default=default_values["auth_username"]): str,
                vol.Required("auth_password", default=default_values["auth_password"]): str,
                vol.Optional("scan_interval", default=default_values["scan_interval"]): int,
            }),
            errors=errors,
        )
