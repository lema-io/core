"""LEMA Off-Grid interface."""
from datetime import timedelta
import logging
import asyncio

from aiocoap import *

import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PATH,
    CONF_SCAN_INTERVAL,
    CONF_SSL,
    CONF_VERIFY_SSL,
    EVENT_HOMEASSISTANT_STOP,
)
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_track_time_interval

_LOGGER = logging.getLogger(__name__)

CONF_CUSTOM = "custom"
CONF_FACTOR = "factor"
CONF_GROUP = "group"
CONF_KEY = "key"
CONF_SENSORS = "sensors"
CONF_UNIT = "unit"

GROUPS = ["user", "installer"]

protocol = ""

PLATFORM_SCHEMA = vol.All(
    PLATFORM_SCHEMA.extend(
        {
            vol.Required(CONF_HOST): cv.string,
            # vol.Optional(CONF_SSL, default=False): cv.boolean,
            # vol.Optional(CONF_VERIFY_SSL, default=True): cv.boolean,
            vol.Required(CONF_PASSWORD): cv.string
            # vol.Optional(CONF_GROUP, default=GROUPS[0]): vol.In(GROUPS),
            # vol.Optional(CONF_SENSORS, default=[]): vol.Any(
            #    cv.schema_with_slug_keys(cv.ensure_list),  # will be deprecated
            #    vol.All(cv.ensure_list, [str]),
            # ),
            # vol.Optional(CONF_CUSTOM, default={}): cv.schema_with_slug_keys(
            #    CUSTOM_SCHEMA
            # ),
        },
        extra=vol.PREVENT_EXTRA,
    )
)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up LEMA Off-Grid Unit."""

    host = config.get(CONF_HOST)

    # Init all default sensors
    # sensor_def = pysma.Sensors()

    # Sensor from the custom config
    # sensor_def.add(
    #    [
    #        pysma.Sensor(o[CONF_KEY], n, o[CONF_UNIT], o[CONF_FACTOR], o.get(CONF_PATH))
    #        for n, o in config[CONF_CUSTOM].items()
    #    ]
    # )

    # Use all sensors by default
    hass_sensors = []

    # Setup Async CoAP
    protocol = await Context.create_client_context()

    hass_sensors.append(LEMAOffGrid("led/blue", host, protocol))

    async_add_entities(hass_sensors)

    # Init the SMA interface

    backoff = 0
    backoff_step = 0

    async def async_lema(event):
        """Update all the LEMA sensors."""

        # Check for new data
        for sensor in hass_sensors:
            await sensor.async_update_values()

    # Call out an interval to poll data from CoAP endpoint
    # interval = config.get(CONF_SCAN_INTERVAL) or timedelta(seconds=5)
    interval = timedelta(seconds=0.5)

    print("LEMA scan interval: " + str(interval))

    async_track_time_interval(hass, async_lema, interval)


class LEMAOffGrid(Entity):
    """Representation of a LEMA Off-Grid Solar Power Supply."""

    def __init__(self, uri, host, protocol):
        """Initialize the sensor."""
        self._uri = uri
        self._name = "lema-off-grid"
        self._uri = ""
        self._value = 0
        self._unit = "no units..."
        self._attr = {"20"}
        # self._attr = {s.name: "" for s in sub_sensors}
        self._state = self._value
        self._host = host
        self._protocol = protocol

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return self._unit

    @property
    def device_state_attributes(self):  # Can be remove from 0.99
        """Return the state attributes of the sensor."""
        return self._attr

    @property
    def poll(self):
        """SMA sensors are updated & don't poll."""
        return False

    @callback
    async def async_update_values(self):
        """Update this sensor."""
        update = False

        print("LEMA async_update_values...")
        # for sens in self._sub_sensors:  # Can be remove from 0.99
        #    newval = f"{sens.value} {sens.unit}"
        #    if self._attr[sens.name] != newval:
        #        update = True
        #        self._attr[sens.name] = newval

        # if self._sensor.value != self._state:
        #    update = True
        #    self._state = self._sensor.value

        _LOGGER.info("LEMA calling coap")
        # if update:
        request = Message(code=GET, uri="coap://" + self._host + "/led/blue")

        try:
            response = await self._protocol.request(request).response
        except Exception as e:
            print("Failed to fetch resource:")
            print(e)
        else:
            print("Result: %s\n%r" % (response.code, response.payload))

            self._value = response.payload
            self._state = self._value
            self.async_write_ha_state()

    @property
    def unique_id(self):
        """Return a unique identifier for this sensor."""
        return f"leam-{self._uri}-{self._name}"
