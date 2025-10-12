# app/products/views.py
from rest_framework import generics, viewsets, authentication, filters, parsers, status
from rest_framework.decorators import action
from rest_framework.response import Response
from db.models import Product
from .serializers import ProductSerializer
from .permissions import IsEmployee

# Publiczny widok listy (np. Home/Shop) — zostaw jak jest:
class ProductListView(generics.ListAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

# Panel pracownika – WSZYSTKO zablokowane dla nie-pracowników
class ProductViewSet(viewsets.ModelViewSet):
    """
    /api/products/manage/           GET lista (z wyszukiwarką), POST create
    /api/products/manage/{id}/      GET/PATCH/PUT/DELETE
    /api/products/manage/{id}/promotion/  POST(percent|price), DELETE(clear)
    """
    queryset = Product.objects.all().order_by("id")
    serializer_class = ProductSerializer
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [IsEmployee]  # <-- pełna blokada dla nie-pracowników
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "description", "country_of_origin"]
    ordering_fields = ["name", "price1", "added_data"]
    parser_classes = [parsers.JSONParser, parsers.MultiPartParser, parsers.FormParser]

    @action(detail=True, methods=["post", "delete"])
    def promotion(self, request, pk=None):
        product = self.get_object()
        if request.method.lower() == "delete":
            product.price2 = None
            product.save()
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
                product.price2 = max(0, float(product.price1) * (100 - percent) / 100.0)
            except (TypeError, ValueError):
                return Response({"detail": "Invalid percent"}, status=400)
        else:
            return Response({"detail": "Provide 'price' or 'percent'."}, status=400)

        product.save()
        return Response(self.get_serializer(product).data, status=200)


    def perform_update(self, serializer):
        # 1) zapisz produkt (rotacja cen robi się w serializer.update)
        product = serializer.save()

        # 2) weź numer półki z requestu: najpierw query ?shelf=, potem body {"shelf": }
        shelf_raw = self.request.query_params.get("shelf", None)
        if shelf_raw is None:
            shelf_raw = self.request.data.get("shelf", None)

        try:
            shelf = int(shelf_raw) if shelf_raw is not None else None
        except (TypeError, ValueError):
            shelf = None

        # 3) jeśli jest poprawny numer półki, wyślij komendę MQTT
        if shelf in (1, 2, 3):
            try:
                from app import mqtt_client
                ack = mqtt_client.publish_product_to_shelf(
                    product, shelf=shelf, retain=False, timeout=10.0
                )
                print("[MQTT] publish ack:", ack)
            except Exception as e:
                # Nie blokuj zapisu przy błędzie MQTT
                print("[MQTT] error in perform_update:", e)
        else:
            # brak / zły numer półki -> nie publikujemy
            print("[MQTT] skip publish (no valid 'shelf' provided)")

