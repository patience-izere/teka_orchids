from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    # Stripe Connect setup for chefs
    path('connect/setup/', views.setup_stripe_connect, name='setup_connect'),
    path('connect/return/', views.connect_return, name='connect_return'),
    path('connect/refresh/', views.connect_refresh, name='connect_refresh'),
    
    # Payment processing
    path('create-payment-intent/', views.create_payment_intent, name='create_payment_intent'),
    path('success/<uuid:order_id>/', views.payment_success, name='success'),
    path('cancel/<uuid:order_id>/', views.payment_cancel, name='cancel'),
    
    # Webhooks
    path('webhook/stripe/', views.stripe_webhook, name='stripe_webhook'),
]