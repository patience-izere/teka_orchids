from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User, ChefProfile, MenuItem, Order, OrderItem, 
    Review, ChefAvailabilitySchedule, ChefUnavailableDate
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_staff', 'date_joined')
    list_filter = ('role', 'is_staff', 'is_superuser', 'is_active', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Role Information', {'fields': ('role', 'phone_number')}),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Role Information', {'fields': ('role', 'phone_number')}),
    )


class MenuItemInline(admin.TabularInline):
    model = MenuItem
    extra = 0
    readonly_fields = ('created_at', 'updated_at')
    fields = ('name', 'category', 'price', 'is_available', 'preparation_time_minutes')


class ChefAvailabilityScheduleInline(admin.TabularInline):
    model = ChefAvailabilitySchedule
    extra = 0


@admin.register(ChefProfile)
class ChefProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_available', 'is_verified', 'average_rating', 'total_reviews', 'created_at')
    list_filter = ('is_available', 'is_verified', 'created_at')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name', 'address')
    readonly_fields = ('average_rating', 'total_reviews', 'created_at', 'updated_at')
    inlines = [MenuItemInline, ChefAvailabilityScheduleInline]
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'is_verified')
        }),
        ('Profile Details', {
            'fields': ('bio', 'profile_picture', 'header_image')
        }),
        ('Location', {
            'fields': ('address', 'latitude', 'longitude', 'delivery_radius_km')
        }),
        ('Social Media', {
            'fields': ('instagram_url', 'facebook_url', 'tiktok_url', 'instagram_embed_code'),
            'classes': ('collapse',)
        }),
        ('Business Settings', {
            'fields': ('is_available', 'minimum_order_amount')
        }),
        ('Ratings & Payment', {
            'fields': ('average_rating', 'total_reviews', 'stripe_account_id', 'stripe_connected'),
            'classes': ('collapse',)
        }),
        ('Verification', {
            'fields': ('verification_documents',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'chef_profile', 'category', 'price', 'is_available', 'is_vegetarian', 'is_vegan')
    list_filter = ('category', 'is_available', 'is_vegetarian', 'is_vegan', 'is_gluten_free', 'created_at')
    search_fields = ('name', 'description', 'chef_profile__user__username')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('chef_profile', 'name', 'description', 'category', 'price', 'image')
        }),
        ('Dietary Information', {
            'fields': ('ingredients', 'allergens', 'is_vegetarian', 'is_vegan', 'is_gluten_free')
        }),
        ('Availability & Customization', {
            'fields': ('is_available', 'preparation_time_minutes', 'customization_options')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('total_price',)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'client', 'chef_profile', 'status', 'total_amount', 'payment_status', 'created_at')
    list_filter = ('status', 'payment_status', 'created_at', 'chef_profile')
    search_fields = ('id', 'client__username', 'chef_profile__user__username', 'delivery_address')
    readonly_fields = ('created_at', 'confirmed_at', 'completed_at')
    inlines = [OrderItemInline]
    
    fieldsets = (
        ('Order Information', {
            'fields': ('client', 'chef_profile', 'status')
        }),
        ('Financial Details', {
            'fields': ('subtotal', 'delivery_fee', 'platform_fee', 'total_amount', 'payment_status', 'stripe_payment_intent')
        }),
        ('Delivery Information', {
            'fields': ('delivery_address', 'delivery_instructions', 'estimated_delivery_time')
        }),
        ('Payment Information', {
            'fields': ('stripe_payment_intent_id',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'confirmed_at', 'completed_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'menu_item', 'quantity', 'unit_price', 'total_price')
    list_filter = ('menu_item__category',)
    search_fields = ('order__id', 'menu_item__name')
    readonly_fields = ('total_price',)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('client', 'chef_profile', 'rating', 'is_approved', 'is_flagged', 'created_at')
    list_filter = ('rating', 'is_approved', 'is_flagged', 'created_at')
    search_fields = ('client__username', 'chef_profile__user__username', 'comment')
    readonly_fields = ('created_at',)
    
    actions = ['approve_reviews', 'flag_reviews', 'unflag_reviews']
    
    def approve_reviews(self, request, queryset):
        queryset.update(is_approved=True, is_flagged=False)
        self.message_user(request, f"{queryset.count()} reviews approved.")
    
    def flag_reviews(self, request, queryset):
        queryset.update(is_flagged=True)
        self.message_user(request, f"{queryset.count()} reviews flagged.")
    
    def unflag_reviews(self, request, queryset):
        queryset.update(is_flagged=False)
        self.message_user(request, f"{queryset.count()} reviews unflagged.")
    
    approve_reviews.short_description = "Approve selected reviews"
    flag_reviews.short_description = "Flag selected reviews"
    unflag_reviews.short_description = "Remove flag from selected reviews"


@admin.register(ChefAvailabilitySchedule)
class ChefAvailabilityScheduleAdmin(admin.ModelAdmin):
    list_display = ('chef_profile', 'get_weekday_display', 'start_time', 'end_time', 'is_active')
    list_filter = ('weekday', 'is_active')
    search_fields = ('chef_profile__user__username',)


@admin.register(ChefUnavailableDate)
class ChefUnavailableDateAdmin(admin.ModelAdmin):
    list_display = ('chef_profile', 'date', 'reason')
    list_filter = ('date',)
    search_fields = ('chef_profile__user__username', 'reason')
