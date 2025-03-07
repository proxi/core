"""Test deCONZ gateway."""

from unittest.mock import patch

import pydeconz
from pydeconz.websocket import State
import pytest
from syrupy import SnapshotAssertion

from homeassistant.components import ssdp
from homeassistant.components.deconz.config_flow import DECONZ_MANUFACTURERURL
from homeassistant.components.deconz.const import DOMAIN as DECONZ_DOMAIN
from homeassistant.components.deconz.errors import AuthenticationRequired, CannotConnect
from homeassistant.components.deconz.hub import DeconzHub, get_deconz_api
from homeassistant.components.ssdp import (
    ATTR_UPNP_MANUFACTURER_URL,
    ATTR_UPNP_SERIAL,
    ATTR_UPNP_UDN,
)
from homeassistant.config_entries import SOURCE_SSDP
from homeassistant.const import STATE_OFF, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .conftest import BRIDGE_ID

from tests.common import MockConfigEntry


async def test_device_registry_entry(
    config_entry_setup: MockConfigEntry,
    device_registry: dr.DeviceRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Successful setup."""
    device_entry = device_registry.async_get_device(
        identifiers={(DECONZ_DOMAIN, config_entry_setup.unique_id)}
    )
    assert device_entry == snapshot


@pytest.mark.parametrize(
    "sensor_payload",
    [
        {
            "name": "presence",
            "type": "ZHAPresence",
            "state": {"presence": False},
            "config": {"on": True, "reachable": True},
            "uniqueid": "00:00:00:00:00:00:00:00-00",
        }
    ],
)
@pytest.mark.usefixtures("config_entry_setup")
async def test_connection_status_signalling(
    hass: HomeAssistant, mock_websocket_state
) -> None:
    """Make sure that connection status triggers a dispatcher send."""
    assert hass.states.get("binary_sensor.presence").state == STATE_OFF

    await mock_websocket_state(State.RETRYING)
    await hass.async_block_till_done()

    assert hass.states.get("binary_sensor.presence").state == STATE_UNAVAILABLE

    await mock_websocket_state(State.RUNNING)
    await hass.async_block_till_done()

    assert hass.states.get("binary_sensor.presence").state == STATE_OFF


async def test_update_address(
    hass: HomeAssistant, config_entry_setup: MockConfigEntry
) -> None:
    """Make sure that connection status triggers a dispatcher send."""
    gateway = DeconzHub.get_hub(hass, config_entry_setup)
    assert gateway.api.host == "1.2.3.4"

    with patch(
        "homeassistant.components.deconz.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        await hass.config_entries.flow.async_init(
            DECONZ_DOMAIN,
            data=ssdp.SsdpServiceInfo(
                ssdp_st="mock_st",
                ssdp_usn="mock_usn",
                ssdp_location="http://2.3.4.5:80/",
                upnp={
                    ATTR_UPNP_MANUFACTURER_URL: DECONZ_MANUFACTURERURL,
                    ATTR_UPNP_SERIAL: BRIDGE_ID,
                    ATTR_UPNP_UDN: "uuid:456DEF",
                },
            ),
            context={"source": SOURCE_SSDP},
        )
        await hass.async_block_till_done()

    assert gateway.api.host == "2.3.4.5"
    assert len(mock_setup_entry.mock_calls) == 1


async def test_reset_after_successful_setup(
    hass: HomeAssistant, config_entry_setup: MockConfigEntry
) -> None:
    """Make sure that connection status triggers a dispatcher send."""
    gateway = DeconzHub.get_hub(hass, config_entry_setup)

    result = await gateway.async_reset()
    await hass.async_block_till_done()

    assert result is True


async def test_get_deconz_api(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """Successful call."""
    with patch("pydeconz.DeconzSession.refresh_state", return_value=True):
        assert await get_deconz_api(hass, config_entry)


@pytest.mark.parametrize(
    ("side_effect", "raised_exception"),
    [
        (TimeoutError, CannotConnect),
        (pydeconz.RequestError, CannotConnect),
        (pydeconz.ResponseError, CannotConnect),
        (pydeconz.Unauthorized, AuthenticationRequired),
    ],
)
async def test_get_deconz_api_fails(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    side_effect: Exception,
    raised_exception: Exception,
) -> None:
    """Failed call."""
    with (
        patch(
            "pydeconz.DeconzSession.refresh_state",
            side_effect=side_effect,
        ),
        pytest.raises(raised_exception),
    ):
        assert await get_deconz_api(hass, config_entry)
