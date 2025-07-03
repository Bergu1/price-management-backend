from rest_framework import serializers
from db.models import Product

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            'name',
            'description',
            'picture',
            'country_of_origin',
            'distance',
            'price1',
        ]
