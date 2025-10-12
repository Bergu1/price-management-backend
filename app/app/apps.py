from django.apps import AppConfig

class AppConfig(AppConfig):
    name = "app"
    verbose_name = "App"

    def ready(self):
        # odpal MQTT w tym samym procesie co Django
        try:
            from . import mqtt_client
            mqtt_client.start()
            print("[MQTT] client loop started in Django process")
        except Exception as e:
            print("[MQTT] start error:", e)
