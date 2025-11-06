from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count, Avg
from django.db import models
from django.utils import timezone
# Removed GIS import - using regular coordinates
from core.models import User, ChefProfile, MenuItem, Order, OrderItem, Review
from decimal import Decimal
import json


def chef_register(request):
    """Chef registration"""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        phone_number = request.POST.get('phone_number')
        bio = request.POST.get('bio')
        address = request.POST.get('address')
        lat = request.POST.get('lat')
        lng = request.POST.get('lng')
        
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
                    role='chef'
                )
                
                # Create chef profile
                ChefProfile.objects.create(
                    user=user,
                    bio=bio,
                    address=address,
                    latitude=float(lat) if lat else None,
                    longitude=float(lng) if lng else None,
                    is_available=False,  # Requires verification first
                    is_verified=False
                )
                
                login(request, user)
                messages.success(request, 'Chef account created successfully! Your account is pending verification.')
                return redirect('chef_portal:dashboard')
            except Exception as e:
                messages.error(request, f'Error creating account: {str(e)}')
    
    return render(request, 'chef_portal/auth/register.html')


def chef_login(request):
    """Chef login"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        if user is not None and user.role == 'chef':
            login(request, user)
            messages.success(request, 'Welcome back!')
            return redirect('chef_portal:dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'chef_portal/auth/login.html')


def chef_logout(request):
    """Chef logout"""
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('chef_portal:login')


@login_required
def chef_dashboard(request):
    """Chef dashboard with overview stats"""
    if request.user.role != 'chef':
        return redirect('client_portal:home')
    
    try:
        chef_profile = request.user.chef_profile
    except ChefProfile.DoesNotExist:
        messages.error(request, 'Chef profile not found.')
        return redirect('client_portal:home')
    
    # Get dashboard stats
    today = timezone.now().date()
    
    # Recent orders
    recent_orders = Order.objects.filter(
        chef_profile=chef_profile
    ).order_by('-created_at')[:10]
    
    # Pending orders (need chef action)
    pending_orders = Order.objects.filter(
        chef_profile=chef_profile,
        status__in=['placed']
    ).order_by('-created_at')
    
    # Today's stats
    today_orders = Order.objects.filter(
        chef_profile=chef_profile,
        created_at__date=today
    )
    
    today_revenue = today_orders.aggregate(
        revenue=Sum('total_amount')
    )['revenue'] or Decimal('0.00')

    stats = {
        'today_revenue': today_revenue,
        'orders_today': today_orders.count(),
        'pending_orders': pending_orders.count(),
        'menu_items_count': menu_items.count(),
        'available_items': available_items,
    }
    
    context = {
        'chef': chef_profile,
        'recent_orders': recent_orders,
        'pending_orders': pending_orders,
        'stats': stats,
        'recent_reviews': recent_reviews,
    }
    
    return render(request, 'chef_portal/dashboard.html', context)


@login_required
def chef_profile(request):
    """Chef profile management"""
    if request.user.role != 'chef':
        return redirect('client_portal:home')
    
    try:
        chef_profile = request.user.chef_profile
    except ChefProfile.DoesNotExist:
        messages.error(request, 'Chef profile not found.')
        return redirect('client_portal:home')
    
    if request.method == 'POST':
        # Update user info
        user = request.user
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.email = request.POST.get('email', '')
        user.phone_number = request.POST.get('phone_number', '')
        
        # Update chef profile
        chef_profile.bio = request.POST.get('bio', '')
        chef_profile.address = request.POST.get('address', '')
        chef_profile.instagram_url = request.POST.get('instagram_url', '')
        chef_profile.facebook_url = request.POST.get('facebook_url', '')
        chef_profile.tiktok_url = request.POST.get('tiktok_url', '')
        chef_profile.instagram_embed_code = request.POST.get('instagram_embed_code', '')
        chef_profile.delivery_radius_km = request.POST.get('delivery_radius_km', 5)
        chef_profile.minimum_order_amount = request.POST.get('minimum_order_amount', 0)
        
        try:
            user.save()
            chef_profile.save()
            messages.success(request, 'Profile updated successfully!')
        except Exception as e:
            messages.error(request, f'Error updating profile: {str(e)}')
        
        return redirect('chef_portal:profile')
    
    # Get additional context for the profile page
    total_orders = Order.objects.filter(chef_profile=chef_profile).count()
    
    # Available specialties (this would come from a model)
    available_specialties = [
        {'id': 1, 'name': 'Italian Cuisine'},
        {'id': 2, 'name': 'Asian Fusion'},
        {'id': 3, 'name': 'Mediterranean'},
        {'id': 4, 'name': 'Vegetarian'},
        {'id': 5, 'name': 'Desserts'},
        {'id': 6, 'name': 'Grilling & BBQ'},
    ]
    
    # Weekdays for availability settings
    weekdays = [
        {'name': 'Monday', 'code': 'mon', 'is_open': True, 'open_time': '09:00', 'close_time': '21:00'},
        {'name': 'Tuesday', 'code': 'tue', 'is_open': True, 'open_time': '09:00', 'close_time': '21:00'},
        {'name': 'Wednesday', 'code': 'wed', 'is_open': True, 'open_time': '09:00', 'close_time': '21:00'},
        {'name': 'Thursday', 'code': 'thu', 'is_open': True, 'open_time': '09:00', 'close_time': '21:00'},
        {'name': 'Friday', 'code': 'fri', 'is_open': True, 'open_time': '09:00', 'close_time': '22:00'},
        {'name': 'Saturday', 'code': 'sat', 'is_open': True, 'open_time': '10:00', 'close_time': '22:00'},
        {'name': 'Sunday', 'code': 'sun', 'is_open': False, 'open_time': '10:00', 'close_time': '20:00'},
    ]
    
    context = {
        'chef_profile': chef_profile, 
        'total_orders': total_orders,
        'available_specialties': available_specialties,
        'weekdays': weekdays,
    }
    return render(request, 'chef_portal/chef_profile.html', context)


@login_required
def menu_management(request):
    """Menu item management"""
    if request.user.role != 'chef':
        return redirect('client_portal:home')
    
    try:
        chef_profile = request.user.chef_profile
    except ChefProfile.DoesNotExist:
        messages.error(request, 'Chef profile not found.')
        return redirect('client_portal:home')
    
    menu_items = MenuItem.objects.filter(chef_profile=chef_profile).order_by('category', 'name')
    
    # Group by category
    menu_by_category = {}
    for item in menu_items:
        category = item.get_category_display()
        if category not in menu_by_category:
            menu_by_category[category] = []
        menu_by_category[category].append(item)
    
    context = {
        'chef_profile': chef_profile,
        'menu_by_category': menu_by_category,
        'total_items': menu_items.count(),
        'available_items': menu_items.filter(is_available=True).count(),
    }
    
    return render(request, 'chef_portal/menu_management.html', context)


@login_required
def order_management(request):
    """Order management and fulfillment"""
    if request.user.role != 'chef':
        return redirect('client_portal:home')
    
    try:
        chef_profile = request.user.chef_profile
    except ChefProfile.DoesNotExist:
        messages.error(request, 'Chef profile not found.')
        return redirect('client_portal:home')
    
    status_filter = request.GET.get('status', 'all')
    
    orders = Order.objects.filter(chef_profile=chef_profile)
    
    if status_filter != 'all':
        orders = orders.filter(status=status_filter)
    
    orders = orders.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(orders, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Status counts for filter tabs
    status_counts = {}
    all_orders = Order.objects.filter(chef_profile=chef_profile)
    for status, _ in Order.STATUS_CHOICES:
        status_counts[status] = all_orders.filter(status=status).count()
    
    # Calculate order statistics
    today = timezone.now().date()
    orders_stats = {
        'total_today': all_orders.filter(created_at__date=today).count(),
        'pending_count': status_counts.get('pending', 0),
        'revenue_today': all_orders.filter(created_at__date=today).aggregate(
            total=models.Sum('total_amount'))['total'] or 0,
        'avg_prep_time': 30  # This would be calculated from actual data
    }

    context = {
        'chef_profile': chef_profile,
        'orders': page_obj,
        'orders_stats': orders_stats,
        'current_status': status_filter,
        'status_counts': status_counts,
        'order_statuses': Order.STATUS_CHOICES,
        'today': today,
    }
    return render(request, 'chef_portal/order_management.html', context)


@login_required
def analytics(request):
    """Analytics and reporting dashboard"""
    if request.user.role != 'chef':
        return redirect('client_portal:home')
    
    try:
        chef_profile = request.user.chef_profile
    except ChefProfile.DoesNotExist:
        messages.error(request, 'Chef profile not found.')
        return redirect('client_portal:home')
    
    # Get orders for analytics
    orders = Order.objects.filter(chef_profile=chef_profile)
    today = timezone.now().date()
    
    # Basic analytics
    analytics = {
        'total_revenue': orders.aggregate(total=models.Sum('total_amount'))['total'] or 0,
        'total_orders': orders.count(),
        'new_customers': orders.values('user').distinct().count(),
        'average_rating': chef_profile.average_rating or 0,
        'revenue_change': 15.5,  # This would be calculated from previous period
        'orders_change': 8.2,
        'customers_change': 12.3,
        'rating_change': 0.1,
    }
    
    # Chart data (placeholder - would be calculated from actual data)
    chart_labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    revenue_data = [120, 190, 300, 500, 200, 300, 450]
    orders_data = [5, 8, 12, 20, 8, 12, 18]
    customers_data = [3, 5, 7, 12, 5, 8, 10]
    
    # Distribution data
    distribution_labels = ['Delivery', 'Pickup', 'Dine-in']
    distribution_data = [65, 25, 10]
    
    # Top selling items
    top_items = MenuItem.objects.filter(chef_profile=chef_profile).annotate(
        total_orders=models.Count('orderitem'),
        total_revenue=models.Sum('orderitem__quantity') * models.F('price')
    ).order_by('-total_orders')[:5]
    
    # Peak hours (placeholder data)
    peak_hours = [
        {'hour': 12, 'period_name': 'Lunch Rush', 'order_count': 15, 'percentage': 25},
        {'hour': 19, 'period_name': 'Dinner Peak', 'order_count': 22, 'percentage': 37},
        {'hour': 18, 'period_name': 'Evening', 'order_count': 12, 'percentage': 20},
    ]
    
    # Business insights
    insights = {
        'peak_day': 'Saturday',
        'peak_orders': 25,
        'top_category': 'Main Courses',
        'category_percentage': 60,
        'retention_rate': 75,
        'peak_hour': '7 PM',
    }
    
    context = {
        'chef_profile': chef_profile,
        'analytics': analytics,
        'chart_labels': chart_labels,
        'revenue_data': revenue_data,
        'orders_data': orders_data,
        'customers_data': customers_data,
        'distribution_labels': distribution_labels,
        'distribution_data': distribution_data,
        'top_items': top_items,
        'peak_hours': peak_hours,
        'insights': insights,
        'today': today,
    }
    return render(request, 'chef_portal/analytics.html', context)


# AJAX Views for the new templates
@login_required
@csrf_exempt
def ajax_save_menu_item(request):
    """AJAX endpoint to save (create/update) menu items"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'})
    
    try:
        chef_profile = request.user.chef_profile
        item_id = request.POST.get('item_id')
        
        # Create or update menu item
        if item_id:
            menu_item = get_object_or_404(MenuItem, id=item_id, chef_profile=chef_profile)
        else:
            menu_item = MenuItem(chef_profile=chef_profile)
        
        menu_item.name = request.POST.get('name')
        menu_item.description = request.POST.get('description')
        menu_item.price = request.POST.get('price')
        menu_item.category = request.POST.get('category')
        menu_item.is_vegetarian = request.POST.get('is_vegetarian') == 'on'
        menu_item.is_vegan = request.POST.get('is_vegan') == 'on'
        menu_item.is_gluten_free = request.POST.get('is_gluten_free') == 'on'
        menu_item.is_spicy = request.POST.get('is_spicy') == 'on'
        menu_item.is_available = request.POST.get('is_available') == 'on'
        
        if 'image' in request.FILES:
            menu_item.image = request.FILES['image']
        
        menu_item.save()
        
        return JsonResponse({'success': True, 'message': 'Menu item saved successfully'})
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@csrf_exempt
def ajax_toggle_menu_item(request):
    """AJAX endpoint to toggle menu item availability"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'})
    
    try:
        data = json.loads(request.body)
        chef_profile = request.user.chef_profile
        item_id = data.get('item_id')
        is_available = data.get('is_available')
        
        menu_item = get_object_or_404(MenuItem, id=item_id, chef_profile=chef_profile)
        menu_item.is_available = is_available
        menu_item.save()
        
        return JsonResponse({'success': True, 'message': 'Item status updated'})
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@csrf_exempt
def ajax_delete_menu_item(request):
    """AJAX endpoint to delete menu items"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'})
    
    try:
        data = json.loads(request.body)
        chef_profile = request.user.chef_profile
        item_id = data.get('item_id')
        
        menu_item = get_object_or_404(MenuItem, id=item_id, chef_profile=chef_profile)
        menu_item.delete()
        
        return JsonResponse({'success': True, 'message': 'Item deleted successfully'})
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@csrf_exempt
def ajax_update_profile(request):
    """AJAX endpoint to update chef profile"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'})
    
    try:
        user = request.user
        chef_profile = user.chef_profile
        
        # Update user fields
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.email = request.POST.get('email', '')
        
        # Update chef profile fields
        chef_profile.phone_number = request.POST.get('phone', '')
        chef_profile.bio = request.POST.get('bio', '')
        chef_profile.business_name = request.POST.get('business_name', '')
        chef_profile.cuisine_type = request.POST.get('cuisine_type', '')
        chef_profile.address = request.POST.get('address', '')
        chef_profile.delivery_radius_km = request.POST.get('delivery_radius', 5)
        chef_profile.minimum_order_amount = request.POST.get('min_order', 0)
        chef_profile.business_description = request.POST.get('business_description', '')
        chef_profile.average_prep_time = request.POST.get('prep_time', 30)
        chef_profile.advance_booking_hours = request.POST.get('advance_booking', 2)
        chef_profile.accepts_orders = request.POST.get('accepts_orders') == 'on'
        
        # Social media links
        chef_profile.website = request.POST.get('website', '')
        chef_profile.facebook_url = request.POST.get('facebook_url', '')
        chef_profile.instagram_url = request.POST.get('instagram_url', '')
        chef_profile.twitter_url = request.POST.get('twitter_url', '')
        chef_profile.linkedin_url = request.POST.get('linkedin_url', '')
        
        # Handle profile picture upload
        if 'profile_picture' in request.FILES:
            chef_profile.profile_picture = request.FILES['profile_picture']
        
        user.save()
        chef_profile.save()
        
        return JsonResponse({'success': True, 'message': 'Profile updated successfully'})
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@csrf_exempt
def ajax_analytics_data(request):
    """AJAX endpoint to fetch analytics data for different periods"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'})
    
    try:
        data = json.loads(request.body)
        period = data.get('period', 'today')
        chef_profile = request.user.chef_profile
        
        # This would contain complex analytics calculations
        # For now, returning placeholder data
        
        analytics = {
            'total_revenue': 1250.00,
            'total_orders': 45,
            'new_customers': 12,
            'average_rating': 4.5,
            'revenue_change': 15.5,
            'orders_change': 8.2,
            'customers_change': 12.3,
            'rating_change': 0.1,
        }
        
        chart_data = {
            'labels': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
            'revenue_data': [120, 190, 300, 500, 200, 300, 450],
            'orders_data': [5, 8, 12, 20, 8, 12, 18],
            'customers_data': [3, 5, 7, 12, 5, 8, 10],
            'distribution_data': [65, 25, 10]
        }
        
        insights = {
            'peak_day': 'Saturday',
            'peak_orders': 25,
            'top_category': 'Main Courses',
            'category_percentage': 60,
            'retention_rate': 75,
            'peak_hour': '7 PM',
        }
        
        return JsonResponse({
            'success': True,
            'analytics': analytics,
            'chart_data': chart_data,
            'insights': insights
        })
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def order_detail(request, order_id):
    """Order detail view"""
    chef_profile = request.user.chef_profile
    order = get_object_or_404(Order, id=order_id, chef_profile=chef_profile)
    
    context = {
        'order': order,
        'chef_profile': chef_profile,
    }
    return render(request, 'chef_portal/order_detail.html', context)


