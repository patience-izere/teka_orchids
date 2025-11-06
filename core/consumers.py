import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import Order, ChefProfile

User = get_user_model()


class OrderConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time order updates
    """
    
    async def connect(self):
        self.user = self.scope['user']
        if self.user.is_anonymous:
            await self.close()
            return
        
        # Join user-specific group
        self.group_name = f'user_{self.user.id}'
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()
    
    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        # Handle incoming messages from client if needed
        pass
    
    async def order_notification(self, event):
        """Send order notification to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'order_notification',
            'message': event['message'],
            'order_id': event['order_id'],
            'status': event.get('status'),
        }))


class ChefConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer specifically for chef notifications
    """
    
    async def connect(self):
        self.user = self.scope['user']
        self.chef_id = self.scope['url_route']['kwargs']['chef_id']
        
        if self.user.is_anonymous or self.user.role != 'chef':
            await self.close()
            return
        
        # Verify user is the chef
        if str(self.user.id) != str(self.chef_id):
            await self.close()
            return
        
        self.group_name = f'chef_{self.chef_id}'
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()
    
    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        # Handle chef-specific messages
        pass
    
    async def new_order(self, event):
        """Send new order notification to chef"""
        await self.send(text_data=json.dumps({
            'type': 'new_order',
            'message': event['message'],
            'order_id': event['order_id'],
            'client_name': event.get('client_name'),
            'total_amount': event.get('total_amount'),
        }))


class ClientConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for client order tracking
    """
    
    async def connect(self):
        self.user = self.scope['user']
        self.client_id = self.scope['url_route']['kwargs']['client_id']
        
        if self.user.is_anonymous or self.user.role != 'client':
            await self.close()
            return
        
        # Verify user is the client
        if str(self.user.id) != str(self.client_id):
            await self.close()
            return
        
        self.group_name = f'client_{self.client_id}'
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()
    
    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        # Handle client-specific messages
        pass
    
    async def order_status_update(self, event):
        """Send order status update to client"""
        await self.send(text_data=json.dumps({
            'type': 'order_status_update',
            'message': event['message'],
            'order_id': event['order_id'],
            'status': event['status'],
            'chef_name': event.get('chef_name'),
        }))