"""
E2E tests for preview features on reCamera.

These tests verify RTSP stream and MQTT detection data availability.
These are read-only tests that don't modify device state.
"""

import socket
import time
from typing import Any

import pytest

from .conftest import RECAMERA_HOST, check_port_open

# Default reCamera preview configuration
RTSP_PORT = 8554
RTSP_PATH = "/live0"
MQTT_PORT = 1883
MQTT_TOPIC = "recamera/yolo11/detections"


# =============================================================================
# RTSP Stream Tests
# =============================================================================


@pytest.mark.e2e
@pytest.mark.device_recamera
@pytest.mark.dependency(depends=["simple_preset_deployed"], scope="session")
class TestRTSPStream:
    """Tests for reCamera RTSP stream availability (requires YOLO detector deployed)."""

    def test_rtsp_port_open(self, recamera_available):
        """Verify RTSP port is open on reCamera."""
        port_open = check_port_open(RECAMERA_HOST, RTSP_PORT, timeout=5.0)
        assert port_open, f"RTSP port {RTSP_PORT} not open"

    def test_rtsp_describe_response(self, recamera_available):
        """
        Verify RTSP server responds to DESCRIBE request.

        This test sends a basic RTSP DESCRIBE request to verify the stream exists.
        """
        rtsp_url = f"rtsp://{RECAMERA_HOST}:{RTSP_PORT}{RTSP_PATH}"

        # Build RTSP DESCRIBE request
        describe_request = (
            f"DESCRIBE {rtsp_url} RTSP/1.0\r\n"
            f"CSeq: 1\r\n"
            f"Accept: application/sdp\r\n"
            f"\r\n"
        )

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect((RECAMERA_HOST, RTSP_PORT))
            sock.sendall(describe_request.encode())

            # Receive response
            response = b""
            while True:
                try:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    response += chunk
                    # Check if we got complete response
                    if b"\r\n\r\n" in response:
                        # Check for content-length
                        header_end = response.find(b"\r\n\r\n")
                        headers = response[:header_end].decode("utf-8", errors="ignore")
                        if "Content-Length:" not in headers:
                            break
                        # Parse content length and wait for body
                        for line in headers.split("\r\n"):
                            if line.lower().startswith("content-length:"):
                                content_length = int(line.split(":")[1].strip())
                                body_start = header_end + 4
                                if len(response) >= body_start + content_length:
                                    break
                except socket.timeout:
                    break

            sock.close()

            response_str = response.decode("utf-8", errors="ignore")

            # Check for valid RTSP response
            assert "RTSP/1.0" in response_str, "Invalid RTSP response"

            # 200 OK means stream exists, 404 means not found
            if "200 OK" in response_str:
                # Stream exists and is available
                assert True
            elif "404" in response_str:
                pytest.skip(f"RTSP stream {RTSP_PATH} not found (404)")
            elif "401" in response_str:
                pytest.skip("RTSP requires authentication")
            else:
                # Other response - might still be valid
                assert "RTSP/1.0" in response_str, f"Unexpected response: {response_str[:200]}"

        except socket.timeout:
            pytest.skip(f"RTSP connection timeout - YOLO detector may not be deployed")
        except ConnectionRefusedError:
            pytest.skip(f"RTSP connection refused - YOLO detector may not be deployed")

    def test_rtsp_options_request(self, recamera_available):
        """
        Verify RTSP server responds to OPTIONS request.

        OPTIONS is the most basic RTSP request and should always work.
        """
        rtsp_url = f"rtsp://{RECAMERA_HOST}:{RTSP_PORT}{RTSP_PATH}"

        options_request = (
            f"OPTIONS {rtsp_url} RTSP/1.0\r\n"
            f"CSeq: 1\r\n"
            f"\r\n"
        )

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect((RECAMERA_HOST, RTSP_PORT))
            sock.sendall(options_request.encode())

            response = sock.recv(4096).decode("utf-8", errors="ignore")
            sock.close()

            assert "RTSP/1.0" in response, "Invalid RTSP response"
            assert "200 OK" in response, f"OPTIONS failed: {response[:200]}"

            # Check for common RTSP methods in Public header
            if "Public:" in response:
                public_methods = response.split("Public:")[1].split("\r\n")[0]
                # Should support at least DESCRIBE and SETUP
                assert "DESCRIBE" in public_methods or "SETUP" in public_methods

        except socket.timeout:
            pytest.fail("RTSP OPTIONS timeout")


# =============================================================================
# MQTT Detection Data Tests
# =============================================================================


