"""Tests for diagnostics data."""

import pytest
from syrupy.assertion import SnapshotAssertion

from homeassistant.const import CONF_USERNAME
from homeassistant.core import HomeAssistant

from .const import VALID_ENTRY_DATA_CLOUD, VALID_ENTRY_DATA_SELF_HOSTED

from tests.common import MockConfigEntry
from tests.components.diagnostics import snapshot_get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


@pytest.mark.parametrize(
    "mock_config_entry_data",
    [VALID_ENTRY_DATA_CLOUD, VALID_ENTRY_DATA_SELF_HOSTED],
    ids=lambda data: data[CONF_USERNAME],
)
async def test_diagnostics(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    init_integration: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test diagnostics."""
    await snapshot_get_diagnostics_for_config_entry(
        hass, hass_client, init_integration, snapshot
    )
