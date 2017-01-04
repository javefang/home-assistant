import json
import logging

from homeassistant.helpers.entity import Entity
from homeassistant.components.discovery import load_platform
import aqara.aqara as aqara

DOMAIN = 'aqara'
REQUIREMENTS = [
  'https://github.com/javefang/pyaqara/archive/'
  '0.2.0.zip#aqara==0.2.0']

_LOGGER = logging.getLogger(__name__)

GATEWAY_FACTORY = None

# AQARA_SENSOR_CLASSES
S_MOTION = "motion"
S_MAGNET = "magnet"
S_SENSOR_HT = "sensor_ht"
S_SWITCH = "switch"

SENSOR_CLASS_MAP = {
    # S_MOTION: 'binary_sensor',
    S_MAGNET: 'binary_sensor',
    # S_SENSOR_HT: 'sensor'
}

def async_setup(hass, config):

    """Setup the Aqara component."""
    global GATEWAY_FACTORY
    GATEWAY_FACTORY = AqaraGatewayFactory(hass)
    yield from GATEWAY_FACTORY.start(hass.loop)
    return True

"""Aqara Gateway Implementation"""
class AqaraGatewayFactory(aqara.AbstractAqaraEventHandler):
    def __init__(self, hass):
        self.sensor_reported = {}
        self.sensor_confirmed = {}
        self.sensor_by_class = {
            S_MOTION: {},
            S_MAGNET: {},
            S_SENSOR_HT: {},
            S_SWITCH: {},
        }
        self.sensor_cb_index = {}
        self.hass = hass
        self.hass_initialized = False

    def handle_new_device_list(self, gateway_sid, sids):
        for sid in sids:
            if sid in self.sensor_reported:
                _LOGGER.info("Ignore already added sensor sid=%s", sid)
                continue
            self.sensor_reported[sid] = gateway_sid
            _LOGGER.debug("Sensor reported: sid=%s", sid)

    def handle_read_ack(self, model, sid, data):
        if sid not in self.sensor_reported:
            _LOGGER.warning("Ignore unknown sensor sid=%s", sid)
            return
        self.sensor_confirmed[sid] = (model, sid, data)
        self.sensor_by_class[model][sid] = data
        _LOGGER.debug("Sensor confirmed: sid=%s", sid)
        if self.check_all_sensors_discovered():
            self.init_hass()

    def handle_report(self, model, sid, data):
        if sid not in self.sensor_cb_index:
            _LOGGER.warning("Ignore non-subscribed sensor sid=%s", sid)
            return
        sensor = self.sensor_cb_index[sid]
        sensor.aqara_update(data)

    def check_all_sensors_discovered(self):
        sensor_reported_count = len(self.sensor_reported.keys())
        sensor_confirmed_count = len(self.sensor_confirmed.keys())
        return sensor_reported_count == sensor_confirmed_count

    def init_hass(self):
        if self.hass_initialized:
            return
        _LOGGER.debug("All sensor confirmed, initializing hass")
        for sensor_class in SENSOR_CLASS_MAP.keys():
            hass_sensor_type = SENSOR_CLASS_MAP[sensor_class]
            sensor_index = self.sensor_by_class[sensor_class]
            _LOGGER.debug('Loading platform: type=%s, domain=aqara, sensor_count=%s', hass_sensor_type, len(sensor_index.values()))
            load_platform(self.hass, hass_sensor_type, DOMAIN, { "sensor_index": sensor_index})
        self.hass_initialized = True

    def subscribe_update(self, sid, aqara_device):
        _LOGGER.debug("Subscrib sensor update: sid=%s", sid)
        self.sensor_cb_index[sid] = aqara_device

class AbstractAqaraDevice(Entity):
    def __init__(self, model, sid):
        self.sid = sid
        self.model = model
        self.data = None
        self._name = "{}_{}".format(model, sid)

    @property
    def should_poll(self):
        return False

    @property
    def name(self):
        return self._name

    def aqara_update(self, data):
        self.data = data
        _LOGGER.info("SensorUpdate: model=%s, sid=%s, data=%s", self.model, self.sid, json.dumps(data))
        self.schedule_update_ha_state()
