# app/products/serializers.py
from rest_framework import serializers
from decimal import Decimal, InvalidOperation
from db.models import Product

class ProductSerializer(serializers.ModelSerializer):
    availability = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "description",
            "picture",
            "country_of_origin",
            "availability",
            "price1",   # aktualna
            "price2",   # poprzednia
            "price3",   # przed-poprzednia
            "is_active",
            "added_data",
        ]
        read_only_fields = ["id", "added_data", "availability", "price2", "price3"]

    def get_availability(self, obj):
        for attr in ("availability", "stock", "distance"):
            if hasattr(obj, attr):
                return getattr(obj, attr)
        return None

    def _to_decimal(self, v):
        try:
            return Decimal(str(v))
        except (InvalidOperation, TypeError, ValueError):
            return None

    def update(self, instance, validated_data):
        """
        Jeżeli przychodzi nowa price1 i różni się od bieżącej:
        price3 <- price2, price2 <- stare price1, price1 <- nowe.
        price2/price3 z requestu są ignorowane (read-only).
        """
        # Zabezpieczenie: nie pozwalaj nadpisywać price2/price3 z zewnątrz
        validated_data.pop("price2", None)
        validated_data.pop("price3", None)

        if "price1" in validated_data:
            new_p = self._to_decimal(validated_data.get("price1"))
            old_p = self._to_decimal(instance.price1)

            if new_p is not None and old_p is not None and new_p != old_p:
                # rotacja historii cen
                instance.price3 = instance.price2
                instance.price2 = instance.price1
                instance.price1 = new_p
                # usuwamy z validated_data, żeby super().update nie nadpisał
                validated_data.pop("price1", None)

        # reszta pól jak zwykle
        return super().update(instance, validated_data)
