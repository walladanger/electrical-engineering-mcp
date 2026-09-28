import sys
from pathlib import Path

import pytest
from mcp import Client, StdioServerParameters

from electrical_engineering_mcp.server import mcp


@pytest.mark.asyncio
async def test_tool_catalog_and_structured_result():
    async with Client(mcp, raise_exceptions=True) as client:
        catalog = await client.list_tools()
        names = {tool.name for tool in catalog.tools}
        assert names == {
            "calculate_power_current", "calculate_voltage_drop", "calculate_motor_parameters",
            "calculate_transformer_parameters", "calculate_power_factor_correction", "describe_method",
        }
        for tool in catalog.tools:
            assert tool.input_schema["type"] == "object"
            assert tool.output_schema is not None
            assert tool.annotations.read_only_hint is True
        for tool in (t for t in catalog.tools if t.name != "describe_method"):
            assert "results" in tool.output_schema["properties"]
        power_tool = next(tool for tool in catalog.tools if tool.name == "calculate_power_current")
        assert "line-to-line" in power_tool.input_schema["properties"]["voltage_v"]["description"]
        assert "fraction" in power_tool.input_schema["properties"]["power_factor"]["description"]
        assert power_tool.output_schema["$defs"]["PowerResults"]["required"] == [
            "current_a", "apparent_power_kva", "reactive_power_magnitude_kvar",
        ]
        result = await client.call_tool("calculate_power_current", {
            "phase": "three_phase", "voltage_v": 480, "real_power_kw": 20, "power_factor": .8,
        })
        assert not result.is_error
        assert result.structured_content["results"]["current_a"] == pytest.approx(30.070326, rel=1e-6)
        assert result.structured_content["method"]["standard"] is None
        description = await client.call_tool("describe_method", {"method_id": "balanced_power_current"})
        assert description.structured_content["compliance_status"] == "not assessed"


@pytest.mark.asyncio
@pytest.mark.parametrize(("name", "inputs", "result_key"), [
    ("calculate_voltage_drop", {"phase": "three_phase", "voltage_v": 400, "current_a": 50,
                                "length_m": 100, "resistance_ohm_per_km": .5,
                                "reactance_ohm_per_km": .08, "power_factor": .8}, "voltage_drop_v"),
    ("calculate_motor_parameters", {"frequency_hz": 60, "poles": 4, "rated_speed_rpm": 1740,
                                    "shaft_power_kw": 15, "efficiency": .9, "power_factor": .85,
                                    "line_voltage_v": 480}, "shaft_torque_nm"),
    ("calculate_transformer_parameters", {"phase": "three_phase", "primary_voltage_v": 480,
                                          "secondary_voltage_v": 208, "apparent_power_kva": 75}, "secondary_line_current_a"),
    ("calculate_power_factor_correction", {"real_power_kw": 100, "initial_power_factor": .8,
                                           "target_power_factor": .95}, "capacitive_reactive_power_kvar"),
])
async def test_each_calculation_via_mcp(name, inputs, result_key):
    async with Client(mcp, raise_exceptions=True) as client:
        result = await client.call_tool(name, inputs)
        assert not result.is_error
        assert result.structured_content["results"][result_key] > 0
        assert result.structured_content["engine"]["version"] == "0.1.0"


@pytest.mark.asyncio
async def test_bad_input_is_tool_error_and_no_numeric_result():
    async with Client(mcp, raise_exceptions=True) as client:
        result = await client.call_tool("calculate_voltage_drop", {
            "phase": "three_phase", "voltage_v": 400, "current_a": 50, "length_m": 100,
            "resistance_ohm_per_km": .5, "reactance_ohm_per_km": .08, "power_factor": 2,
        })
        assert result.is_error
        assert result.structured_content is None


@pytest.mark.asyncio
async def test_stdio_entry_point_in_a_subprocess():
    executable = Path(sys.executable).parent / ("electrical-engineering-mcp.exe" if sys.platform == "win32" else "electrical-engineering-mcp")
    assert executable.is_file(), "install the package with pip install -e '.[test]' before testing"
    params = StdioServerParameters(command=str(executable))
    async with Client(params, read_timeout_seconds=10) as client:
        result = await client.call_tool("describe_method", {"method_id": "ideal_transformer_nameplate"})
        assert not result.is_error
        assert result.structured_content["compliance_status"] == "not assessed"
