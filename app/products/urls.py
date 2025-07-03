from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from products import views

app_name = 'products'

urlpatterns = [
    path('product_view/', views.ProductListView.as_view(), name='product_view'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)