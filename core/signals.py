from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Order, Review
import json


channel_layer = get_channel_layer()


@receiver(post_save, sender=Order)
def order_created_notification(sender, instance, created, **kwargs):
    """
    Send real-time notification when a new order is created
    """
    if created:
        # Notify chef of new order
        async_to_sync(channel_layer.group_send)(
            f'chef_{instance.chef_profile.user.id}',
            {
                'type': 'new_order',
                'message': f'New order #{str(instance.id)[:8]} received!',
                'order_id': str(instance.id),
                'client_name': instance.client.get_full_name() or instance.client.username,
                'total_amount': str(instance.total_amount),
            }
        )


@receiver(pre_save, sender=Order)
def order_status_changed_notification(sender, instance, **kwargs):
    """
    Send real-time notification when order status changes
    """
    if instance.pk:  # Only for existing orders
        try:
            old_instance = Order.objects.get(pk=instance.pk)
            if old_instance.status != instance.status:
                # Status changed, notify client
                status_messages = {
                    'confirmed': f'Your order has been confirmed by {instance.chef_profile.user.get_full_name() or instance.chef_profile.user.username}!',
                    'in_progress': 'Your order is being prepared in the kitchen.',
                    'ready': 'Your order is ready for pickup/delivery!',
                    'out_for_delivery': 'Your order is on the way!',
                    'delivered': 'Your order has been delivered. Enjoy your meal!',
                    'cancelled': 'Your order has been cancelled.',
                    'rejected': 'Sorry, your order was rejected by the chef.',
                }
                
                message = status_messages.get(instance.status, f'Order status updated to {instance.status}')
                
                async_to_sync(channel_layer.group_send)(
                    f'client_{instance.client.id}',
                    {
                        'type': 'order_status_update',
                        'message': message,
                        'order_id': str(instance.id),
                        'status': instance.status,
                        'chef_name': instance.chef_profile.user.get_full_name() or instance.chef_profile.user.username,
                    }
                )
        except Order.DoesNotExist:
            pass


@receiver(post_save, sender=Review)
def review_created_notification(sender, instance, created, **kwargs):
    """
    Notify chef when they receive a new review
    """
    if created:
        message = f'You received a {instance.rating}-star review!'
        if instance.comment:
            message += f' "{instance.comment[:50]}..."'
        
        async_to_sync(channel_layer.group_send)(
            f'chef_{instance.chef_profile.user.id}',
            {
                'type': 'order_notification',
                'message': message,
                'order_id': str(instance.order.id),
            }
        )