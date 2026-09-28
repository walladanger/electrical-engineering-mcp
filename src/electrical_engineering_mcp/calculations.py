"""Pure, unit-explicit, steady-state electrical calculations.

These functions intentionally contain no conductor selection or code rules.
"""

import math
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict
from typing_extensions import TypedDict

from . import __version__

Phase = Literal["single_phase", "three_phase"]


class Method(BaseModel):
    id: str
    equation: str
    standard: None = None
    edition: None = None


class Engine(BaseModel):
    name: str = "electrical-engineering-mcp math kernel"
    version: str = __version__


class PowerResults(TypedDict):
    current_a: float
    apparent_power_kva: float
    reactive_power_magnitude_kvar: float


class VoltageDropResults(TypedDict):
    voltage_drop_v: float
    voltage_drop_percent: float
    estimated_load_voltage_v: float


class MotorResults(TypedDict):
    synchronous_speed_rpm: float
    slip_percent: float
    shaft_torque_nm: float
    estimated_input_current_a: float


class TransformerResults(TypedDict):
    primary_line_current_a: float
    secondary_line_current_a: float
    terminal_voltage_ratio: float


class CorrectionResults(TypedDict):
    capacitive_reactive_power_kvar: float


ResultT = TypeVar("ResultT")


class CalculationResult(BaseModel, Generic[ResultT]):
    model_config = ConfigDict(extra="forbid")

    method: Method
    engine: Engine
    inputs: dict[str, str | float | int]
    assumptions: list[str]
    results: ResultT
    warnings: list[str]
    provenance: list[str]


_CODE_WARNING = "This calculation is not a code-compliance determination or equipment recommendation."


def _number(name: str, value: float, *, lower: float = 0, upper: float | None = None, strict: bool = True) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    outside_range = value <= lower if strict else value < lower
    if outside_range:
        raise ValueError(f"{name} must be {'greater than' if strict else 'at least'} {lower}")
    if upper is not None and value > upper:
        raise ValueError(f"{name} must be at most {upper}")


def _phase(phase: str) -> float:
    if phase == "single_phase":
        return 1.0
    if phase == "three_phase":
        return math.sqrt(3)
    raise ValueError("phase must be single_phase or three_phase")


def _result(result_schema: type[ResultT], method: str, equation: str, inputs: dict,
            assumptions: list[str], results: ResultT, warnings: list[str] | None = None) -> CalculationResult[ResultT]:
    if any(not math.isfinite(value) for value in results.values()):
        raise ValueError("calculation overflow; input magnitude is outside the supported range")
    return CalculationResult[result_schema](
        method=Method(id=method, equation=equation), engine=Engine(), inputs=inputs,
        assumptions=assumptions, results=results,
        warnings=[_CODE_WARNING, *(warnings or [])],
        provenance=["Electrical Engineering MCP v0 deterministic algebraic method; see SPEC.md and source calculations.py"],
    )


def power_current(*, phase: Phase, voltage_v: float, real_power_kw: float, power_factor: float) -> CalculationResult[PowerResults]:
    """Balanced AC load; voltage is line-to-line for three phase."""
    factor = _phase(phase)
    _number("voltage_v", voltage_v)
    _number("real_power_kw", real_power_kw)
    _number("power_factor", power_factor, upper=1)
    apparent_kva = real_power_kw / power_factor
    current_a = real_power_kw * 1000 / (factor * voltage_v * power_factor)
    return _result(
        PowerResults,
        "balanced_power_current", "P = k × V × I × PF; k = 1 (1φ), √3 (3φ)",
        {"phase": phase, "voltage_v": voltage_v, "real_power_kw": real_power_kw, "power_factor": power_factor},
        ["Balanced, sinusoidal, steady-state AC load with lagging power factor.", "Three-phase voltage is line-to-line RMS; single-phase voltage is load RMS."],
        {"current_a": current_a, "apparent_power_kva": apparent_kva, "reactive_power_magnitude_kvar": real_power_kw * math.tan(math.acos(power_factor))},
    )


def voltage_drop(*, phase: Phase, voltage_v: float, current_a: float, length_m: float,
                 resistance_ohm_per_km: float, reactance_ohm_per_km: float, power_factor: float) -> CalculationResult[VoltageDropResults]:
    """Approximate AC drop using operating-temperature R and line X per conductor."""
    factor = math.sqrt(3) if _phase(phase) > 1 else 2.0
    _number("voltage_v", voltage_v)
    _number("current_a", current_a)
    _number("length_m", length_m)
    _number("resistance_ohm_per_km", resistance_ohm_per_km)
    _number("reactance_ohm_per_km", reactance_ohm_per_km, strict=False)
    _number("power_factor", power_factor, upper=1)
    drop = factor * current_a * (length_m / 1000) * (
        resistance_ohm_per_km * power_factor + reactance_ohm_per_km * math.sqrt(1 - power_factor**2)
    )
    warnings = ["Calculated drop meets or exceeds nominal supply voltage; linear approximation is not useful here."] if drop >= voltage_v else []
    return _result(
        VoltageDropResults,
        "approximate_ac_voltage_drop", "ΔV ≈ k × I × Lkm × (R × PF + X × √(1 − PF²)); k = 2 (1φ), √3 (3φ)",
        {"phase": phase, "voltage_v": voltage_v, "current_a": current_a, "length_m": length_m,
                      "resistance_ohm_per_km": resistance_ohm_per_km, "reactance_ohm_per_km": reactance_ohm_per_km, "power_factor": power_factor},
        ["One-way route length, lagging power factor, balanced steady-state load.",
         "R is the supplied resistance at operating temperature; X is supplied reactance per conductor.",
         "Single-phase assumes equal supply and return path impedances; excludes upstream source impedance."],
        {"voltage_drop_v": drop, "voltage_drop_percent": 100 * drop / voltage_v, "estimated_load_voltage_v": voltage_v - drop}, warnings,
    )


