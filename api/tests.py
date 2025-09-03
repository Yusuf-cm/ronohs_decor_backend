# In api/views.py

from rest_framework import generics
from .models import Product
from .serializers import ProductSerializer

# This view will handle GET requests to list all products.
class ProductListAPIView(generics.ListAPIView):
    queryset = Product.objects.all() # The data we want to list
    serializer_class = ProductSerializer # The serializer to use for translation