@login_required
def print_order(request, order_id):
    """Print-friendly order view"""
    chef_profile = request.user.chef_profile
    order = get_object_or_404(Order, id=order_id, chef_profile=chef_profile)
    
    context = {
        'order': order,
        'chef_profile': chef_profile,
    }
    return render(request, 'chef_portal/print_order.html', context)


@login_required
def export_analytics(request):
    """Export analytics report"""
    format_type = request.GET.get('format', 'pdf')
    period = request.GET.get('period', 'month')
    
    # This would generate actual export files
    # For now, returning a simple response
    
    return JsonResponse({
        'success': True,
        'message': f'Export feature coming soon for {format_type} format'
    })


@login_required
def payouts(request):
    """Payout management and history"""
    if request.user.role != 'chef':
        return redirect('client_portal:home')
    
    try:
        chef_profile = request.user.chef_profile
    except ChefProfile.DoesNotExist:
        messages.error(request, 'Chef profile not found.')
        return redirect('client_portal:home')
    
    # Payout logic would be implemented here
    # This would integrate with Stripe Connect
    
    context = {
        'chef_profile': chef_profile,
    }
    return render(request, 'chef_portal/payouts.html', context)


# AJAX Views
@login_required
@require_http_methods(["POST"])
def toggle_availability_ajax(request):
    """Toggle chef availability status"""
    if request.user.role != 'chef':
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    try:
        chef_profile = request.user.chef_profile
        data = json.loads(request.body)
        is_available = data.get('is_available', False)
        
        chef_profile.is_available = is_available
        chef_profile.save()
        
        status = "online" if is_available else "offline"
        return JsonResponse({
            'success': True,
            'message': f'Status updated to {status}',
            'is_available': is_available
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def update_order_status_ajax(request):
    """Update order status"""
    if request.user.role != 'chef':
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    try:
        data = json.loads(request.body)
        order_id = data.get('order_id')
        new_status = data.get('status')
        
        order = get_object_or_404(Order, id=order_id, chef_profile__user=request.user)
        
        # Validate status transition
        valid_statuses = ['confirmed', 'in_progress', 'ready', 'out_for_delivery', 'delivered', 'rejected']
        if new_status not in valid_statuses:
            return JsonResponse({'success': False, 'error': 'Invalid status'}, status=400)
        
        order.status = new_status
        if new_status == 'confirmed':
            order.confirmed_at = timezone.now()
        elif new_status == 'delivered':
            order.completed_at = timezone.now()
        
        order.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Order status updated to {new_status}',
            'status': new_status
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def create_menu_item_ajax(request):
    """Create new menu item"""
    if request.user.role != 'chef':
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    try:
        chef_profile = request.user.chef_profile
        data = json.loads(request.body)
        
        menu_item = MenuItem.objects.create(
            chef_profile=chef_profile,
            name=data.get('name'),
            description=data.get('description'),
            price=Decimal(data.get('price')),
            category=data.get('category'),
            ingredients=data.get('ingredients', []),
            allergens=data.get('allergens', []),
            is_vegetarian=data.get('is_vegetarian', False),
            is_vegan=data.get('is_vegan', False),
            is_gluten_free=data.get('is_gluten_free', False),
            customization_options=data.get('customization_options', {}),
            preparation_time_minutes=data.get('preparation_time_minutes', 30)
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Menu item created successfully',
            'item': {
                'id': str(menu_item.id),
                'name': menu_item.name,
                'price': str(menu_item.price),
                'category': menu_item.get_category_display(),
                'is_available': menu_item.is_available
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def update_menu_item_ajax(request, item_id):
    """Update menu item"""
    if request.user.role != 'chef':
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    try:
        menu_item = get_object_or_404(MenuItem, id=item_id, chef_profile__user=request.user)
        data = json.loads(request.body)
        
        menu_item.name = data.get('name', menu_item.name)
        menu_item.description = data.get('description', menu_item.description)
        menu_item.price = Decimal(data.get('price', menu_item.price))
        menu_item.category = data.get('category', menu_item.category)
        menu_item.ingredients = data.get('ingredients', menu_item.ingredients)
        menu_item.allergens = data.get('allergens', menu_item.allergens)
        menu_item.is_vegetarian = data.get('is_vegetarian', menu_item.is_vegetarian)
        menu_item.is_vegan = data.get('is_vegan', menu_item.is_vegan)
        menu_item.is_gluten_free = data.get('is_gluten_free', menu_item.is_gluten_free)
        menu_item.customization_options = data.get('customization_options', menu_item.customization_options)
        menu_item.preparation_time_minutes = data.get('preparation_time_minutes', menu_item.preparation_time_minutes)
        
        menu_item.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Menu item updated successfully'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(["DELETE"])
def delete_menu_item_ajax(request, item_id):
    """Delete menu item"""
    if request.user.role != 'chef':
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    try:
        menu_item = get_object_or_404(MenuItem, id=item_id, chef_profile__user=request.user)
        menu_item.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Menu item deleted successfully'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def toggle_menu_item_ajax(request, item_id):
    """Toggle menu item availability"""
    if request.user.role != 'chef':
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    try:
        menu_item = get_object_or_404(MenuItem, id=item_id, chef_profile__user=request.user)
        menu_item.is_available = not menu_item.is_available
        menu_item.save()
        
        status = "available" if menu_item.is_available else "unavailable"
        
        return JsonResponse({
            'success': True,
            'status': status,
            'is_available': menu_item.is_available
        })
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
def menu_items(request):
    """Menu items management page"""
    if request.user.role != 'chef':
        return redirect('client_portal:home')
    
    try:
        chef_profile = request.user.chef_profile
    except ChefProfile.DoesNotExist:
        messages.error(request, 'Chef profile not found.')
        return redirect('client_portal:home')
    
    # Get all menu items for this chef
    menu_items = MenuItem.objects.filter(chef_profile=chef_profile).order_by('category', 'name')
    
    # Group by category
    menu_by_category = {}
    for item in menu_items:
        category = item.get_category_display()
        if category not in menu_by_category:
            menu_by_category[category] = []
        menu_by_category[category].append(item)
    
    context = {
        'chef': chef_profile,
        'menu_items': menu_items,
        'menu_by_category': menu_by_category,
    }
    
    return render(request, 'chef_portal/menu_items.html', context)


@login_required 
@require_http_methods(["POST"])
def toggle_availability(request):
    """Toggle chef availability status"""
    if request.user.role != 'chef':
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    try:
        chef_profile = request.user.chef_profile
        chef_profile.is_available = not chef_profile.is_available
        chef_profile.save()
        
        return JsonResponse({
            'success': True,
            'available': chef_profile.is_available
        })
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def toggle_item_status(request):
    """Toggle menu item availability status"""
    if request.user.role != 'chef':
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    try:
        data = json.loads(request.body)
        item_id = data.get('item_id')
        is_available = data.get('is_available')
        
        menu_item = get_object_or_404(MenuItem, id=item_id, chef_profile__user=request.user)
        menu_item.is_available = is_available
        menu_item.save()
        
        return JsonResponse({'success': True})
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def update_order_status(request):
    """Update order status"""
    if request.user.role != 'chef':
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    try:
        data = json.loads(request.body)
        order_id = data.get('order_id')
        status = data.get('status')
        
        order = get_object_or_404(Order, id=order_id, chef_profile__user=request.user)
        order.status = status
        if status == 'confirmed':
            order.confirmed_at = timezone.now()
        elif status in ['delivered', 'cancelled']:
            order.completed_at = timezone.now()
        order.save()
        
        return JsonResponse({'success': True})
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
        return JsonResponse({
            'success': True,
            'message': f'Menu item marked as {status}',
            'is_available': menu_item.is_available
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
