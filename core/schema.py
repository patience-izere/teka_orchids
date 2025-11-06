import graphene
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
from django.contrib.auth import authenticate, login, logout
import math
from django.utils import timezone
from django.db import models
from decimal import Decimal
import stripe
from django.conf import settings

from .models import (
    User, ChefProfile, MenuItem, Order, OrderItem, Review,
    ChefAvailabilitySchedule, ChefUnavailableDate
)

stripe.api_key = settings.STRIPE_SECRET_KEY


# GraphQL Types
class UserType(DjangoObjectType):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'role', 'phone_number', 'date_joined')


class ChefProfileType(DjangoObjectType):
    class Meta:
        model = ChefProfile
        fields = '__all__'
    
    distance_km = graphene.Float()
    
    def resolve_distance_km(self, info):
        # This will be set by the resolver when calculating distance
        return getattr(self, '_distance_km', None)


class MenuItemType(DjangoObjectType):
    class Meta:
        model = MenuItem
        fields = '__all__'


class OrderType(DjangoObjectType):
    class Meta:
        model = Order
        fields = '__all__'


class OrderItemType(DjangoObjectType):
    class Meta:
        model = OrderItem
        fields = '__all__'
    
    total_price = graphene.Decimal()
    
    def resolve_total_price(self, info):
        return self.total_price


class ReviewType(DjangoObjectType):
    class Meta:
        model = Review
        fields = '__all__'


class ChefAvailabilityScheduleType(DjangoObjectType):
    class Meta:
        model = ChefAvailabilitySchedule
        fields = '__all__'


# Input Types
class OrderItemInput(graphene.InputObjectType):
    menu_item_id = graphene.ID(required=True)
    quantity = graphene.Int(required=True)
    customizations = graphene.JSONString()


class MenuItemInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    description = graphene.String(required=True)
    price = graphene.Decimal(required=True)
    category = graphene.String(required=True)
    ingredients = graphene.List(graphene.String)
    allergens = graphene.List(graphene.String)
    is_vegetarian = graphene.Boolean()
    is_vegan = graphene.Boolean()
    is_gluten_free = graphene.Boolean()
    customization_options = graphene.JSONString()
    preparation_time_minutes = graphene.Int()


# Authentication Types
class AuthPayload(graphene.ObjectType):
    user = graphene.Field(UserType)
    success = graphene.Boolean()
    message = graphene.String()


