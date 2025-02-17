import logging
import requests
import base64
import uuid
import json

_LOGGER = logging.getLogger(__name__)

# 模块级别的全局变量
_ip_address = None
_auth_username = None
_auth_password = None
_iot_device_name = None
_gw_iot_name = None

def set_credentials(ip_address, auth_username, auth_password):
    """Set the global credentials and device names for API requests."""
    global _ip_address, _auth_username, _auth_password
    _ip_address = ip_address
    _auth_username = auth_username
    _auth_password = auth_password

def set_iot_credentials(iot_device_name, gw_iot_name):
    global _iot_device_name, _gw_iot_name
    _iot_device_name = iot_device_name
    _gw_iot_name = gw_iot_name

def get_iot_info():
    iot_info = make_api_request(None, "GET", "/route.cgi?api=profile.get")
    if not iot_info:
        _LOGGER.error("Failed to fetch iot info")
        return {}
    else:
        return {"iot_device_name": iot_info.get("iotDeviceName"), "gw_iot_name": iot_info.get("gwIotName")}

def get_device_states():
    device_states = make_api_request({"action": "readAllDevState"})
    if not device_states or "devList" not in device_states:
        _LOGGER.error("Failed to fetch device states")
        return []
    return device_states.get("devList")

def get_devices():
    device_states = get_device_states()
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
            (state for state in device_states if state.get("devNo") == dev_no and state.get("devCh") == dev_ch),
            None,
        )
        if state_info:
            device.update({
                "state": state_info.get("state", 0),  # 默认状态为关
                "level": state_info.get("level", 0),  # 默认level为0
            })
        devices.append(device)

    return devices

def make_api_request(payload=None, method="POST", endpoint="/route.cgi?api=request"):
    """Make an API request to the Dnake device."""
    if _ip_address is None or _auth_username is None or _auth_password is None:
        _LOGGER.error("API credentials are not set")
        return None

    url = f"http://{_ip_address}{endpoint}"
    
    auth_string = f"{_auth_username}:{_auth_password}".encode('utf-8')
    auth_b64 = base64.b64encode(auth_string).decode('utf-8')
    
    headers = {
        "Authorization": f"Basic {auth_b64}"
    }

    try:
        if method.upper() == "GET":
            response = requests.get(
                url, 
                headers=headers, 
                timeout=10,
                verify=False  # 如果设备使用自签名证书
            )
        elif method.upper() == "POST":
            if isinstance(payload, dict):
                payload.update({
                    "uuid": str(uuid.uuid4())
                })
                post_data = {
                    "fromDev": _iot_device_name,
                    "toDev": _gw_iot_name,
                    "data": payload
                }
                _LOGGER.debug("Sending POST request to %s with data: %s", url, json.dumps(post_data))
                response = requests.post(
                    url, 
                    headers=headers, 
                    json=post_data,
                    timeout=10,
                    verify=False
                )
            else:
                response = requests.post(
                    url, 
                    headers=headers, 
                    timeout=10,
                    verify=False
                )
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        response.raise_for_status()
        _LOGGER.debug("Response from %s: %s", url, response.text)
        return response.json()
    except requests.exceptions.RequestException as ex:
        _LOGGER.error("Error making API request to %s: %s", url, ex)
        _LOGGER.debug("Request headers: %s", headers)
        if 'response' in locals():
            _LOGGER.debug("Response status code: %s", response.status_code)
            _LOGGER.debug("Response text: %s", response.text)
        return None