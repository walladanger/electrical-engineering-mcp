import math

import pytest

from electrical_engineering_mcp.calculations import (
    motor_parameters,
    power_current,
    power_factor_correction,
    transformer_parameters,
    voltage_drop,
)


def test_three_phase_power_current_golden_vector():
    result = power_current(phase="three_phase", voltage_v=480, real_power_kw=20, power_factor=0.8)
    assert result.results["current_a"] == pytest.approx(30.070326, rel=1e-6)
    assert result.results["apparent_power_kva"] == pytest.approx(25)
    assert result.results["reactive_power_magnitude_kvar"] == pytest.approx(15)
    assert result.method.id == "balanced_power_current"


def test_single_phase_power_current():
    result = power_current(phase="single_phase", voltage_v=240, real_power_kw=4.8, power_factor=1)
    assert result.results["current_a"] == pytest.approx(20)
    assert result.results["reactive_power_magnitude_kvar"] == pytest.approx(0)


def test_voltage_drop_balanced_three_phase_and_percent():
    result = voltage_drop(
        phase="three_phase", voltage_v=400, current_a=50, length_m=100,
        resistance_ohm_per_km=0.5, reactance_ohm_per_km=0.08, power_factor=0.8,
    )
    assert result.results["voltage_drop_v"] == pytest.approx(math.sqrt(3) * 50 * 0.1 * (0.5 * 0.8 + 0.08 * 0.6))
    assert result.results["voltage_drop_percent"] == pytest.approx(result.results["voltage_drop_v"] / 4)
    assert "not a code-compliance" in " ".join(result.warnings)


def test_single_phase_voltage_drop_and_excess_warning():
    result = voltage_drop(phase="single_phase", voltage_v=120, current_a=20, length_m=100,
                          resistance_ohm_per_km=1, reactance_ohm_per_km=0, power_factor=1)
    assert result.results["voltage_drop_v"] == pytest.approx(4)
    assert result.results["estimated_load_voltage_v"] == pytest.approx(116)
    excess = voltage_drop(phase="single_phase", voltage_v=1, current_a=20, length_m=100,
                          resistance_ohm_per_km=1, reactance_ohm_per_km=0, power_factor=1)
    assert "meets or exceeds" in " ".join(excess.warnings)


def test_motor_nameplate_relations():
    result = motor_parameters(
        frequency_hz=60, poles=4, rated_speed_rpm=1740, shaft_power_kw=15,
        efficiency=0.9, power_factor=0.85, line_voltage_v=480,
    )
    assert result.results["synchronous_speed_rpm"] == pytest.approx(1800)
    assert result.results["slip_percent"] == pytest.approx(100 / 30)
    assert result.results["shaft_torque_nm"] == pytest.approx(15000 / (2 * math.pi * 1740 / 60))
    assert result.results["estimated_input_current_a"] == pytest.approx(15000 / (.9 * math.sqrt(3) * 480 * .85))


def test_transformer_ideal_three_phase():
    result = transformer_parameters(phase="three_phase", primary_voltage_v=480, secondary_voltage_v=208, apparent_power_kva=75)
    assert result.results["primary_line_current_a"] == pytest.approx(75000 / (math.sqrt(3) * 480))
    assert result.results["secondary_line_current_a"] == pytest.approx(75000 / (math.sqrt(3) * 208))
    assert result.results["terminal_voltage_ratio"] == pytest.approx(480 / 208)


def test_transformer_single_phase_line_current():
    result = transformer_parameters(phase="single_phase", primary_voltage_v=240, secondary_voltage_v=120, apparent_power_kva=12)
    assert result.results["primary_line_current_a"] == pytest.approx(50)
    assert result.results["secondary_line_current_a"] == pytest.approx(100)


def test_power_factor_correction_golden_vector():
    result = power_factor_correction(real_power_kw=100, initial_power_factor=0.8, target_power_factor=0.95)
    assert result.results["capacitive_reactive_power_kvar"] == pytest.approx(100 * (0.75 - math.tan(math.acos(0.95))))


@pytest.mark.parametrize("call", [
    lambda: power_current(phase="three_phase", voltage_v=0, real_power_kw=20, power_factor=0.8),
    lambda: power_current(phase="single_phase", voltage_v=120, real_power_kw=float("nan"), power_factor=0.8),
    lambda: voltage_drop(phase="single_phase", voltage_v=120, current_a=20, length_m=10, resistance_ohm_per_km=1, reactance_ohm_per_km=0, power_factor=1.01),
    lambda: motor_parameters(frequency_hz=60, poles=3, rated_speed_rpm=1700, shaft_power_kw=10, efficiency=.9, power_factor=.9, line_voltage_v=480),
    lambda: motor_parameters(frequency_hz=60, poles=4, rated_speed_rpm=1801, shaft_power_kw=10, efficiency=.9, power_factor=.9, line_voltage_v=480),
    lambda: transformer_parameters(phase="three_phase", primary_voltage_v=480, secondary_voltage_v=208, apparent_power_kva=float("inf")),
    lambda: power_factor_correction(real_power_kw=10, initial_power_factor=.95, target_power_factor=.9),
    lambda: power_current(phase="single_phase", voltage_v=1e-300, real_power_kw=1e308, power_factor=1),
])
def test_invalid_inputs_are_rejected(call):
    with pytest.raises(ValueError):
        call()