# Queries
class Query(graphene.ObjectType):
    # Chef discovery
    chefs_near_me = graphene.List(
        ChefProfileType,
        lat=graphene.Float(required=True),
        long=graphene.Float(required=True),
        radius=graphene.Int(default_value=10)
    )
    
    # Individual chef profile
    chef_profile = graphene.Field(ChefProfileType, id=graphene.ID(required=True))
    
    # Menu for specific chef
    menu_for_chef = graphene.List(MenuItemType, chef_id=graphene.ID(required=True))
    
    # Client orders
    my_orders = graphene.List(OrderType)
    
    # Chef orders
    chef_orders = graphene.List(OrderType, status=graphene.String())
    
    # Current user
    me = graphene.Field(UserType)
    
    # Search functionality
    search_chefs = graphene.List(
        ChefProfileType,
        query=graphene.String(),
        cuisine_type=graphene.String(),
        dietary_filter=graphene.String()
    )
    
    def resolve_chefs_near_me(self, info, lat, long, radius):
        """Find chefs within specified radius of given coordinates"""
        def calculate_distance(lat1, lon1, lat2, lon2):
            """Calculate distance between two coordinates in kilometers"""
            R = 6371  # Earth's radius in kilometers
            lat1_rad = math.radians(lat1)
            lat2_rad = math.radians(lat2)
            delta_lat = math.radians(lat2 - lat1)
            delta_lon = math.radians(lon2 - lon1)
            
            a = (math.sin(delta_lat/2) * math.sin(delta_lat/2) +
                 math.cos(lat1_rad) * math.cos(lat2_rad) *
                 math.sin(delta_lon/2) * math.sin(delta_lon/2))
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
            
            return R * c
        
        # Get all available chefs
        all_chefs = ChefProfile.objects.filter(
            is_available=True,
            is_verified=True,
            latitude__isnull=False,
            longitude__isnull=False
        )
        
        # Filter by distance
        nearby_chefs = []
        for chef in all_chefs:
            distance = calculate_distance(lat, long, chef.latitude, chef.longitude)
            if distance <= radius:
                chef._distance_km = round(distance, 2)
                nearby_chefs.append(chef)
        
        # Sort by distance
        nearby_chefs.sort(key=lambda x: x._distance_km)
        
        return nearby_chefs
    
    def resolve_chef_profile(self, info, id):
        try:
            return ChefProfile.objects.get(id=id, is_verified=True)
        except ChefProfile.DoesNotExist:
            return None
    
    def resolve_menu_for_chef(self, info, chef_id):
        return MenuItem.objects.filter(chef_profile_id=chef_id, is_available=True)
    
    def resolve_my_orders(self, info):
        if not info.context.user.is_authenticated:
            return []
        return Order.objects.filter(client=info.context.user).order_by('-created_at')
    
    def resolve_chef_orders(self, info, status=None):
        user = info.context.user
        if not user.is_authenticated or user.role != 'chef':
            return []
        
        try:
            chef_profile = user.chef_profile
            orders = Order.objects.filter(chef_profile=chef_profile)
            if status:
                orders = orders.filter(status=status)
            return orders.order_by('-created_at')
        except ChefProfile.DoesNotExist:
            return []
    
    def resolve_me(self, info):
        if info.context.user.is_authenticated:
            return info.context.user
        return None
    
    def resolve_search_chefs(self, info, query=None, cuisine_type=None, dietary_filter=None):
        chefs = ChefProfile.objects.filter(is_available=True, is_verified=True)
        
        if query:
            chefs = chefs.filter(
                models.Q(user__first_name__icontains=query) |
                models.Q(user__last_name__icontains=query) |
                models.Q(bio__icontains=query)
            )
        
        # Additional filtering can be implemented based on menu items
        return chefs


# Mutations
class RegisterClient(graphene.Mutation):
    class Arguments:
        username = graphene.String(required=True)
        email = graphene.String(required=True)
        password = graphene.String(required=True)
        first_name = graphene.String()
        last_name = graphene.String()
        phone_number = graphene.String()
    
    Output = AuthPayload
    
    def mutate(self, info, username, email, password, first_name=None, last_name=None, phone_number=None):
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name or '',
                last_name=last_name or '',
                phone_number=phone_number,
                role='client'
            )
            return AuthPayload(user=user, success=True, message="Account created successfully")
        except Exception as e:
            return AuthPayload(user=None, success=False, message=str(e))


class RegisterChef(graphene.Mutation):
    class Arguments:
        username = graphene.String(required=True)
        email = graphene.String(required=True)
        password = graphene.String(required=True)
        first_name = graphene.String()
        last_name = graphene.String()
        phone_number = graphene.String()
        bio = graphene.String(required=True)
        address = graphene.String(required=True)
        lat = graphene.Float(required=True)
        long = graphene.Float(required=True)
    
    Output = AuthPayload
    
    def mutate(self, info, username, email, password, bio, address, lat, long, 
               first_name=None, last_name=None, phone_number=None):
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name or '',
                last_name=last_name or '',
                phone_number=phone_number,
                role='chef'
            )
            
            # Create chef profile
            ChefProfile.objects.create(
                user=user,
                bio=bio,
                address=address,
                latitude=lat,
                longitude=long,
                is_available=False,  # Requires verification first
                is_verified=False
            )
            
            return AuthPayload(user=user, success=True, message="Chef account created successfully. Awaiting verification.")
        except Exception as e:
            return AuthPayload(user=None, success=False, message=str(e))


class LoginUser(graphene.Mutation):
    class Arguments:
        username = graphene.String(required=True)
        password = graphene.String(required=True)
    
    Output = AuthPayload
    
    def mutate(self, info, username, password):
        user = authenticate(username=username, password=password)
        if user:
            login(info.context, user)
            return AuthPayload(user=user, success=True, message="Login successful")
        return AuthPayload(user=None, success=False, message="Invalid credentials")


class LogoutUser(graphene.Mutation):
    Output = AuthPayload
    
    def mutate(self, info):
        if info.context.user.is_authenticated:
            logout(info.context)
            return AuthPayload(user=None, success=True, message="Logged out successfully")
        return AuthPayload(user=None, success=False, message="Not logged in")


