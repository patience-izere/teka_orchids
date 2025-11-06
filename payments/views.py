import stripe
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_http_methods
from django.contrib import messages
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
import json
import logging
from decimal import Decimal

from core.models import Order, ChefProfile, User

# Configure stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

logger = logging.getLogger(__name__)


@login_required
def setup_stripe_connect(request):
    """Start Stripe Connect onboarding for chefs"""
    if request.user.role != 'chef':
        messages.error(request, 'Only chefs can set up payment processing.')
        return redirect('client_portal:home')
    
    try:
        chef_profile = request.user.chef_profile
        
        # Create Stripe Express account if doesn't exist
        if not chef_profile.stripe_account_id:
            account = stripe.Account.create(
                type='express',
                country='US',
                email=request.user.email,
                capabilities={
                    'card_payments': {'requested': True},
                    'transfers': {'requested': True},
                }
            )
            chef_profile.stripe_account_id = account.id
            chef_profile.save()
        
        # Create account link for onboarding
        account_link = stripe.AccountLink.create(
            account=chef_profile.stripe_account_id,
            refresh_url=request.build_absolute_uri(reverse('payments:connect_refresh')),
            return_url=request.build_absolute_uri(reverse('payments:connect_return')),
            type='account_onboarding'
        )
        
        return redirect(account_link.url)
        
    except Exception as e:
        logger.error(f"Stripe Connect setup error: {str(e)}")
        messages.error(request, 'Error setting up payment processing. Please try again.')
        return redirect('chef_portal:profile')


@login_required
def connect_return(request):
    """Handle return from Stripe Connect onboarding"""
    if request.user.role != 'chef':
        return redirect('client_portal:home')
    
    try:
        chef_profile = request.user.chef_profile
        
        # Check account status
        account = stripe.Account.retrieve(chef_profile.stripe_account_id)
        
        if account.charges_enabled and account.payouts_enabled:
            chef_profile.stripe_connected = True
            chef_profile.save()
            messages.success(request, 'Payment processing successfully set up! You can now receive payments.')
        else:
            messages.warning(request, 'Payment setup is incomplete. Please complete all required information.')
        
    except Exception as e:
        logger.error(f"Connect return error: {str(e)}")
        messages.error(request, 'Error verifying payment setup.')
    
    return redirect('chef_portal:profile')


@login_required
def connect_refresh(request):
    """Handle refresh from Stripe Connect onboarding"""
    if request.user.role != 'chef':
        return redirect('client_portal:home')
    
    try:
        chef_profile = request.user.chef_profile
        
        # Create new account link
        account_link = stripe.AccountLink.create(
            account=chef_profile.stripe_account_id,
            refresh_url=request.build_absolute_uri(reverse('payments:connect_refresh')),
            return_url=request.build_absolute_uri(reverse('payments:connect_return')),
            type='account_onboarding'
        )
        
        return redirect(account_link.url)
        
    except Exception as e:
        logger.error(f"Connect refresh error: {str(e)}")
        messages.error(request, 'Error refreshing setup process.')
        return redirect('chef_portal:profile')


@login_required
@require_POST
def create_payment_intent(request):
    """Create payment intent for order checkout"""
    try:
        data = json.loads(request.body)
        order_id = data.get('order_id')
        
        order = get_object_or_404(Order, id=order_id, user=request.user)
        
        if order.status != 'pending':
            return JsonResponse({'error': 'Order cannot be paid'}, status=400)
        
        # Calculate amounts
        total_amount = int(order.total_amount * 100)  # Convert to cents
        application_fee = int(total_amount * Decimal('0.10'))  # 10% platform fee
        
        # Create payment intent
        intent = stripe.PaymentIntent.create(
            amount=total_amount,
            currency='usd',
            application_fee_amount=application_fee,
            transfer_data={
                'destination': order.chef_profile.stripe_account_id,
            },
            metadata={
                'order_id': str(order.id),
                'chef_id': str(order.chef_profile.id),
                'user_id': str(request.user.id),
            }
        )
        
        # Store payment intent ID
        order.stripe_payment_intent = intent.id
        order.save()
        
        return JsonResponse({
            'client_secret': intent.client_secret,
            'payment_intent_id': intent.id
        })
        
    except Exception as e:
        logger.error(f"Payment intent creation error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@require_POST
def stripe_webhook(request):
    """Handle Stripe webhooks"""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError:
        logger.error("Invalid payload in Stripe webhook")
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        logger.error("Invalid signature in Stripe webhook")
        return HttpResponse(status=400)
    
    # Handle the event
    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        handle_payment_success(payment_intent)
    
    elif event['type'] == 'payment_intent.payment_failed':
        payment_intent = event['data']['object']
        handle_payment_failure(payment_intent)
    
    elif event['type'] == 'account.updated':
        account = event['data']['object']
        handle_account_update(account)
    
    else:
        logger.info(f"Unhandled Stripe webhook event: {event['type']}")
    
    return HttpResponse(status=200)


def handle_payment_success(payment_intent):
    """Handle successful payment"""
    try:
        order_id = payment_intent['metadata'].get('order_id')
        if not order_id:
            return
        
        order = Order.objects.get(id=order_id)
        order.status = 'confirmed'
        order.payment_status = 'paid'
        order.stripe_payment_intent = payment_intent['id']
        order.save()
        
        logger.info(f"Payment successful for order {order_id}")
        
    except Order.DoesNotExist:
        logger.error(f"Order not found for payment intent {payment_intent['id']}")
    except Exception as e:
        logger.error(f"Error handling payment success: {str(e)}")


def handle_payment_failure(payment_intent):
    """Handle failed payment"""
    try:
        order_id = payment_intent['metadata'].get('order_id')
        if not order_id:
            return
        
        order = Order.objects.get(id=order_id)
        order.payment_status = 'failed'
        order.save()
        
        logger.info(f"Payment failed for order {order_id}")
        
    except Order.DoesNotExist:
        logger.error(f"Order not found for payment intent {payment_intent['id']}")
    except Exception as e:
        logger.error(f"Error handling payment failure: {str(e)}")


def handle_account_update(account):
    """Handle Stripe account updates"""
    try:
        chef_profile = ChefProfile.objects.get(stripe_account_id=account['id'])
        
        # Update connection status
        chef_profile.stripe_connected = (
            account.get('charges_enabled', False) and 
            account.get('payouts_enabled', False)
        )
        chef_profile.save()
        
        logger.info(f"Updated Stripe account status for chef {chef_profile.id}")
        
    except ChefProfile.DoesNotExist:
        logger.error(f"Chef profile not found for Stripe account {account['id']}")
    except Exception as e:
        logger.error(f"Error handling account update: {str(e)}")


@login_required
def payment_success(request, order_id):
    """Payment success page"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    context = {
        'order': order,
    }
    
    return render(request, 'payments/success.html', context)


@login_required
def payment_cancel(request, order_id):
    """Payment cancellation page"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    context = {
        'order': order,
    }
    
    return render(request, 'payments/cancel.html', context)