from django.db.models import OuterRef, Subquery
from rest_framework import (
    generics, viewsets, authentication, filters, parsers, status, permissions, mixins
)
from rest_framework.decorators import action
from rest_framework.response import Response

from db.models import Product, ShelfState
from .serializers import ProductSerializer, ShelfStateSerializer
from .permissions import IsEmployee


def with_telemetry(qs):
    """
    Dołącza wartości z ShelfState wg Product.shelf_number.
    Półka 1 -> d1_mm, półka 2 -> d2_mm, półka 3 -> weight_g.
    Jeśli produkt nie ma shelf_number lub brak rekordu — pola będą NULL.
    """
    ss = ShelfState.objects.filter(shelf=OuterRef("shelf_number"))
    return qs.annotate(
        d1_mm=Subquery(ss.values("d1_mm")[:1]),
        d2_mm=Subquery(ss.values("d2_mm")[:1]),
        weight_g=Subquery(ss.values("weight_g")[:1]),
    )


# --------- Produkty ----------
class ProductListView(generics.ListAPIView):
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get_queryset(self):
        return with_telemetry(Product.objects.all())


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all().order_by("id")
    serializer_class = ProductSerializer

    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [IsEmployee]

    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "description", "country_of_origin"]
    ordering_fields = ["name", "price1", "added_data"]
    parser_classes = [parsers.JSONParser, parsers.MultiPartParser, parsers.FormParser]

    def get_queryset(self):
        return with_telemetry(super().get_queryset())

    @action(detail=True, methods=["post", "delete"])
    def promotion(self, request, pk=None):
        product = self.get_object()
        if request.method.lower() == "delete":
            product.price2 = None
            product.save(update_fields=["price2"])
            return Response(status=status.HTTP_204_NO_CONTENT)

        price = request.data.get("price")
        percent = request.data.get("percent")

        if price is not None:
            try:
                product.price2 = float(price)
            except (TypeError, ValueError):
                return Response({"detail": "Invalid price"}, status=400)
        elif percent is not None:
            try:
                percent = float(percent)
                product.price2 = max(0.0, float(product.price1) * (100.0 - percent) / 100.0)
            except (TypeError, ValueError):
                return Response({"detail": "Invalid percent"}, status=400)
        else:
            return Response({"detail": "Provide 'price' or 'percent'."}, status=400)

        product.save(update_fields=["price2"])
        return Response(self.get_serializer(product).data, status=200)

    def perform_update(self, serializer):
        product = serializer.save()
        shelf_raw = self.request.query_params.get("shelf")
        if shelf_raw is None:
            shelf_raw = self.request.data.get("shelf")

        try:
            shelf = int(shelf_raw) if shelf_raw is not None else None
        except (TypeError, ValueError):
            shelf = None

        if shelf in (1, 2, 3):
            if product.shelf_number != shelf:
                product.shelf_number = shelf
                product.save(update_fields=["shelf_number"])

            try:
                from app import mqtt_client
                ack = mqtt_client.publish_product_to_shelf(
                    product, shelf=shelf, retain=False, timeout=10.0
                )
                print("[MQTT] publish ack:", ack)
            except Exception as e:
                print("[MQTT] error in perform_update:", e)
        else:
            print("[MQTT] skip publish (no valid 'shelf' provided)")


# --------- TELEMETRIA ----------
def _num(v):
    """czyści stringi typu '571 mm'/'3.6 g' → float; None jeśli brak."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).replace(",", ".")
    import re
    m = re.search(r"-?\d+(\.\d+)?", s)
    return float(m.group(0)) if m else None


class TelemetryViewSet(mixins.CreateModelMixin,
                       mixins.UpdateModelMixin,
                       mixins.ListModelMixin,
                       viewsets.GenericViewSet):
    """
    POST /api/products/telemetry/ – upsert ostatniego stanu PÓŁKI.
    Mapowanie:
      - shelf=1 -> używamy tylko d1_mm
      - shelf=2 -> używamy tylko d2_mm
      - shelf=3 -> używamy tylko weight_g

    Przykłady payloadu:
      {"shelf":1, "d1_mm":470}
      {"shelf":2, "d2_mm":530}
      {"shelf":3, "weight_g":1600}
    """
    queryset = ShelfState.objects.all()
    serializer_class = ShelfStateSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def create(self, request, *args, **kwargs):
        shelf = _num(request.data.get("shelf"))
        if shelf is None:
            return Response({"detail": "Field 'shelf' is required"}, status=400)
        shelf = int(shelf)

        d1 = _num(request.data.get("d1_mm") or request.data.get("d1"))
        d2 = _num(request.data.get("d2_mm") or request.data.get("d2"))
        wg = _num(request.data.get("weight_g"))
        if wg is None and request.data.get("weight_kg") is not None:
            wk = _num(request.data.get("weight_kg"))
            wg = wk * 1000.0 if wk is not None else None
            
        defaults = {}
        if shelf == 1 and d1 is not None:
            defaults["d1_mm"] = d1
        elif shelf == 2 and d2 is not None:
            defaults["d2_mm"] = d2
        elif shelf == 3 and wg is not None:
            defaults["weight_g"] = wg

        if not defaults:
            return Response({"detail": "Provide value for the selected shelf"}, status=400)

        obj, _ = ShelfState.objects.update_or_create(shelf=shelf, defaults=defaults)
        return Response(ShelfStateSerializer(obj).data, status=201)