class CreateOrder(graphene.Mutation):
    class Arguments:
        chef_id = graphene.ID(required=True)
        items = graphene.List(OrderItemInput, required=True)
        delivery_address = graphene.String(required=True)
        delivery_instructions = graphene.String()
    
    order = graphene.Field(OrderType)
    success = graphene.Boolean()
    message = graphene.String()
    
    def mutate(self, info, chef_id, items, delivery_address, delivery_instructions=None):
        user = info.context.user
        if not user.is_authenticated:
            return CreateOrder(success=False, message="Authentication required")
        
        try:
            chef_profile = ChefProfile.objects.get(id=chef_id, is_available=True)
            
            # Calculate order totals
            subtotal = Decimal('0.00')
            order_items_data = []
            
            for item_input in items:
                menu_item = MenuItem.objects.get(id=item_input.menu_item_id, is_available=True)
                if menu_item.chef_profile != chef_profile:
                    return CreateOrder(success=False, message="All items must be from the same chef")
                
                item_total = menu_item.price * item_input.quantity
                subtotal += item_total
                
                order_items_data.append({
                    'menu_item': menu_item,
                    'quantity': item_input.quantity,
                    'unit_price': menu_item.price,
                    'customizations': item_input.customizations or {}
                })
            
            # Calculate fees
            delivery_fee = Decimal('2.99')  # This could be dynamic based on distance
            platform_fee = subtotal * Decimal('0.10')  # 10% platform commission
            total_amount = subtotal + delivery_fee + platform_fee
            
            # Create Stripe payment intent
            payment_intent = stripe.PaymentIntent.create(
                amount=int(total_amount * 100),  # Convert to cents
                currency='usd',
                metadata={
                    'chef_id': str(chef_id),
                    'client_id': str(user.id)
                }
            )
            
            # Create order
            order = Order.objects.create(
                client=user,
                chef_profile=chef_profile,
                subtotal=subtotal,
                delivery_fee=delivery_fee,
                platform_fee=platform_fee,
                total_amount=total_amount,
                delivery_address=delivery_address,
                delivery_instructions=delivery_instructions or '',
                stripe_payment_intent_id=payment_intent.id
            )
            
            # Create order items
            for item_data in order_items_data:
                OrderItem.objects.create(
                    order=order,
                    **item_data
                )
            
            return CreateOrder(order=order, success=True, message="Order created successfully")
            
        except ChefProfile.DoesNotExist:
            return CreateOrder(success=False, message="Chef not found or unavailable")
        except MenuItem.DoesNotExist:
            return CreateOrder(success=False, message="Menu item not found")
        except Exception as e:
            return CreateOrder(success=False, message=str(e))


class UpdateOrderStatus(graphene.Mutation):
    class Arguments:
        order_id = graphene.ID(required=True)
        status = graphene.String(required=True)
    
    order = graphene.Field(OrderType)
    success = graphene.Boolean()
    message = graphene.String()
    
    def mutate(self, info, order_id, status):
        user = info.context.user
        if not user.is_authenticated or user.role != 'chef':
            return UpdateOrderStatus(success=False, message="Chef authentication required")
        
        try:
            order = Order.objects.get(id=order_id, chef_profile__user=user)
            
            # Validate status transition
            valid_statuses = ['confirmed', 'in_progress', 'ready', 'out_for_delivery', 'delivered']
            if status not in valid_statuses:
                return UpdateOrderStatus(success=False, message="Invalid status")
            
            order.status = status
            if status == 'confirmed':
                order.confirmed_at = timezone.now()
            elif status == 'delivered':
                order.completed_at = timezone.now()
            
            order.save()
            
            return UpdateOrderStatus(order=order, success=True, message="Order status updated")
            
        except Order.DoesNotExist:
            return UpdateOrderStatus(success=False, message="Order not found")
        except Exception as e:
            return UpdateOrderStatus(success=False, message=str(e))


