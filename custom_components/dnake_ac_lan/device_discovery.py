import logging
from .utils import make_api_request

_LOGGER = logging.getLogger(__name__)

def fetch_devices():
    """Fetch the list of devices and their states from the Dnake API."""

    # 获取设备状态
    device_states = make_api_request({"action": "readAllDevState"})
    if not device_states or "devList" not in device_states:
        _LOGGER.error("Failed to fetch device states")
        return []

    # 获取设备列表
    device_list = make_api_request(None, method="GET", endpoint="/smart/speDev.info")
    if not device_list:
        _LOGGER.error("Failed to fetch device list")
        return []

    # 将设备状态与设备列表匹配
    devices = []
    for device in device_list.get("dl"):
        dev_no = device.get("nm")
        dev_ch = device.get("ch")
        # 查找匹配的设备状态
        state_info = next(
            (state for state in device_states["devList"] if state["devNo"] == dev_no and state["devCh"] == dev_ch),
            None,
        )
        if state_info:
            device.update({
                "state": state_info.get("state", 0),  # 默认状态为关
                "level": state_info.get("level", 0),  # 默认level为0
            })
        devices.append(device)

    return devices