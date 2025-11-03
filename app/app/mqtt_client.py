# app/mqtt_client.py
import os, json, threading, time, queue, re
from uuid import uuid4
import paho.mqtt.client as mqtt

# ================== KONFIG ==================
MQTT_HOST = os.getenv("MQTT_HOST", "mqtt")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USER = os.getenv("MQTT_USER", "backend")
MQTT_PASS = os.getenv("MQTT_PASS", "backendpass")
BASE = os.getenv("MQTT_BASE", "store")
# ============================================

_ack_waiters = {}
_ack_lock = threading.Lock()
_started_evt = threading.Event()
_connected_evt = threading.Event()

def _num(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).replace(",", ".")
    m = re.search(r"-?\d+(\.\d+)?", s)
    return float(m.group(0)) if m else None

def _shelf_from_topic(topic: str):
    parts = topic.split("/")
    try:
        i = parts.index("shelf")
        return int(parts[i+1])
    except Exception:
        return None

def _save_single_shelf(data: dict, shelf: int):
    """Zapis dla jednej półki wg reguł: 1->d1_mm, 2->d2_mm, 3->weight_g."""
    from django.db import transaction, close_old_connections
    from db.models import ShelfState

    d1 = _num(data.get("d1_mm") or data.get("d1"))
    d2 = _num(data.get("d2_mm") or data.get("d2"))
    wg = _num(data.get("weight_g"))
    if wg is None and data.get("weight_kg") is not None:
        wk = _num(data.get("weight_kg"))
        wg = wk * 1000.0 if wk is not None else None

    defaults = {}
    if shelf == 1 and d1 is not None:
        defaults["d1_mm"] = d1
    elif shelf == 2 and d2 is not None:
        defaults["d2_mm"] = d2
    elif shelf == 3 and wg is not None:
        defaults["weight_g"] = wg

    if not defaults:
        print("[TELEM] brak wartości dla wybranej półki -> skip")
        return

    close_old_connections()
    with transaction.atomic():
        ShelfState.objects.update_or_create(shelf=shelf, defaults=defaults)

def _save_batch_3_shelves(data: dict):
    from django.db import transaction, close_old_connections
    from db.models import ShelfState

    d1 = _num(data.get("d1_mm") or data.get("d1"))
    d2 = _num(data.get("d2_mm") or data.get("d2"))
    wg = _num(data.get("weight_g"))
    if wg is None and data.get("weight_kg") is not None:
        wk = _num(data.get("weight_kg"))
        wg = wk * 1000.0 if wk is not None else None

    ops = []
    if d1 is not None:
        ops.append((1, {"d1_mm": d1}))
    if d2 is not None:
        ops.append((2, {"d2_mm": d2}))
    if wg is not None:
        ops.append((3, {"weight_g": wg}))

    if not ops:
        print("[TELEM] batch: brak danych do zapisu -> skip")
        return

    close_old_connections()
    with transaction.atomic():
        for shelf, defaults in ops:
            ShelfState.objects.update_or_create(shelf=shelf, defaults=defaults)

def _save_telemetry(topic: str, data: dict):
    shelf = _shelf_from_topic(topic)
    if shelf is None:
        s = data.get("shelf")
        try:
            shelf = int(float(str(s))) if s is not None else None
        except Exception:
            shelf = None

    if shelf in (1, 2, 3):
        _save_single_shelf(data, shelf)
    else:
        _save_batch_3_shelves(data)

def _on_connect(client, userdata, flags, reason_code, properties=None):
    print("[MQTT] Connected:", reason_code)
    client.subscribe(f"{BASE}/shelf/+/display/ack", qos=1)
    client.subscribe(f"{BASE}/device/+/telemetry", qos=0)  # obecny ESP topic
    client.subscribe(f"{BASE}/shelf/+/telemetry", qos=0)   # ewentualnie docelowy topic
    _connected_evt.set()

def _on_message(client, userdata, msg):
    topic = msg.topic
    try:
        data = json.loads(msg.payload.decode("utf-8"))
    except Exception as e:
        print("[MQTT] Bad JSON:", e, "topic:", topic)
        return

    # ACK
    mid = data.get("msg_id")
    if mid:
        with _ack_lock:
            q = _ack_waiters.get(mid)
        if q:
            q.put(data)

    # TELEMETRIA
    if topic.endswith("/telemetry"):
        print(
            f"[TELEM] topic={topic} device={data.get('device','?')} ts={data.get('ts')}"
            f" d1={data.get('d1_mm')} d2={data.get('d2_mm')} weight={data.get('weight_g')}"
        )
        try:
            _save_telemetry(topic, data)
        except Exception as e:
            print("[TELEM] save error:", e)

_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"backend-{uuid4()}")
_client.username_pw_set(MQTT_USER, MQTT_PASS)
_client.on_connect = _on_connect
_client.on_message = _on_message

def start():
    if _started_evt.is_set():
        return
    _started_evt.set()
    _client.reconnect_delay_set(min_delay=1, max_delay=30)
    _client.connect_async(MQTT_HOST, MQTT_PORT, keepalive=30)
    _client.loop_start()
    print("[MQTT] client loop started")

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
