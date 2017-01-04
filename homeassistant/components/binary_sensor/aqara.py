from homeassistant.loader import get_component
from homeassistant.components.binary_sensor import (SENSOR_CLASSES, BinarySensorDevice)

DEPENDENCIES = ['aqara']

aqara = get_component('aqara')

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup the aqara platform for binary_sensors."""
    if discovery_info is None:
        return
    devices = []
    for sid, init_data in discovery_info["sensor_index"].items():
        sensor = AqaraContactSensor(sid, init_data)
        aqara.GATEWAY_FACTORY.subscribe_update(sid, sensor)
        devices.append(sensor)
    add_devices(devices)

class AqaraContactSensor(aqara.AbstractAqaraDevice, BinarySensorDevice):
    def __init__(self, sid, init_data):
        aqara.AbstractAqaraDevice.__init__(self, 'magnet', sid)
        self.data = init_data

    @property
    def is_on(self):
        return self.data["status"] == "open"
