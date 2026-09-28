# Electrical Engineering MCP: initial contract

## Value proposition

Give electricians and technical users conversational access to reproducible electrical calculations. The assistant translates a request into explicit inputs; the server validates those inputs and performs arithmetic. Current workflows require selecting separate calculators and tracking assumptions by hand.

## Why an assistant

Natural language helps identify the appropriate calculation and missing inputs. The assistant does not supply a numeric answer from its own arithmetic. The MCP tool returns the method, units, assumptions, limits, and engine identity alongside each result.

## Initial experience

Tool-only local MCP over stdio. The user asks for a calculation, the assistant supplies inputs to a typed tool, and then presents its structured result and limitations. No graphical view or authentication is involved. All calls are read-only.

## v0 flows and tools

1. Calculate single-phase or balanced three-phase power/current: `calculate_power_current`.
2. Estimate voltage drop from *provided operating-temperature* line resistance and reactance: `calculate_voltage_drop`.
3. Calculate induction-motor speed, slip, shaft torque and estimated three-phase input current: `calculate_motor_parameters`.
4. Calculate ideal transformer terminal voltage ratio and rated line currents: `calculate_transformer_parameters`.
5. Calculate ideal reactive-power correction in kVAr: `calculate_power_factor_correction`.
6. Explain a supported method and its limits: `describe_method`.

Every calculation returns a structured envelope with `method`, `engine`, `inputs`, `assumptions`, `results`, `warnings`, and `provenance`. Invalid, nonfinite or physically inconsistent inputs fail validation. Values must have units in names. No numeric defaults for missing engineering inputs.

## Boundaries

- Results are mathematical estimates, not NEC/IEC/CEC compliance findings, equipment selection, or work instructions.
- No conductor ampacity/size or protective-device recommendation in v0. No standards tables are bundled.
- Voltage drop uses a steady-state approximate formula for a balanced load and a lagging power factor. It excludes starting transients, harmonic loads, return-path variations, temperature estimation, and upstream impedance.
- Motor estimates assume rated steady-state operation. Transformer results assume ideal nameplate ratio and ignore losses, regulation and impedance.
- Later adapters may add pandapower network studies and OpenDSS distribution studies; their inputs and standard editions must be explicit, and their outputs must retain engine provenance.
- Reports and UI are later work.

## Acceptance

- Local install and stdio launch work on Python 3.11+ including Windows.
- Golden vectors and invalid-input tests exercise the pure calculation library.
- An in-process MCP client lists and invokes each tool and receives structured output.
- CI runs the same test suite.
