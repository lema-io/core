"""LEMA Off-Grid interface."""
from datetime import timedelta
import logging
import asyncio

# Bring in CoAP
from aiocoap import *

import voluptuous as vol

from homeassistant.components.switch import PLATFORM_SCHEMA
from homeassistant.const import (
    CONF_HOST,
    CONF_FRIENDLY_NAME,
    CONF_SCAN_INTERVAL,
    POWER_WATT,
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

CONST_DEFAULT_SCAN_PERIOD_S = 60

# TODO figure out why entity_playform.py has self.scan_interval set to a string "7"
# ...seconds.  It's used once on boot but then our switch async_setup_platform
# completes and the exception never happens again.
# Seems like a race condition on init or we neet to setup something else that
# we are not doing.  See how platform is used in zwave.py
# must have to do with vol.Optional(CONF_SCAN_INTERVAL): cv.string
SCAN_INTERVAL = timedelta(seconds=CONST_DEFAULT_SCAN_PERIOD_S)

CONST_COAP_PROTOCOL = "coap://"
CONST_COAP_STRING_TRUE = "1"
CONST_COAP_STRING_FALSE = "0"

protocol = ""

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_FRIENDLY_NAME): cv.string,
        vol.Optional(CONF_SCAN_INTERVAL): cv.string
    }
)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up LEMA Off-Grid Unit Switchs."""

    host = config.get(CONF_HOST)

    # Use all switches by default
    hass_switches = []

    # Setup Async CoAP
    protocol = await Context.create_client_context()

    # Add switches
    hass_switches.append(LEMAIOSwitch(host, "io/r1", protocol, config.get(CONF_FRIENDLY_NAME) + " - Outlet 1", False, None))
    hass_switches.append(LEMAIOSwitch(host, "io/r2", protocol, config.get(CONF_FRIENDLY_NAME) + " - Outlet 2", False, None))

    # Add the entities
    async_add_entities(hass_switches)

    async def async_update_switches(event):
        """Update all the LEMA switches."""

        # Update sensors based on scan_period set below which comes in from the config
        for sw in hass_switches:
            await sw.async_update_values()

    # Call out an interval to poll data from CoAP endpoint
    # period_s = config.get(CONF_SCAN_INTERVAL)
    # if (period_s != None and float(period_s) > 0):
    #     print("Switch using scan period from config: " + str(period_s))
    #     scan_period = datetime.timedelta(seconds=float(period_s))
    # else:
    #     print("Switch using default scan period of: " + str(CONST_DEFAULT_SCAN_PERIOD_S))
    #     scan_period = datetime.timedelta(seconds=CONST_DEFAULT_SCAN_PERIOD_S)

    #print("Note there's a silly exception shown here, but it's not actually an issue TODO... Type of scan_period = " + str(type(scan_period)))
    
    #datetime.timedelta(0,interval)
    #interval = config.get(CONF_SCAN_INTERVAL) or timedelta(seconds=5)
    
    async_track_time_interval(hass, async_update_switches, timedelta(seconds=5))

class LEMAIOSwitch(ToggleEntity):
    """Representation of a Digital Output."""

    def __init__(self, host, uri, protocol, name, unit, invert_logic):
        """Initialize the pin."""

        print("Init LEMA switch = " + uri)

        self._host = host
        self._uri = uri
        self._name = name
        self._unit = unit
        self._invert_logic = invert_logic
        self._state = False
        self._protocol = protocol
        self.async_turn_off()

    @property
    def name(self):
        """Return the name of the switch."""
        return self._name

    @property
    def should_poll(self):
        """Return the polling state."""
        return True

    @property
    def is_on(self):
        """Return true if device is on."""
        return self._state

    async def async_turn_on(self, **kwargs):
        """Turn the device on."""
        try:
            _LOGGER.info("LEMA calling TURN_ON for " + self._uri)
            request = Message(code=PUT, payload=CONST_COAP_STRING_TRUE.encode("ascii"), uri=CONST_COAP_PROTOCOL + self._host + "/" + self._uri)
            response = await self._protocol.request(request).response
            self._state = True
            self.schedule_update_ha_state()
        except Exception as e:
            _LOGGER.info("Failed to PUT resource: " + self._uri)
            _LOGGER.info(e)

    async def async_turn_off(self, **kwargs):
        """Turn the device off."""
        try:
            _LOGGER.info("LEMA calling TURN_OFF for " + self._uri)
            request = Message(code=PUT, payload=CONST_COAP_STRING_FALSE.encode("ascii"), uri=CONST_COAP_PROTOCOL + self._host + "/" + self._uri)
            response = await self._protocol.request(request).response
            self._state = False
            self.schedule_update_ha_state()
        except Exception as e:
            _LOGGER.info("Failed to PUT resource: " + self._uri)
            _LOGGER.info(e)

    @callback
    async def async_update_values(self):
        """Update this switch."""
        try:
            request = Message(code=GET, uri=CONST_COAP_PROTOCOL + self._host + "/" + self._uri)
            response = await self._protocol.request(request).response

            response_bool = False

            if (response.payload == b'1'):
                response_bool = True

            # Check for change
            if (self._state != response_bool):
                self._state = response_bool
                _LOGGER.info("%s changed: %s - %s" % (self._uri, response.code, str(response_bool)))
                self.async_write_ha_state()
            else:
                _LOGGER.info("%s no change..." % (self._uri))

        except Exception as e:
            _LOGGER.info("Failed to GET resource: " + self._uri)
            _LOGGER.info(e)

    @property
    def unique_id(self):
        """Return a unique identifier for this sensor."""
        return f"{self._name}"

