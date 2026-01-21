## Local Deployment

Deploy the HVAC Automation Control System on this machine using Docker.

### What Will Be Deployed

- **HVAC Control Application** - Web interface and API server (port 8280)
- **Built-in OPC-UA Simulator** - For testing without live equipment (port 4841)

### Configuration

**OPC-UA Server Address**: Enter your OPC-UA server address, or leave default to use the built-in simulator.

### After Deployment

The application will be available at **http://localhost:8280**

Your data will be persisted in Docker volumes:
- `configs/` - Configuration files
- `uploads/` - Uploaded training data
- `models/` - Trained prediction models
- `log/` - Application logs
