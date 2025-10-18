# app/apps.py
import os
import sys
from django.apps import AppConfig as DjangoAppConfig

def _should_start_mqtt() -> bool:
    # pozwól wyłączyć przez ENV (np. w testach/komendach)
    if os.environ.get("MQTT_DISABLED") == "1":
        return False

    # odpalaj tylko przy serwerach www, nie przy migrate/shell
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    return cmd in {"runserver", "gunicorn", "uvicorn", "daphne"}

class AppConfig(DjangoAppConfig):
    name = "app"
    verbose_name = "App"

    def ready(self):
        if not _should_start_mqtt():
            return

        # (opcjonalnie) jeżeli kiedyś włączysz autoreloader, to unikniesz duplikacji:
        if os.environ.get("RUN_MAIN") != "true" and os.environ.get("DJANGO_AUTORELOAD") == "1":
            return

        try:
            from . import mqtt_client
            mqtt_client.start()  # idempotentne (patrz pkt 2)
            print("[MQTT] client loop started in Django process")
        except Exception as e:
            print("[MQTT] start error:", e)
