from django.urls import path
from . import views

app_name = 'chef_portal'

urlpatterns = [
    # Chef authentication
    path('register/', views.chef_register, name='register'),
    path('login/', views.chef_login, name='login'),
    path('logout/', views.chef_logout, name='logout'),
    
    # Chef dashboard and management
    path('dashboard/', views.chef_dashboard, name='dashboard'),
    path('profile/', views.chef_profile, name='profile'),
    path('menu/', views.menu_items, name='menu'),
    path('menu-management/', views.menu_management, name='menu_management'),
    path('orders/', views.order_management, name='orders'),
    path('analytics/', views.analytics, name='analytics'),
    path('payouts/', views.payouts, name='payouts'),
    
    # AJAX endpoints for dynamic functionality
    path('ajax/toggle-availability/', views.toggle_availability, name='ajax_toggle_availability'),
    path('ajax/update-order-status/', views.update_order_status, name='ajax_update_order_status'),
    path('ajax/menu-item/save/', views.ajax_save_menu_item, name='ajax_save_menu_item'),
    path('ajax/menu-item/toggle/', views.ajax_toggle_menu_item, name='ajax_toggle_menu_item'),
    path('ajax/menu-item/delete/', views.ajax_delete_menu_item, name='ajax_delete_menu_item'),
    path('ajax/profile/update/', views.ajax_update_profile, name='ajax_update_profile'),
    path('ajax/analytics-data/', views.ajax_analytics_data, name='ajax_analytics_data'),
    path('order/<uuid:order_id>/detail/', views.order_detail, name='order_detail'),
    path('order/<uuid:order_id>/print/', views.print_order, name='print_order'),
    path('export/analytics/', views.export_analytics, name='export_analytics'),
]