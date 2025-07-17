from rest_framework.response import Response
from rest_framework import generics, authentication, permissions
from rest_framework import status
from db.models import ShoppingListItem
from rest_framework import viewsets
from .serializers import ShoppingListItemSerializer


class ShoppingListItemViewSet(viewsets.ModelViewSet):
    serializer_class = ShoppingListItemSerializer
    authentication_classes = [authentication.TokenAuthentication] 
    permission_classes = [permissions.IsAuthenticated]
    

    def get_queryset(self):
        return ShoppingListItem.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        user = request.user
        product_id = request.data.get("product")
        quantity = int(request.data.get("quantity", 1))
        existing_item = ShoppingListItem.objects.filter(user=user, product_id=product_id).first()

        if existing_item:
            existing_item.quantity += quantity
            existing_item.save()
            serializer = self.get_serializer(existing_item)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        else:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save(user=user, product_id=product_id)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