def motor_parameters(*, frequency_hz: float, poles: int, rated_speed_rpm: float, shaft_power_kw: float,
                     efficiency: float, power_factor: float, line_voltage_v: float) -> CalculationResult[MotorResults]:
    """Induction motor steady-state estimates from specified rated nameplate values."""
    for name, value in (("frequency_hz", frequency_hz), ("rated_speed_rpm", rated_speed_rpm),
                        ("shaft_power_kw", shaft_power_kw), ("line_voltage_v", line_voltage_v)):
        _number(name, value)
    for name, value in (("efficiency", efficiency), ("power_factor", power_factor)):
        _number(name, value, upper=1)
    if isinstance(poles, bool) or not isinstance(poles, int) or poles < 2 or poles % 2:
        raise ValueError("poles must be an even integer of at least 2")
    synchronous = 120 * frequency_hz / poles
    if rated_speed_rpm >= synchronous:
        raise ValueError("rated_speed_rpm must be below synchronous speed for motoring slip")
    return _result(
        MotorResults,
        "induction_motor_nameplate", "ns = 120f/p; slip = (ns − nr)/ns; T = Pshaft/ωr; I = Pshaft/(η × √3 × VLL × PF)",
        {"frequency_hz": frequency_hz, "poles": poles, "rated_speed_rpm": rated_speed_rpm,
                      "shaft_power_kw": shaft_power_kw, "efficiency": efficiency, "power_factor": power_factor, "line_voltage_v": line_voltage_v},
        ["Three-phase induction motor at the supplied rated operating point.",
         "Estimated current uses shaft output power and efficiency; starting current and service factor are excluded."],
        {"synchronous_speed_rpm": synchronous, "slip_percent": 100 * (synchronous - rated_speed_rpm) / synchronous,
         "shaft_torque_nm": shaft_power_kw * 1000 / (2 * math.pi * rated_speed_rpm / 60),
         "estimated_input_current_a": shaft_power_kw * 1000 / (efficiency * math.sqrt(3) * line_voltage_v * power_factor)},
    )


def transformer_parameters(*, phase: Phase, primary_voltage_v: float, secondary_voltage_v: float,
                           apparent_power_kva: float) -> CalculationResult[TransformerResults]:
    factor = _phase(phase)
    for name, value in (("primary_voltage_v", primary_voltage_v), ("secondary_voltage_v", secondary_voltage_v),
                        ("apparent_power_kva", apparent_power_kva)):
        _number(name, value)
    return _result(
        TransformerResults,
        "ideal_transformer_nameplate", "Iline = S/(k × Vterminal); k = 1 (1φ), √3 (3φ); terminal voltage ratio = V1/V2",
        {"phase": phase, "primary_voltage_v": primary_voltage_v, "secondary_voltage_v": secondary_voltage_v,
                      "apparent_power_kva": apparent_power_kva},
        ["Ideal nameplate relation; three-phase voltages and currents are terminal line quantities, not winding quantities.",
         "Winding connection and turns ratio, losses, impedance, regulation and fault current are excluded."],
        {"primary_line_current_a": apparent_power_kva * 1000 / (factor * primary_voltage_v),
         "secondary_line_current_a": apparent_power_kva * 1000 / (factor * secondary_voltage_v),
         "terminal_voltage_ratio": primary_voltage_v / secondary_voltage_v},
    )


def power_factor_correction(*, real_power_kw: float, initial_power_factor: float,
                            target_power_factor: float) -> CalculationResult[CorrectionResults]:
    for name, value in (("real_power_kw", real_power_kw), ("initial_power_factor", initial_power_factor),
                        ("target_power_factor", target_power_factor)):
        _number(name, value)
    if initial_power_factor >= target_power_factor or target_power_factor > 1:
        raise ValueError("power factors must satisfy 0 < initial_power_factor < target_power_factor <= 1")
    kvar = real_power_kw * (math.tan(math.acos(initial_power_factor)) - math.tan(math.acos(target_power_factor)))
    return _result(
        CorrectionResults,
        "ideal_power_factor_correction", "Qc = P × (tan(arccos(PF_initial)) − tan(arccos(PF_target)))",
        {"real_power_kw": real_power_kw, "initial_power_factor": initial_power_factor,
                      "target_power_factor": target_power_factor},
        ["Sinusoidal steady-state load with lagging initial and target power factors.",
         "Capacitor voltage, topology, harmonics, switching, resonance and step size are excluded."],
        {"capacitive_reactive_power_kvar": kvar},
    )
