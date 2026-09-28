"""Local stdio MCP server exposing deterministic calculation tools."""

from typing import Annotated, Literal

from mcp.server import MCPServer
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

from . import __version__
from .calculations import (
    CalculationResult,
    CorrectionResults,
    MotorResults,
    PowerResults,
    TransformerResults,
    VoltageDropResults,
)
from .calculations import (
    motor_parameters as compute_motor,
)
from .calculations import (
    power_current as compute_power,
)
from .calculations import (
    power_factor_correction as compute_correction,
)
from .calculations import (
    transformer_parameters as compute_transformer,
)
from .calculations import (
    voltage_drop as compute_drop,
)

mcp = MCPServer(
    "Electrical Engineering MCP",
    version=__version__,
    instructions="Use explicit electrical inputs. Results are mathematical estimates, not code-compliance findings or equipment selection.",
)
READ_ONLY = ToolAnnotations(read_only_hint=True, open_world_hint=False)


class MethodDescription(BaseModel):
    method_id: str
    equation: str
    limits: list[str]
    compliance_status: Literal["not assessed"] = "not assessed"


PhaseInput = Annotated[Literal["single_phase", "three_phase"], Field(description="Single-phase or balanced three-phase AC circuit.")]
LoadVoltage = Annotated[float, Field(description="Nominal RMS voltage in volts: line-to-line for three phase, load voltage for single phase.", gt=0, allow_inf_nan=False)]
LaggingPF = Annotated[float, Field(description="Lagging power factor as a fraction greater than 0 and at most 1, not a percentage.", gt=0, le=1, allow_inf_nan=False)]


@mcp.tool(annotations=READ_ONLY)
def calculate_power_current(phase: PhaseInput, voltage_v: LoadVoltage,
                            real_power_kw: Annotated[float, Field(description="Positive real load power in kilowatts.", gt=0, allow_inf_nan=False)],
                            power_factor: LaggingPF) -> CalculationResult[PowerResults]:
    """Calculate balanced steady-state AC current, apparent power and lagging reactive-power magnitude."""
    return compute_power(phase=phase, voltage_v=voltage_v, real_power_kw=real_power_kw, power_factor=power_factor)


@mcp.tool(annotations=READ_ONLY)
def calculate_voltage_drop(phase: PhaseInput, voltage_v: LoadVoltage,
                           current_a: Annotated[float, Field(description="Positive RMS load current in amperes.", gt=0, allow_inf_nan=False)],
                           length_m: Annotated[float, Field(description="One-way route length in metres.", gt=0, allow_inf_nan=False)],
                           resistance_ohm_per_km: Annotated[float, Field(description="Per-conductor AC resistance in ohms/km at operating temperature; supply measured or manufacturer data.", gt=0, allow_inf_nan=False)],
                           reactance_ohm_per_km: Annotated[float, Field(description="Per-conductor AC reactance in ohms/km for the actual wiring arrangement.", ge=0, allow_inf_nan=False)],
                           power_factor: LaggingPF) -> CalculationResult[VoltageDropResults]:
    """Estimate balanced AC voltage drop using one-way length and supplied operating-temperature R and X per conductor."""
    return compute_drop(phase=phase, voltage_v=voltage_v, current_a=current_a, length_m=length_m,
                        resistance_ohm_per_km=resistance_ohm_per_km,
                        reactance_ohm_per_km=reactance_ohm_per_km, power_factor=power_factor)