class CreateMenuItem(graphene.Mutation):
    class Arguments:
        menu_item = MenuItemInput(required=True)
    
    menu_item = graphene.Field(MenuItemType)
    success = graphene.Boolean()
    message = graphene.String()
    
    def mutate(self, info, menu_item):
        user = info.context.user
        if not user.is_authenticated or user.role != 'chef':
            return CreateMenuItem(success=False, message="Chef authentication required")
        
        try:
            chef_profile = user.chef_profile
            
            new_item = MenuItem.objects.create(
                chef_profile=chef_profile,
                name=menu_item.name,
                description=menu_item.description,
                price=menu_item.price,
                category=menu_item.category,
                ingredients=menu_item.ingredients or [],
                allergens=menu_item.allergens or [],
                is_vegetarian=menu_item.is_vegetarian or False,
                is_vegan=menu_item.is_vegan or False,
                is_gluten_free=menu_item.is_gluten_free or False,
                customization_options=menu_item.customization_options or {},
                preparation_time_minutes=menu_item.preparation_time_minutes or 30
            )
            
            return CreateMenuItem(menu_item=new_item, success=True, message="Menu item created")
            
        except ChefProfile.DoesNotExist:
            return CreateMenuItem(success=False, message="Chef profile not found")
        except Exception as e:
            return CreateMenuItem(success=False, message=str(e))


class UpdateChefAvailability(graphene.Mutation):
    class Arguments:
        is_available = graphene.Boolean(required=True)
    
    chef_profile = graphene.Field(ChefProfileType)
    success = graphene.Boolean()
    message = graphene.String()
    
    def mutate(self, info, is_available):
        user = info.context.user
        if not user.is_authenticated or user.role != 'chef':
            return UpdateChefAvailability(success=False, message="Chef authentication required")
        
        try:
            chef_profile = user.chef_profile
            chef_profile.is_available = is_available
            chef_profile.save()
            
            status = "online" if is_available else "offline"
            return UpdateChefAvailability(
                chef_profile=chef_profile, 
                success=True, 
                message=f"Status updated to {status}"
            )
            
        except ChefProfile.DoesNotExist:
            return UpdateChefAvailability(success=False, message="Chef profile not found")


class SubmitReview(graphene.Mutation):
    class Arguments:
        order_id = graphene.ID(required=True)
        rating = graphene.Int(required=True)
        comment = graphene.String()
    
    review = graphene.Field(ReviewType)
    success = graphene.Boolean()
    message = graphene.String()
    
    def mutate(self, info, order_id, rating, comment=None):
        user = info.context.user
        if not user.is_authenticated:
            return SubmitReview(success=False, message="Authentication required")
        
        try:
            order = Order.objects.get(id=order_id, client=user, status='delivered')
            
            if hasattr(order, 'review'):
                return SubmitReview(success=False, message="Review already submitted for this order")
            
            if not (1 <= rating <= 5):
                return SubmitReview(success=False, message="Rating must be between 1 and 5")
            
            review = Review.objects.create(
                order=order,
                client=user,
                chef_profile=order.chef_profile,
                rating=rating,
                comment=comment or ''
            )
            
            # Update chef's average rating
            chef_profile = order.chef_profile
            reviews = Review.objects.filter(chef_profile=chef_profile, is_approved=True)
            if reviews.exists():
                avg_rating = reviews.aggregate(avg=models.Avg('rating'))['avg']
                chef_profile.average_rating = round(avg_rating, 2)
                chef_profile.total_reviews = reviews.count()
                chef_profile.save()
            
            return SubmitReview(review=review, success=True, message="Review submitted successfully")
            
        except Order.DoesNotExist:
            return SubmitReview(success=False, message="Order not found or not eligible for review")
        except Exception as e:
            return SubmitReview(success=False, message=str(e))


class Mutation(graphene.ObjectType):
    # Authentication
    register_client = RegisterClient.Field()
    register_chef = RegisterChef.Field()
    login_user = LoginUser.Field()
    logout_user = LogoutUser.Field()
    
    # Orders
    create_order = CreateOrder.Field()
    update_order_status = UpdateOrderStatus.Field()
    
    # Menu management
    create_menu_item = CreateMenuItem.Field()
    
    # Chef operations
    update_chef_availability = UpdateChefAvailability.Field()
    
    # Reviews
    submit_review = SubmitReview.Field()


schema = graphene.Schema(query=Query, mutation=Mutation)