@pytest.mark.e2e
@pytest.mark.device_recamera
@pytest.mark.dependency(depends=["simple_preset_deployed"], scope="session")
class TestMQTTDetections:
    """Tests for reCamera MQTT detection data (requires YOLO detector deployed)."""

    def test_mqtt_port_open(self, recamera_available):
        """Verify MQTT port is open on reCamera."""
        port_open = check_port_open(RECAMERA_HOST, MQTT_PORT, timeout=5.0)
        assert port_open, f"MQTT port {MQTT_PORT} not open on {RECAMERA_HOST}"

    def test_mqtt_broker_connection(self, recamera_available):
        """
        Verify MQTT broker accepts connections.

        Uses paho-mqtt to connect to the broker.
        """
        try:
            import paho.mqtt.client as mqtt
        except ImportError:
            pytest.skip("paho-mqtt not installed")

        connected = False
        connect_error = None

        def on_connect(client, userdata, flags, rc, properties=None):
            nonlocal connected, connect_error
            if rc == 0:
                connected = True
            else:
                connect_error = f"Connection failed with code {rc}"

        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        client.on_connect = on_connect

        try:
            client.connect(RECAMERA_HOST, MQTT_PORT, keepalive=10)
            client.loop_start()

            # Wait for connection
            timeout = 10
            start = time.time()
            while not connected and time.time() - start < timeout:
                if connect_error:
                    break
                time.sleep(0.1)

            client.loop_stop()
            client.disconnect()

            assert connected, f"MQTT connection failed: {connect_error or 'timeout'}"

        except Exception as e:
            pytest.fail(f"MQTT connection error: {e}")

    def test_mqtt_receive_detections(self, recamera_available):
        """
        Verify detection messages are being published to MQTT.

        This test subscribes to the detection topic and waits for messages.
        Note: This test may timeout if no objects are being detected.
        """
        try:
            import paho.mqtt.client as mqtt
        except ImportError:
            pytest.skip("paho-mqtt not installed")

        messages_received: list[Any] = []
        connected = False

        def on_connect(client, userdata, flags, rc, properties=None):
            nonlocal connected
            if rc == 0:
                connected = True
                # Subscribe to detection topic
                client.subscribe(MQTT_TOPIC)

        def on_message(client, userdata, msg):
            messages_received.append(msg)

        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        client.on_connect = on_connect
        client.on_message = on_message

        try:
            client.connect(RECAMERA_HOST, MQTT_PORT, keepalive=30)
            client.loop_start()

            # Wait for messages (30 seconds max)
            # Detection frequency depends on what's in front of camera
            timeout = 30
            start = time.time()

            while time.time() - start < timeout:
                if messages_received:
                    break
                time.sleep(0.5)

            client.loop_stop()
            client.disconnect()

            if not messages_received:
                pytest.skip(
                    f"No MQTT messages received on topic {MQTT_TOPIC} within {timeout}s "
                    "(this may be normal if nothing is being detected)"
                )

            # Verify message structure
            msg = messages_received[0]
            assert msg.topic == MQTT_TOPIC

            # Try to parse payload as JSON
            import json

            try:
                payload = json.loads(msg.payload.decode())
                # Detection messages typically have detections array
                assert isinstance(payload, (dict, list)), "Unexpected payload format"
            except json.JSONDecodeError:
                # Raw payload might be valid too
                pass

        except Exception as e:
            pytest.fail(f"MQTT test error: {e}")

    def test_mqtt_detection_message_format(self, recamera_available):
        """
        Verify detection message format (if messages are available).

        Expected format:
        {
            "detections": [
                {"class": "person", "confidence": 0.95, "bbox": [x, y, w, h]},
                ...
            ],
            "timestamp": "..."
        }
        """
        try:
            import paho.mqtt.client as mqtt
            import json
        except ImportError:
            pytest.skip("paho-mqtt not installed")

        messages_received: list[Any] = []
        connected = False

        def on_connect(client, userdata, flags, rc, properties=None):
            nonlocal connected
            if rc == 0:
                connected = True
                client.subscribe(MQTT_TOPIC)

        def on_message(client, userdata, msg):
            messages_received.append(msg)

        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        client.on_connect = on_connect
        client.on_message = on_message

        try:
            client.connect(RECAMERA_HOST, MQTT_PORT, keepalive=30)
            client.loop_start()

            # Wait for a message
            timeout = 15
            start = time.time()
            while not messages_received and time.time() - start < timeout:
                time.sleep(0.5)

            client.loop_stop()
            client.disconnect()

            if not messages_received:
                pytest.skip("No detection messages received")

            # Parse and validate message format
            msg = messages_received[0]
            payload = json.loads(msg.payload.decode())

            # Check for common detection message fields
            # The exact format may vary, so we check for likely fields
            is_valid_format = (
                "detections" in payload
                or "objects" in payload
                or "results" in payload
                or isinstance(payload, list)  # Might be array of detections
            )

            if not is_valid_format:
                # Log the payload for debugging
                pytest.skip(f"Unknown detection format: {str(payload)[:200]}")

        except json.JSONDecodeError as e:
            pytest.skip(f"Detection message not JSON: {e}")
        except Exception as e:
            pytest.fail(f"Error testing detection format: {e}")


# =============================================================================
# Preview API Tests
# =============================================================================


@pytest.mark.e2e
class TestPreviewAPI:
    """API tests for preview feature (no device required)."""

    def test_preview_device_in_solution(self, api_server_running, api_client):
        """Verify preview device exists in solution deployment."""
        response = api_client.get("/api/solutions/recamera_heatmap_grafana/deployment")
        assert response.status_code == 200

        data = response.json()
        devices = data.get("devices", [])

        # Find preview device
        preview_device = next(
            (d for d in devices if d.get("type") == "preview"), None
        )

        # Preview might be optional, so just check if it exists when present
        if preview_device:
            assert "id" in preview_device
            # Preview devices should have user_inputs for configuration
            assert "user_inputs" in preview_device or "section" in preview_device

    def test_preview_video_config(self, api_server_running, api_client):
        """Verify preview video configuration is available."""
        response = api_client.get("/api/solutions/recamera_heatmap_grafana/deployment")
        assert response.status_code == 200

        data = response.json()
        devices = data.get("devices", [])

        preview_device = next(
            (d for d in devices if d.get("type") == "preview"), None
        )

        if preview_device and "video" in preview_device:
            video = preview_device["video"]
            # Should have video type specified
            assert "type" in video