@mcp.tool(annotations=READ_ONLY)
def calculate_motor_parameters(frequency_hz: Annotated[float, Field(description="Positive supply frequency in hertz.", gt=0, allow_inf_nan=False)],
                               poles: Annotated[int, Field(description="Even number of motor poles, at least two.", ge=2)],
                               rated_speed_rpm: Annotated[float, Field(description="Rated shaft speed in revolutions/minute below synchronous speed.", gt=0, allow_inf_nan=False)],
                               shaft_power_kw: Annotated[float, Field(description="Rated mechanical shaft OUTPUT power in kilowatts.", gt=0, allow_inf_nan=False)],
                               efficiency: Annotated[float, Field(description="Rated efficiency as a fraction greater than 0 and at most 1.", gt=0, le=1, allow_inf_nan=False)],
                               power_factor: LaggingPF,
                               line_voltage_v: Annotated[float, Field(description="Three-phase line-to-line RMS supply voltage in volts.", gt=0, allow_inf_nan=False)]) -> CalculationResult[MotorResults]:
    """Estimate three-phase induction motor synchronous speed, slip, shaft torque and rated input current."""
    return compute_motor(frequency_hz=frequency_hz, poles=poles, rated_speed_rpm=rated_speed_rpm,
                         shaft_power_kw=shaft_power_kw, efficiency=efficiency, power_factor=power_factor,
                         line_voltage_v=line_voltage_v)


@mcp.tool(annotations=READ_ONLY)
def calculate_transformer_parameters(phase: PhaseInput,
                                     primary_voltage_v: Annotated[float, Field(description="Primary terminal RMS voltage in volts, line-to-line for three phase.", gt=0, allow_inf_nan=False)],
                                     secondary_voltage_v: Annotated[float, Field(description="Secondary terminal RMS voltage in volts, line-to-line for three phase.", gt=0, allow_inf_nan=False)],
                                     apparent_power_kva: Annotated[float, Field(description="Rated apparent power in kilovolt-amperes.", gt=0, allow_inf_nan=False)]) -> CalculationResult[TransformerResults]:
    """Calculate ideal transformer terminal voltage ratio and rated LINE currents, not winding currents or turns ratio."""
    return compute_transformer(phase=phase, primary_voltage_v=primary_voltage_v,
                               secondary_voltage_v=secondary_voltage_v, apparent_power_kva=apparent_power_kva)


@mcp.tool(annotations=READ_ONLY)
def calculate_power_factor_correction(real_power_kw: Annotated[float, Field(description="Positive real load power in kilowatts.", gt=0, allow_inf_nan=False)],
                                      initial_power_factor: Annotated[float, Field(description="Initial LAGGING power factor as a fraction (0, 1).", gt=0, lt=1, allow_inf_nan=False)],
                                      target_power_factor: LaggingPF) -> CalculationResult[CorrectionResults]:
    """Calculate ideal capacitive kVAr for an improved lagging power factor; does not size a capacitor bank."""
    return compute_correction(real_power_kw=real_power_kw, initial_power_factor=initial_power_factor,
                              target_power_factor=target_power_factor)


@mcp.tool(annotations=READ_ONLY)
def describe_method(method_id: Literal[
    "balanced_power_current", "approximate_ac_voltage_drop", "induction_motor_nameplate",
    "ideal_transformer_nameplate", "ideal_power_factor_correction",
]) -> MethodDescription:
    """Describe a supported calculation method and its input/engineering limits."""
    descriptions = {
        "balanced_power_current": ("Balanced AC P = k V I PF", ["Requires RMS voltage, real power, PF and phase", "Not a load or conductor sizing study"]),
        "approximate_ac_voltage_drop": ("ΔV ≈ k I L (R PF + X sinφ)", ["Requires one-way length and R/X at operating temperature", "Lagging balanced steady-state load only"]),
        "induction_motor_nameplate": ("ns = 120 f/p; slip and shaft torque at rated speed", ["Requires nameplate shaft output, efficiency and PF", "Excludes motor starting and service factor"]),
        "ideal_transformer_nameplate": ("S = k V I; ideal voltage ratio", ["Excludes impedance, winding configuration, losses and fault study"]),
        "ideal_power_factor_correction": ("Qc = P (tanφ1 − tanφ2)", ["Lagging steady-state load", "Excludes harmonic/resonance and capacitor bank design"]),
    }
    equation, limits = descriptions[method_id]
    return MethodDescription(method_id=method_id, equation=equation, limits=limits)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
