# 狄耐克(Dnake)非官方HomeAssistant集成

使用HA，通过狄耐克门禁的内网api，控制室内狄耐克的设备，如灯控、窗帘。

**因设备有限，只接入了灯控和窗帘，要接入更多设备欢迎提pr。(可参考以下链接的参数)**
https://bbs.hassbian.com/thread-28476-1-1.html

---

## 安装方式

### 1. 安装集成

将集成（`dnake_ac_lan`文件夹）复制到HA的`/config/custom_components`目录，并重启HA。

### 2. 配置集成

进入 **HA -> 设置 -> 添加集成**，搜索`dnake_ac_lan`并配置以下信息：

- 门禁IP地址：门禁局域网IP地址如192.168.1.8
- 门禁用户名：默认为admin
- 门禁密码：默认为123456
- 本地 IOT 名称：从门禁设置查看
- 网关 IOT 名称：从门禁设置查看
- 状态刷新间隔（秒）：本插件目前是通过轮询的方式获取设备状态，过于频繁的请求状态可能会使设备负载过高。默认30

---

## 相关项目

**dnake接入HA控制门禁开关、查看rtsp流、控制电梯等**
https://github.com/xswxm/home-assistant-dnake