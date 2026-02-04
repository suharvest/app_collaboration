"""
MQTT Bridge Service - MQTT to WebSocket bridging

Connects to MQTT brokers and forwards messages to WebSocket clients.
"""

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# Try to import paho-mqtt
try:
    import paho.mqtt.client as mqtt

    # Check for paho-mqtt 2.0+ callback API
    try:
        from paho.mqtt.enums import CallbackAPIVersion

        MQTT_V2_API = True
    except ImportError:
        MQTT_V2_API = False
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False
    MQTT_V2_API = False
    logger.warning(
        "paho-mqtt not installed. MQTT bridge functionality will be limited."
    )


@dataclass
class MqttSubscription:
    """Information about an MQTT subscription"""

    subscription_id: str
    broker: str
    port: int
    topic: str
    username: Optional[str] = None
    password: Optional[str] = None
    client: Optional["mqtt.Client"] = None
    connected: bool = False
    error: Optional[str] = None
    callbacks: Set[Callable] = field(default_factory=set)
    message_count: int = 0


class MqttBridge:
    """
    Bridges MQTT messages to WebSocket clients.

    Manages MQTT connections and forwards messages to registered callbacks.
    """

    def __init__(self):
        """Initialize the MQTT bridge"""
        self.subscriptions: Dict[str, MqttSubscription] = {}
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    async def subscribe(
        self,
        broker: str,
        port: int,
        topic: str,
        callback: Callable,
        username: Optional[str] = None,
        password: Optional[str] = None,
        subscription_id: Optional[str] = None,
    ) -> str:
        """
        Subscribe to an MQTT topic and forward messages to callback.

        Args:
            broker: MQTT broker hostname or IP
            port: MQTT broker port
            topic: MQTT topic to subscribe to
            callback: Async callback function(message: dict) to receive messages
            username: Optional MQTT username
            password: Optional MQTT password
            subscription_id: Optional subscription ID (auto-generated if not provided)

        Returns:
            The subscription ID

        Raises:
            RuntimeError: If paho-mqtt is not installed
        """
        if not MQTT_AVAILABLE:
            raise RuntimeError(
                "paho-mqtt is not installed. " "Install it with: pip install paho-mqtt"
            )

        # Generate subscription ID
        if subscription_id is None:
            subscription_id = str(uuid.uuid4())[:8]

        # Create unique key for this connection
        conn_key = f"{broker}:{port}:{topic}"

        # Check if we already have this subscription
        existing = None
        for sub_id, sub in self.subscriptions.items():
            sub_key = f"{sub.broker}:{sub.port}:{sub.topic}"
            if sub_key == conn_key:
                existing = sub
                break

        if existing:
            # Add callback to existing subscription
            existing.callbacks.add(callback)
            logger.info(f"Added callback to existing subscription: {conn_key}")
            return existing.subscription_id

        # Create new subscription
        # Use get_running_loop() instead of get_event_loop() for Python 3.10+ compatibility
        # This ensures we get the actual running loop, not a new one
        self._loop = asyncio.get_running_loop()
        subscription = MqttSubscription(
            subscription_id=subscription_id,
            broker=broker,
            port=port,
            topic=topic,
            username=username,
            password=password,
        )
        subscription.callbacks.add(callback)

        # Create and configure MQTT client
        if MQTT_V2_API:
            client = mqtt.Client(
                callback_api_version=CallbackAPIVersion.VERSION2,
                client_id=f"preview_bridge_{subscription_id}",
                protocol=mqtt.MQTTv311,
            )
        else:
            client = mqtt.Client(
                client_id=f"preview_bridge_{subscription_id}",
                protocol=mqtt.MQTTv311,
            )

        if username and password:
            client.username_pw_set(username, password)

        # Set up callbacks (signature differs between API versions)
        if MQTT_V2_API:

            def on_connect(client, userdata, flags, rc, properties=None):
                if rc == 0 or rc.value == 0:
                    subscription.connected = True
                    subscription.error = None
                    client.subscribe(topic)
                    logger.info(
                        f"Connected to MQTT broker {broker}:{port}, subscribed to {topic}"
                    )
                else:
                    subscription.connected = False
                    subscription.error = f"Connection failed with code {rc}"
                    logger.error(f"MQTT connection failed: {subscription.error}")

            def on_disconnect(client, userdata, flags, rc, properties=None):
                subscription.connected = False
                if rc != 0:
                    subscription.error = f"Unexpected disconnect (code {rc})"
                    logger.warning(f"MQTT disconnected: {subscription.error}")

        else:

            def on_connect(client, userdata, flags, rc):
                if rc == 0:
                    subscription.connected = True
                    subscription.error = None
                    client.subscribe(topic)
                    logger.info(
                        f"Connected to MQTT broker {broker}:{port}, subscribed to {topic}"
                    )
                else:
                    subscription.connected = False
                    subscription.error = f"Connection failed with code {rc}"
                    logger.error(f"MQTT connection failed: {subscription.error}")

            def on_disconnect(client, userdata, rc):
                subscription.connected = False
                if rc != 0:
                    subscription.error = f"Unexpected disconnect (code {rc})"
                    logger.warning(f"MQTT disconnected: {subscription.error}")

        def on_message(client, userdata, msg):
            subscription.message_count += 1
            try:
                # Try to parse as JSON
                payload = msg.payload.decode("utf-8")
                try:
                    data = json.loads(payload)
                except json.JSONDecodeError:
                    data = {"raw": payload}

                import time

                message = {
                    "topic": msg.topic,
                    "payload": data,
                    "timestamp": time.time(),
                }

                # Forward to all callbacks
                for callback in subscription.callbacks:
                    if asyncio.iscoroutinefunction(callback):
                        asyncio.run_coroutine_threadsafe(callback(message), self._loop)
                    else:
                        callback(message)

            except Exception as e:
                logger.error(f"Error processing MQTT message: {e}")

        client.on_connect = on_connect
        client.on_disconnect = on_disconnect
        client.on_message = on_message

        subscription.client = client
        self.subscriptions[subscription_id] = subscription

        # Connect and wait for actual connection
        try:
            client.connect_async(broker, port, keepalive=60)
            client.loop_start()
            logger.info(
                f"Starting MQTT subscription {subscription_id} to {broker}:{port}/{topic}"
            )

            # Wait for connection to be established (max 10 seconds)
            for _ in range(100):  # 100 * 0.1s = 10s
                await asyncio.sleep(0.1)
                if subscription.connected:
                    logger.info(f"MQTT connected to {broker}:{port}/{topic}")
                    return subscription_id
                if subscription.error:
                    raise RuntimeError(subscription.error)

            # Timeout
            client.loop_stop()
            client.disconnect()
            raise RuntimeError(f"Connection timeout to {broker}:{port}")

        except Exception as e:
            subscription.error = str(e)
            subscription.connected = False
            logger.error(f"Failed to connect to MQTT: {e}")
            raise RuntimeError(f"Failed to connect to MQTT broker: {e}")

    async def unsubscribe(
        self, subscription_id: str, callback: Optional[Callable] = None
    ) -> bool:
        """
        Unsubscribe from an MQTT topic.

        Args:
            subscription_id: The subscription ID
            callback: Optional specific callback to remove.
                     If None, removes the entire subscription.

        Returns:
            True if unsubscribed, False if not found
        """
        if subscription_id not in self.subscriptions:
            return False

        subscription = self.subscriptions[subscription_id]

        if callback:
            # Remove specific callback
            subscription.callbacks.discard(callback)
            if subscription.callbacks:
                # Still have other callbacks, keep subscription
                return True

        # No more callbacks, disconnect
        if subscription.client:
            subscription.client.loop_stop()
            subscription.client.disconnect()

        del self.subscriptions[subscription_id]
        logger.info(f"Unsubscribed {subscription_id}")
        return True

    def get_subscription_info(self, subscription_id: str) -> Optional[dict]:
        """Get information about a subscription"""
        sub = self.subscriptions.get(subscription_id)
        if not sub:
            return None

        return {
            "subscription_id": sub.subscription_id,
            "broker": sub.broker,
            "port": sub.port,
            "topic": sub.topic,
            "connected": sub.connected,
            "error": sub.error,
            "message_count": sub.message_count,
        }

    def list_subscriptions(self) -> List[dict]:
        """List all active subscriptions"""
        return [self.get_subscription_info(sid) for sid in self.subscriptions.keys()]

    async def stop_all(self):
        """Stop all MQTT subscriptions"""
        for subscription_id in list(self.subscriptions.keys()):
            await self.unsubscribe(subscription_id)
        logger.info("All MQTT subscriptions stopped")


# Global instance
_mqtt_bridge: Optional[MqttBridge] = None


def get_mqtt_bridge() -> MqttBridge:
    """Get the global MQTT bridge instance"""
    global _mqtt_bridge
    if _mqtt_bridge is None:
        _mqtt_bridge = MqttBridge()
    return _mqtt_bridge


def is_mqtt_available() -> bool:
    """Check if MQTT functionality is available"""
    return MQTT_AVAILABLE
