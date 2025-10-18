# app/products/urls.py
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from products import views

app_name = "products"

router = DefaultRouter()
router.register(r"manage", views.ProductViewSet, basename="product")
router.register(r"telemetry", views.TelemetryViewSet, basename="telemetry")  # ⬅ DODANE

urlpatterns = [
    path("product_view/", views.ProductListView.as_view(), name="product_view"),  # public
    path("", include(router.urls)),  # /api/products/manage/... i /api/products/telemetry/...
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
