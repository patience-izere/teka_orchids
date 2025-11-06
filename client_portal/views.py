import os
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseRedirect
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q, Avg, Count
from django.conf import settings
# Removed GIS imports - using regular coordinates for development
from core.models import User, ChefProfile, MenuItem, Order, OrderItem, Review
import json
from decimal import Decimal


def home(request):
    """Homepage with chef discovery"""
    # Get featured chefs (top rated, active)
    featured_chefs = ChefProfile.objects.filter(
        is_available=True,
        is_verified=True,
        average_rating__gte=4.0
    ).order_by('-average_rating')[:6]
    
    # Get some stats for the homepage
    stats = {
        'total_chefs': ChefProfile.objects.filter(is_verified=True).count(),
        'total_orders': Order.objects.filter(status='delivered').count(),
        'avg_rating': Review.objects.aggregate(avg=Avg('rating'))['avg'] or 4.9,
        #'cities': ChefProfile.objects.values('city').distinct().count(),
    }
    
    context = {
        'featured_chefs': featured_chefs,
        'stats': stats,
    }
    return render(request, 'client_portal/home.html', context)


def chef_list(request):
    """List all available chefs with filtering"""
    # (no-op) chef_list is intentionally public and returns 200 for all users
    chefs = ChefProfile.objects.filter(
        is_verified=True
    ).select_related('user').prefetch_related('menu_items')
    
    # Search functionality
    query = request.GET.get('q', '')
    if query:
        chefs = chefs.filter(
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            #Q(cuisine_specialty__icontains=query) |
            Q(bio__icontains=query) |
            Q(menu_items__name__icontains=query)
        ).distinct()
    
    # Location filtering
    city = request.GET.get('city', '')
    state = request.GET.get('state', '')
    cuisine = request.GET.get('cuisine', '')
    rating = request.GET.get('rating', '')
    available_now = request.GET.get('available_now', '')
    
    if city:
        chefs = chefs.filter(address__icontains=city)
    if state:
        chefs = chefs.filter(address__icontains=state)
    if cuisine:
        chefs = chefs.filter(cuisine_specialty__icontains=cuisine)
    if available_now:
        chefs = chefs.filter(is_available=True)
    
    # Filter by rating using existing field
    if rating:
        try:
            min_rating = float(rating)
            chefs = chefs.filter(average_rating__gte=min_rating)
        except (ValueError, TypeError):
            pass
    
    # Sorting
    sort_by = request.GET.get('sort', '')
    if sort_by == 'rating':
        chefs = chefs.order_by('-average_rating', '-total_reviews')
    elif sort_by == 'reviews':
        chefs = chefs.order_by('-total_reviews')
    else:
        chefs = chefs.order_by('-average_rating', '-is_available')
    
    # Pagination
    paginator = Paginator(chefs, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get unique cuisine types for filter
    # cuisine_types = ChefProfile.objects.filter(
    #     is_verified=True
    # ).values_list('cuisine_specialty', flat=True).distinct().order_by('cuisine_specialty')
    
    context = {
        'chefs': page_obj,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        #'cuisine_types': cuisine_types,
        'query': query,
    }
    return render(request, 'client_portal/chef_list.html', context)


def chef_detail(request, chef_id):
    """Detailed chef profile with menu"""
    # Support chef lookup by chef profile id (int primary key)
    try:
        chef = get_object_or_404(ChefProfile, id=chef_id, is_verified=True)
    except Exception:
        # Fallback to previous behavior (lookup by user id) for compatibility
        chef = get_object_or_404(ChefProfile, user__id=chef_id, is_verified=True)
    
    # Use existing rating fields from model
    # These are already calculated: chef.average_rating, chef.total_reviews
    
    # Get menu items grouped by category
    menu_items = MenuItem.objects.filter(
        chef_profile=chef
    ).order_by('category', 'name')
    
    # Get menu categories
    menu_categories = menu_items.values_list('category', flat=True).distinct()
    
    # Get recent reviews
    reviews = Review.objects.filter(
        chef_profile=chef
    ).select_related('client').order_by('-created_at')[:10]
    
    context = {
        'chef': chef,
        'menu_categories': menu_categories,
        'reviews': reviews,
    }
    return render(request, 'client_portal/chef_detail.html', context)


def search_chefs(request):
    """Advanced chef search functionality - redirects to chef_list with parameters"""
    # The search endpoint should render the chef_list with the given GET params
    # so clients can hit /search/?q=... and receive a 200 with results.
    return chef_list(request)


def login_view(request):
    """User login"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        if user is not None and user.role == 'client':
            login(request, user)
            messages.success(request, 'Welcome back!')
            return redirect(request.GET.get('next', 'client_portal:home'))
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'client_portal/auth/login.html')


def register_view(request):
    """User registration"""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        phone_number = request.POST.get('phone_number')
        
        # Validation
        if password != password_confirm:
            messages.error(request, 'Passwords do not match.')
        elif User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
        elif User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered.')
        else:
            try:
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    phone_number=phone_number,
                    role='client'
                )
                login(request, user)
                messages.success(request, 'Account created successfully!')
                return redirect('client_portal:home')
            except Exception as e:
                messages.error(request, f'Error creating account: {str(e)}')
    
    return render(request, 'client_portal/auth/register.html')


def logout_view(request):
    """User logout"""
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('client_portal:home')


@login_required
def client_dashboard(request):
    """Client dashboard with order overview"""
    recent_orders = Order.objects.filter(client=request.user).order_by('-created_at')[:5]
    active_orders = Order.objects.filter(
        client=request.user,
        status__in=['placed', 'confirmed', 'in_progress', 'ready', 'out_for_delivery']
    ).order_by('-created_at')
    
    context = {
        'recent_orders': recent_orders,
        'active_orders': active_orders,
    }
    return render(request, 'chef_portal/dashboard.html', context)


@login_required
def order_history(request):
    """Complete order history"""
    orders = Order.objects.filter(client=request.user).order_by('-created_at')
    
    paginator = Paginator(orders, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {'page_obj': page_obj}
    return render(request, 'client_portal/order_history.html', context)


@login_required
def order_detail(request, order_id):
    """Detailed order view"""
    order = get_object_or_404(Order, id=order_id, client=request.user)
    order_items = OrderItem.objects.filter(order=order)
    
    context = {
        'order': order,
        'order_items': order_items,
        'can_review': order.status == 'delivered' and not hasattr(order, 'review')
    }
    return render(request, 'client_portal/order_detail.html', context)


@login_required
def profile_settings(request):
    """User profile management"""
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.email = request.POST.get('email', '')
        user.phone_number = request.POST.get('phone_number', '')
        
        try:
            user.save()
            messages.success(request, 'Profile updated successfully!')
        except Exception as e:
            messages.error(request, f'Error updating profile: {str(e)}')
        
        return redirect('client_portal:profile_settings')
    
    return render(request, 'client_portal/profile_settings.html')


def cart_view(request):
    """Shopping cart view"""
    return render(request, 'client_portal/cart.html')


@login_required
def checkout(request):
    """Checkout process from cart"""
    context = {
        'checkout_type': 'cart',
        'stripe_publishable_key': getattr(settings, 'STRIPE_PUBLISHABLE_KEY', ''),
    }
    return render(request, 'client_portal/checkout.html', context)


# AJAX Views
@require_http_methods(["POST"])
def add_to_cart(request):
    """Add item to cart with validation"""
    try:
        data = json.loads(request.body)
        menu_item_id = data.get('menu_item_id')
        quantity = int(data.get('quantity', 1))
        special_instructions = data.get('special_instructions', '')
        
        # Validate input
        if quantity <= 0 or quantity > 10:
            return JsonResponse({'success': False, 'error': 'Invalid quantity'}, status=400)
        
        # Validate menu item exists and is available
        menu_item = get_object_or_404(MenuItem, id=menu_item_id, is_available=True)
        
        # Check if chef is accepting orders
        if not menu_item.chef_profile.is_available:
            return JsonResponse({
                'success': False, 
                'error': 'Chef is currently not accepting orders'
            }, status=400)
        
        # Persist cart in session (tests expect a 'cart' session key)
        session = request.session
        cart = session.get('cart', {})
        cart[str(menu_item.id)] = {
            'id': str(menu_item.id),
            'name': menu_item.name,
            'price': float(menu_item.price),
            'quantity': quantity,
            'special_instructions': special_instructions,
            'chef_id': str(menu_item.chef_profile.id),
        }
        session['cart'] = cart
        session.modified = True

        # Return item data for frontend cart
        return JsonResponse({
            'success': True,
            'message': f'Added {menu_item.name} to cart',
            'item': {
                'id': str(menu_item.id),
                'name': menu_item.name,
                'price': float(menu_item.price),
                'chef_id': str(menu_item.chef_profile.id),
                'chef_name': menu_item.chef_profile.user.get_full_name() or menu_item.chef_profile.user.username,
                'quantity': quantity,
                'special_instructions': special_instructions,
                'image': menu_item.image.url if menu_item.image else None
            }
        })
    except ValueError:
        return JsonResponse({'success': False, 'error': 'Invalid quantity format'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST"])
def remove_from_cart(request):
    """Remove item from cart"""
    try:
        data = json.loads(request.body)
        menu_item_id = data.get('menu_item_id')
        
        # Validate menu item exists (optional, since it's just for cart management)
        if menu_item_id:
            MenuItem.objects.filter(id=menu_item_id).exists()
        
        return JsonResponse({
            'success': True,
            'message': 'Item removed from cart'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@require_http_methods(["POST"])
def update_cart_item(request):
    """Update cart item quantity"""
    try:
        data = json.loads(request.body)
        menu_item_id = data.get('menu_item_id')
        quantity = int(data.get('quantity', 1))
        
        # Validate input
        if quantity < 0 or quantity > 10:
            return JsonResponse({'success': False, 'error': 'Invalid quantity'}, status=400)
        
        # Validate menu item exists
        menu_item = get_object_or_404(MenuItem, id=menu_item_id)
        
        if quantity == 0:
            return JsonResponse({
                'success': True,
                'message': 'Item removed from cart',
                'action': 'removed'
            })
        else:
            return JsonResponse({
                'success': True,
                'message': 'Cart updated',
                'action': 'updated',
                'quantity': quantity
            })
    except ValueError:
        return JsonResponse({'success': False, 'error': 'Invalid quantity format'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST"])
def validate_cart(request):
    """Validate cart items before checkout"""
    try:
        data = json.loads(request.body)
        items = data.get('items', [])
        
        validation_results = []
        total_valid = True
        
        for item in items:
            try:
                menu_item = MenuItem.objects.get(id=item['id'])
                
                # Check availability
                if not menu_item.is_available:
                    validation_results.append({
                        'id': item['id'],
                        'valid': False,
                        'error': f"{menu_item.name} is no longer available"
                    })
                    total_valid = False
                    continue
                
                # Check chef availability
                if not menu_item.chef_profile.is_available:
                    validation_results.append({
                        'id': item['id'],
                        'valid': False,
                        'error': f"Chef {menu_item.chef_profile.user.get_full_name()} is not accepting orders"
                    })
                    total_valid = False
                    continue
                
                # Check price changes
                if float(item['price']) != float(menu_item.price):
                    validation_results.append({
                        'id': item['id'],
                        'valid': True,
                        'warning': f"Price for {menu_item.name} has changed from ${item['price']} to ${menu_item.price}",
                        'new_price': float(menu_item.price)
                    })
                else:
                    validation_results.append({
                        'id': item['id'],
                        'valid': True
                    })
                
            except MenuItem.DoesNotExist:
                validation_results.append({
                    'id': item['id'],
                    'valid': False,
                    'error': 'Item no longer exists'
                })
                total_valid = False
        
        return JsonResponse({
            'success': True,
            'all_valid': total_valid,
            'items': validation_results
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def get_chef_menu_ajax(request, chef_id):
    """Get chef menu via AJAX"""
    try:
        chef = get_object_or_404(ChefProfile, id=chef_id, is_verified=True)
        menu_items = MenuItem.objects.filter(chef_profile=chef, is_available=True)
        
        items_data = []
        for item in menu_items:
            items_data.append({
                'id': str(item.id),
                'name': item.name,
                'description': item.description,
                'price': str(item.price),
                'category': item.get_category_display(),
                'image': item.image.url if item.image else None,
                'is_vegetarian': item.is_vegetarian,
                'is_vegan': item.is_vegan,
                'is_gluten_free': item.is_gluten_free,
                'customization_options': item.customization_options
            })
        
        return JsonResponse({
            'success': True,
            'items': items_data
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def submit_review_ajax(request):
    """Submit review via AJAX"""
    try:
        data = json.loads(request.body)
        order_id = data.get('order_id')
        rating = int(data.get('rating'))
        comment = data.get('comment', '')
        
        order = get_object_or_404(Order, id=order_id, client=request.user, status='delivered')
        
        if hasattr(order, 'review'):
            return JsonResponse({'success': False, 'error': 'Review already submitted'}, status=400)
        
        if not (1 <= rating <= 5):
            return JsonResponse({'success': False, 'error': 'Invalid rating'}, status=400)
        
        review = Review.objects.create(
            order=order,
            client=request.user,
            chef_profile=order.chef_profile,
            rating=rating,
            comment=comment
        )
        
        # Update chef's average rating
        chef_profile = order.chef_profile
        reviews = Review.objects.filter(chef_profile=chef_profile, is_approved=True)
        if reviews.exists():
            avg_rating = reviews.aggregate(avg=Avg('rating'))['avg']
            chef_profile.average_rating = round(avg_rating, 2)
            chef_profile.total_reviews = reviews.count()
            chef_profile.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Review submitted successfully'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
def checkout(request, order_id):
    """Checkout page with Stripe payment integration"""
    order = get_object_or_404(Order, id=order_id, client=request.user)
    
    if order.payment_status == 'paid':
        messages.info(request, 'This order has already been paid.')
        return redirect('client_portal:order_detail', order_id=order.id)
    
    context = {
        'order': order,
        'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY,
    }
    
    return render(request, 'client_portal/checkout.html', context)


@login_required
@require_http_methods(["POST"])
def create_order(request):
    """Create order from cart data"""
    try:
        data = json.loads(request.body)
        items = data.get('items', [])
        delivery_address = data.get('delivery_address')
        delivery_instructions = data.get('delivery_instructions', '')
        promo_discount = data.get('promo_discount', 0)
        
        if not items:
            return JsonResponse({'success': False, 'error': 'Cart is empty'}, status=400)
        
        if not delivery_address:
            return JsonResponse({'success': False, 'error': 'Delivery address is required'}, status=400)
        
        # Get the first item to determine the chef (assuming single chef per order for now)
        first_item = MenuItem.objects.get(id=items[0]['id'])
        chef_profile = first_item.chef_profile
        
        # Calculate totals
        subtotal = Decimal('0.00')
        for item_data in items:
            menu_item = MenuItem.objects.get(id=item_data['id'])
            item_total = menu_item.price * item_data['quantity']
            subtotal += item_total
        
        delivery_fee = Decimal('5.00')
        platform_fee = subtotal * Decimal('0.10')  # 10% platform fee
        total_amount = subtotal + delivery_fee + platform_fee - Decimal(str(promo_discount))
        
        # Create the order
        order = Order.objects.create(
            client=request.user,
            chef_profile=chef_profile,
            delivery_address=delivery_address,
            delivery_instructions=delivery_instructions,
            subtotal=subtotal,
            delivery_fee=delivery_fee,
            platform_fee=platform_fee,
            total_amount=total_amount,
            status='pending'
        )
        
        # Create order items
        for item_data in items:
            menu_item = MenuItem.objects.get(id=item_data['id'])
            OrderItem.objects.create(
                order=order,
                menu_item=menu_item,
                quantity=item_data['quantity'],
                price=menu_item.price,
                subtotal=menu_item.price * item_data['quantity'],
                special_instructions=item_data.get('special_instructions', '')
            )
        
        return JsonResponse({
            'success': True,
            'order_id': str(order.id),
            'message': 'Order created successfully'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
