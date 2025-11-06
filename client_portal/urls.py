from django.urls import path
from . import views

app_name = 'client_portal'

urlpatterns = [
    # Public pages (no authentication required)
    path('', views.home, name='home'),
    path('chefs/', views.chef_list, name='chef_list'),
    path('chef/<int:chef_id>/', views.chef_detail, name='chef_detail'),
    path('search/', views.search_chefs, name='search_chefs'),
    
    # Authentication
    path('auth/login/', views.login_view, name='login'),
    path('auth/register/', views.register_view, name='register'),
    path('auth/logout/', views.logout_view, name='logout'),
    
    # Authenticated client pages
    path('dashboard/', views.client_dashboard, name='dashboard'),
    path('orders/', views.order_history, name='order_history'),
    path('order/<uuid:order_id>/', views.order_detail, name='order_detail'),
    path('profile/', views.profile_settings, name='profile_settings'),
    
    # Cart and ordering
    path('cart/', views.cart_view, name='cart'),
    # Checkout: allow both routes (with and without order_id) to use the same name so reverse() with kwargs works
    path('checkout/<uuid:order_id>/', views.checkout, name='checkout'),
    path('checkout/', views.checkout, name='checkout'),
    path('create-order/', views.create_order, name='create_order'),
    path('add-to-cart/', views.add_to_cart, name='add_to_cart'),
    path('remove-from-cart/', views.remove_from_cart, name='remove_from_cart'),
    path('update-cart-item/', views.update_cart_item, name='update_cart_item'),
    path('validate-cart/', views.validate_cart, name='validate_cart'),
    
    # AJAX endpoints for dynamic functionality
    path('ajax/chef-menu/<int:chef_id>/', views.get_chef_menu_ajax, name='ajax_chef_menu'),
    path('ajax/submit-review/', views.submit_review_ajax, name='ajax_submit_review'),
]