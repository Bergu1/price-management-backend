from rest_framework import serializers
from db.models import ShoppingListItem, Product

class ProductShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name', 'picture', 'price1']

class ShoppingListItemSerializer(serializers.ModelSerializer):
    product = ProductShortSerializer(read_only=True)

    class Meta:
        model = ShoppingListItem
        fields = ['id', 'product', 'quantity']