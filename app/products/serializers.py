# app/products/serializers.py
from decimal import Decimal, InvalidOperation
from rest_framework import serializers
from db.models import Product, ShelfState


class ProductSerializer(serializers.ModelSerializer):
    availability = serializers.SerializerMethodField(read_only=True)
    d1_mm = serializers.SerializerMethodField(read_only=True)
    d2_mm = serializers.SerializerMethodField(read_only=True)
    weight_g = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Product
        fields = [
            "id", "name", "description", "picture", "country_of_origin",
            "availability",
            "d1_mm", "d2_mm", "weight_g",
            "price1", "price2", "price3", "is_active", "added_data",
            "shelf_number",
        ]
        read_only_fields = [
            "id", "added_data", "availability", "price2", "price3",
            "d1_mm", "d2_mm", "weight_g",
        ]

    def get_availability(self, obj):
        """
        Pola telemetryczne są adnotowane w queryset.
        Tutaj zwracamy None, bo frontend sam liczy dostępność z d1/d2/weight_g.
        """
        return None

    def get_d1_mm(self, obj):
        return getattr(obj, "d1_mm", None)

    def get_d2_mm(self, obj):
        return getattr(obj, "d2_mm", None)

    def get_weight_g(self, obj):
        return getattr(obj, "weight_g", None)

    # --- logika cen ---
    def _to_decimal(self, v):
        try:
            return Decimal(str(v))
        except (InvalidOperation, TypeError, ValueError):
            return None

    def update(self, instance, validated_data):
        validated_data.pop("price2", None)
        validated_data.pop("price3", None)

        if "price1" in validated_data:
            new_p = self._to_decimal(validated_data.get("price1"))
            old_p = self._to_decimal(instance.price1)
            if new_p is not None and old_p is not None and new_p != old_p:
                instance.price3 = instance.price2
                instance.price2 = instance.price1
                instance.price1 = new_p
                validated_data.pop("price1", None)

        return super().update(instance, validated_data)

class ShelfStateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShelfState
        fields = ["shelf", "d1_mm", "d2_mm", "weight_g", "updated_at"]
        read_only_fields = ["updated_at"]
