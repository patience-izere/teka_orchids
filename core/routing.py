from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/orders/', consumers.OrderConsumer.as_asgi()),
    path('ws/chef/<uuid:chef_id>/', consumers.ChefConsumer.as_asgi()),
    path('ws/client/<uuid:client_id>/', consumers.ClientConsumer.as_asgi()),
]