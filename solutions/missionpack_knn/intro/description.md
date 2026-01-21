## Overview

This HVAC Automation Control System uses KNN (K-Nearest Neighbors) regression algorithms to predict optimal equipment parameters based on historical operational data. It communicates with HVAC equipment through the OPC-UA protocol, enabling intelligent automated operations.

## Key Features

- **Intelligent Prediction** - Uses KNN regression algorithm to predict optimal output parameters based on historical data
- **OPC-UA Integration** - Connects to industrial equipment via standard OPC-UA protocol
- **Direct & Isolated Dispatch** - Apply predictions to live equipment or test in simulation mode
- **Continuous Monitoring** - Real-time parameter reading with configurable intervals
- **Web-based Interface** - Modern Vue.js frontend for easy configuration and monitoring

## Use Cases

| Scenario | Description |
|----------|-------------|
| HVAC Optimization | Automatically adjust heating/cooling parameters based on historical patterns |
| Energy Efficiency | Reduce energy consumption by predicting optimal setpoints |
| Predictive Maintenance | Monitor parameter trends to anticipate maintenance needs |
| Testing & Validation | Use isolated dispatch mode to validate predictions before live deployment |

## System Architecture

The system consists of three main components:

1. **Web Interface** - Vue.js frontend for configuration, monitoring, and control
2. **FastAPI Backend** - Handles predictions, OPC-UA communication, and data management
3. **OPC-UA Client** - Connects to industrial HVAC controllers

## Workflow

1. Connect to your OPC-UA server
2. Upload historical training data (CSV format)
3. Train the KNN prediction model
4. Configure input/output parameter mappings
5. Start automatic parameter reading and prediction
6. Apply predictions via direct or isolated dispatch

## Technical Specifications

- **Algorithm**: KNN Regression with configurable K value
- **Protocol**: OPC-UA (Unified Architecture)
- **API**: RESTful HTTP with WebSocket support
- **Container**: Docker with docker-compose support
- **Ports**: 8280 (Web UI), 4841 (OPC-UA Simulator)
