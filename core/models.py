from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
import uuid


class User(AbstractUser):
    """
    Custom User model extending AbstractUser to support role-based authentication
    """
    ROLE_CHOICES = [
        ('client', 'Client'),
        ('chef', 'Chef'),
        ('admin', 'Admin'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='client')
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


class ChefProfile(models.Model):
    """
    Chef profile model containing all chef-specific information
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='chef_profile')
    bio = models.TextField(help_text="Chef's personal story and background")
    profile_picture = models.ImageField(upload_to='chef_profiles/', blank=True, null=True)
    header_image = models.ImageField(upload_to='chef_headers/', blank=True, null=True)
    
    # Location data for geospatial queries (using lat/lng for development)
    latitude = models.FloatField(help_text="Chef's latitude coordinate")
    longitude = models.FloatField(help_text="Chef's longitude coordinate")
    address = models.CharField(max_length=255)
    
    # Social media integration
    instagram_url = models.URLField(blank=True, null=True)
    facebook_url = models.URLField(blank=True, null=True)
    tiktok_url = models.URLField(blank=True, null=True)
    instagram_embed_code = models.TextField(
        blank=True, 
        null=True,
        help_text="Instagram embed iframe code for profile integration"
    )
    
    # Business settings
    is_available = models.BooleanField(default=True, help_text="Currently accepting orders")
    delivery_radius_km = models.PositiveIntegerField(default=5, help_text="Delivery radius in kilometers")
    minimum_order_amount = models.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Minimum order amount required"
    )
    
    # Ratings and reviews
    average_rating = models.DecimalField(
        max_digits=3, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    total_reviews = models.PositiveIntegerField(default=0)
    
    # Stripe Connect for payouts
    stripe_account_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_connected = models.BooleanField(default=False)
    
    # Verification status
    is_verified = models.BooleanField(default=False)
    verification_documents = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Chef: {self.user.get_full_name() or self.user.username}"
    
    class Meta:
        indexes = [
            models.Index(fields=['is_available']),
            models.Index(fields=['is_verified']),
        ]


class MenuItem(models.Model):
    """
    Individual menu items that chefs offer
    """
    CATEGORY_CHOICES = [
        ('appetizer', 'Appetizer'),
        ('main_course', 'Main Course'),
        ('dessert', 'Dessert'),
        ('beverage', 'Beverage'),
        ('side_dish', 'Side Dish'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    chef_profile = models.ForeignKey(ChefProfile, on_delete=models.CASCADE, related_name='menu_items')
    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(
        max_digits=8, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='main_course')
    image = models.ImageField(upload_to='menu_items/', blank=True, null=True)
    
    # Dietary information
    ingredients = models.JSONField(default=list, help_text="List of ingredients")
    allergens = models.JSONField(default=list, help_text="List of potential allergens")
    is_vegetarian = models.BooleanField(default=False)
    is_vegan = models.BooleanField(default=False)
    is_gluten_free = models.BooleanField(default=False)
    
    # Customization options
    customization_options = models.JSONField(
        default=dict, 
        blank=True,
        help_text="Available customizations (e.g., spice levels, protein choices)"
    )
    
    # Availability
    is_available = models.BooleanField(default=True)
    preparation_time_minutes = models.PositiveIntegerField(default=30)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} - {self.chef_profile.user.username}"
    
    class Meta:
        indexes = [
            models.Index(fields=['chef_profile', 'is_available']),
            models.Index(fields=['category']),
        ]


class Order(models.Model):
    """
    Order model representing a complete order from a client to a chef
    """
    STATUS_CHOICES = [
        ('placed', 'Order Placed'),
        ('confirmed', 'Confirmed by Chef'),
        ('in_progress', 'In the Kitchen'),
        ('ready', 'Ready for Pickup/Delivery'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('rejected', 'Rejected by Chef'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    chef_profile = models.ForeignKey(ChefProfile, on_delete=models.CASCADE, related_name='received_orders')
    
    # Order details
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='placed')
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_fee = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    platform_fee = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Delivery information
    delivery_address = models.TextField()
    delivery_instructions = models.TextField(blank=True)
    estimated_delivery_time = models.DateTimeField(null=True, blank=True)
    
    # Payment information
    stripe_payment_intent = models.CharField(max_length=255, blank=True, null=True)
    payment_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('paid', 'Paid'), 
            ('failed', 'Failed'),
            ('refunded', 'Refunded'),
        ],
        default='pending'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Order #{str(self.id)[:8]} - {self.client.username} from {self.chef_profile.user.username}"
    
    @property
    def user(self):
        """Compatibility alias for templates that expect order.user"""
        return self.client
    
    class Meta:
        indexes = [
            models.Index(fields=['client', 'status']),
            models.Index(fields=['chef_profile', 'status']),
            models.Index(fields=['created_at']),
        ]


class OrderItem(models.Model):
    """
    Individual items within an order
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)
    customizations = models.JSONField(default=dict, blank=True)
    
    def __init__(self, *args, **kwargs):
        # Compatibility: allow creating OrderItem with 'price' and 'subtotal' kwars (tests/legacy code)
        if 'price' in kwargs:
            kwargs['unit_price'] = kwargs.pop('price')
        # 'subtotal' is not stored on the model; ignore it if provided
        if 'subtotal' in kwargs:
            kwargs.pop('subtotal')
        super().__init__(*args, **kwargs)
    
    @property
    def total_price(self):
        return self.unit_price * self.quantity
    
    def __str__(self):
        return f"{self.quantity}x {self.menu_item.name}"


class Review(models.Model):
    """
    Review and rating system for orders
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='review')
    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews_given')
    chef_profile = models.ForeignKey(ChefProfile, on_delete=models.CASCADE, related_name='reviews_received')
    
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating from 1 to 5 stars"
    )
    comment = models.TextField(blank=True)
    
    # Moderation
    is_approved = models.BooleanField(default=True)
    is_flagged = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.rating}★ review by {self.client.username} for {self.chef_profile.user.username}"
    
    class Meta:
        indexes = [
            models.Index(fields=['chef_profile', 'is_approved']),
            models.Index(fields=['rating']),
        ]


class ChefAvailabilitySchedule(models.Model):
    """
    Chef's weekly availability schedule
    """
    WEEKDAY_CHOICES = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]
    
    chef_profile = models.ForeignKey(ChefProfile, on_delete=models.CASCADE, related_name='availability_schedule')
    weekday = models.IntegerField(choices=WEEKDAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['chef_profile', 'weekday', 'start_time']
        indexes = [
            models.Index(fields=['chef_profile', 'weekday', 'is_active']),
        ]


class ChefUnavailableDate(models.Model):
    """
    Specific dates when a chef is unavailable (vacations, holidays, etc.)
    """
    chef_profile = models.ForeignKey(ChefProfile, on_delete=models.CASCADE, related_name='unavailable_dates')
    date = models.DateField()
    reason = models.CharField(max_length=255, blank=True)
    
    class Meta:
        unique_together = ['chef_profile', 'date']
