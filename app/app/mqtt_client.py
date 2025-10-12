import os, json, threading, time, queue
from uuid import uuid4
import paho.mqtt.client as mqtt

MQTT_HOST = os.getenv("MQTT_HOST", "mqtt")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USER = os.getenv("MQTT_USER", "backend")
MQTT_PASS = os.getenv("MQTT_PASS", "backendpass")
BASE = "store"

_ack_waiters = {}
_ack_lock = threading.Lock()
_connected_evt = threading.Event()

def _on_connect(client, userdata, flags, reason_code, properties=None):
    print("[MQTT] Connected:", reason_code)
    client.subscribe(f"{BASE}/shelf/+/display/ack", qos=1)
    _connected_evt.set()

def _on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode("utf-8"))
    except Exception as e:
        print("[MQTT] Bad JSON:", e)
        return
    mid = data.get("msg_id")
    if not mid:
        return
    with _ack_lock:
        q = _ack_waiters.get(mid)
    if q:
        q.put(data)

_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"backend-{uuid4()}")
_client.username_pw_set(MQTT_USER, MQTT_PASS)
_client.on_connect = _on_connect
_client.on_message = _on_message

def start():
    _client.connect_async(MQTT_HOST, MQTT_PORT, keepalive=30)
    _client.loop_start()

def _wait_connected(timeout=5.0):
    _connected_evt.wait(timeout=timeout)
    return _connected_evt.is_set()

def publish_product_to_shelf(product, shelf: int, retain=True, timeout=10.0):
    _wait_connected(3.0)
    msg_id = str(uuid4())
    payload = {
        "msg_id": msg_id,
        "shelf": shelf,
        "name": product.name,
        "country": product.country_of_origin or "",
        "price": float(product.price1),
        "currency": "PLN",
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    topic = f"{BASE}/shelf/{shelf}/display/cmd"
    print(f"[MQTT] publish -> {topic} {json.dumps(payload, ensure_ascii=False)}")

    q = queue.Queue()
    with _ack_lock:
        _ack_waiters[msg_id] = q
    try:
        _client.publish(topic, json.dumps(payload), qos=1, retain=False)
        return q.get(timeout=timeout)
    except queue.Empty:
        return {"status": "timeout", "msg_id": msg_id}
    finally:
        with _ack_lock:
            _ack_waiters.pop(msg_id, None)
