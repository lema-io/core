"""LEMA Off-Grid interface."""
from datetime import timedelta
import logging
import asyncio

# Bring in CoAP
from aiocoap import *

import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    CONF_HOST,
    CONF_FRIENDLY_NAME,
    CONF_SCAN_INTERVAL,
    POWER_WATT,
    VOLT,
    PERCENTAGE,
    TIME_SECONDS,
    TEMP_CELSIUS,
    ENERGY_KILO_WATT_HOUR,
    EVENT_HOMEASSISTANT_STOP,
)
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity import ToggleEntity
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.const import ATTR_NAME, DEVICE_DEFAULT_NAME

_LOGGER = logging.getLogger(__name__)

CONST_DEFAULT_SCAN_PERIOD_S = 60.0

CONST_COAP_PROTOCOL = "coap://"
CONST_COAP_STRING_TRUE = "1"
CONST_COAP_STRING_FALSE = "1"

protocol = ""

PLATFORM_SCHEMA = vol.All(
    PLATFORM_SCHEMA.extend(
        {
            vol.Required(CONF_HOST): cv.string,
            vol.Required(CONF_FRIENDLY_NAME): cv.string,
            vol.Optional(CONF_SCAN_INTERVAL): cv.string
        },
        extra=vol.PREVENT_EXTRA,
    )
)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up LEMA Off-Grid Unit."""

    print("Set up LEMA Off-Grid Unit")

    host = config.get(CONF_HOST)

    # Use all sensors by default
    hass_sensors = []

    # Setup Async CoAP
    protocol = await Context.create_client_context()

    # Add sensors
    #hass_sensors.append(LEMAOffGridSensor(host, "led/blue", protocol, config.get(CONF_FRIENDLY_NAME) + " - Blue Led", None))
    hass_sensors.append(LEMAOffGridSensor(host, "inv/w", protocol, config.get(CONF_FRIENDLY_NAME) + " - Inverter Watts", POWER_WATT, 0))
    hass_sensors.append(LEMAOffGridSensor(host, "inv/vac", protocol, config.get(CONF_FRIENDLY_NAME) + " - Inverter Volts AC", "VAC", 1))
    hass_sensors.append(LEMAOffGridSensor(host, "inv/a", protocol, config.get(CONF_FRIENDLY_NAME) + " - Inverter Amps", "Amps", 1))
    hass_sensors.append(LEMAOffGridSensor(host, "cc/w", protocol, config.get(CONF_FRIENDLY_NAME) + " - PV Watts", POWER_WATT, 0))
    hass_sensors.append(LEMAOffGridSensor(host, "cc/v", protocol, config.get(CONF_FRIENDLY_NAME) + " - PV Volts DC", VOLT, 2))
    hass_sensors.append(LEMAOffGridSensor(host, "cc/a", protocol, config.get(CONF_FRIENDLY_NAME) + " - PV Amps", "Amps", 1))
    hass_sensors.append(LEMAOffGridSensor(host, "bat/w", protocol, config.get(CONF_FRIENDLY_NAME) + " - Battery Watts", POWER_WATT, 0))
    hass_sensors.append(LEMAOffGridSensor(host, "bat/a", protocol, config.get(CONF_FRIENDLY_NAME) + " - Battery Amps", "Amps", 1))
    hass_sensors.append(LEMAOffGridSensor(host, "bat/v", protocol, config.get(CONF_FRIENDLY_NAME) + " - Battery Volts DC", VOLT, 1))
    hass_sensors.append(LEMAOffGridSensor(host, "bat/level_percent", protocol, config.get(CONF_FRIENDLY_NAME) + " - Battery Level Percent", PERCENTAGE, 1))
    hass_sensors.append(LEMAOffGridSensor(host, "bat/time_remaining_s", protocol, config.get(CONF_FRIENDLY_NAME) + " - Battery Time Remaining", TIME_SECONDS, 0))
    hass_sensors.append(LEMAOffGridSensor(host, "bat/temperature_deg_c", protocol, config.get(CONF_FRIENDLY_NAME) + " - Battery Temperature", TEMP_CELSIUS, 1))

    print("Adding LEMA sensors done")

    async_add_entities(hass_sensors)

    print("async_add_entities done")

    async def async_update_sensors(event):
        """Update all the LEMA sensors."""

        # Update sensors based on scan_period set below which comes in from the config
        for sensor in hass_sensors:
            await sensor.async_update_values()

    # Call out an interval to poll data from CoAP endpoint
    #period_s = config.get(CONF_SCAN_INTERVAL)
    #if (period_s != None and float(period_s) > 0):
    #    print("Sensor using scan period from config: " + str(period_s))
    #    scan_period = timedelta(seconds=float(period_s))
    #else:
    #    print("Sensor using default scan period of: " + str(CONST_DEFAULT_SCAN_PERIOD_S))
    #    scan_period = timedelta(seconds=CONST_DEFAULT_SCAN_PERIOD_S)

    async_track_time_interval(hass, async_update_sensors, timedelta(seconds=5))

class LEMAOffGridSensor(Entity):
    """Representation of a LEMA Off-Grid Solar Power Supply Sensor."""

    def __init__(self, host, uri, protocol, name, unit, round_places):
        """Initialize the sensor."""

        print("Init Sensor " + uri)
        
        self._uri = uri
        self._name = name
        self._unit = unit
        self._round_places = round_places
        self._state = "0.0"
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
    def poll(self):
        """LEMA sensors are polled."""
        return True

    @callback
    async def async_update_values(self):
        """Update this sensor."""
        try:

            #print("Update2: " + self._uri)
            #_LOGGER.info("Update: " + self._uri)

            request = Message(code=GET, uri=CONST_COAP_PROTOCOL + self._host + "/" + self._uri)
            response = await self._protocol.request(request).response

            # Check for change
            if (self._state != float(response.payload)):
                # Round result to make the ui look nice
                self._state = round(float(response.payload), self._round_places)
                #_LOGGER.info("%s changed: %s - %r" % (self._uri, response.code, self._state))
                self.async_write_ha_state()
            else:
               #_LOGGER.info("%s no change... current value = %s" % (self._uri, self._state))

        except Exception as e:
            _LOGGER.info("Exception - Failed to GET resource: " + self._uri)
            _LOGGER.info(e)

    @property
    def unique_id(self):
        """Return a unique identifier for this sensor."""
        return f"{self._name}"

