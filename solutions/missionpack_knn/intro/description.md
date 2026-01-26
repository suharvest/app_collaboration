## What This Solution Does

HVAC systems (chillers, air handling units, etc.) typically rely on experienced technicians to tune parameters. Inexperienced operators often waste energy, and even experts cannot monitor systems 24/7. This solution learns optimal parameter combinations from historical data, automatically adjusting settings like an experienced technician would.

## Key Benefits

| Benefit | Details |
|---------|---------|
| Save Energy & Money | Analyzes historical data to find optimal parameters, typically reducing energy consumption by 10-20% |
| Reduce Manual Work | System automatically suggests or executes parameter adjustments, no manual monitoring needed |
| Easy for Beginners | Operators without HVAC expertise can use it - the system tells you what to set |
| Safe Validation | Supports "observe only" mode to review suggestions before enabling automatic control |

## Use Cases

| Scenario | How It Helps |
|----------|--------------|
| Malls/Office Buildings | Auto-adjust chilled water temperature and fan speed based on outdoor temperature and indoor load |
| Factory Workshops | Predict HVAC needs based on production schedules, adjust ahead to avoid temperature fluctuations |
| Data Centers | Precisely control room temperature and humidity for equipment safety |
| Hotels | Dynamically adjust common area HVAC based on occupancy rates |

## Requirements

**Hardware**:
- Computer or industrial PC with Docker (e.g., reComputer R series)
- HVAC equipment must support OPC-UA protocol for reading/writing parameters

**Data**:
- At least 1 week of historical operation data (CSV format)
- Data should include: timestamp, setpoint parameters, actual values, energy consumption

**Limitations**:
- Initial setup requires uploading data to "train" the system (takes about 5-10 minutes)
- Recommended to run in "observe only" mode for 1-2 days first, then enable automatic control after confirming suggestions are reasonable
