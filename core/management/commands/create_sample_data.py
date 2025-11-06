from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models.signals import post_save
from core.models import ChefProfile, MenuItem, Review, Order, OrderItem
from decimal import Decimal
import random

User = get_user_model()

class Command(BaseCommand):
    help = 'Create sample data for testing the Teka platform'

    def handle(self, *args, **options):
        self.stdout.write('Creating sample data...')
        
        # Temporarily disable signals to avoid Redis connection issues
        from core.signals import order_created_notification, order_status_updated
        
        post_save.disconnect(order_created_notification, sender=Order)
        post_save.disconnect(order_status_updated, sender=Order)
        
        try:
            # Clear existing sample data
            User.objects.filter(username__startswith='client').delete()
            User.objects.filter(username__endswith='_chef').delete()
            
            # Create sample clients
            clients = []
            for i in range(10):
                user = User.objects.create_user(
                username=f'client{i+1}',
                email=f'client{i+1}@example.com',
                password='testpass123',
                first_name=f'Client{i+1}',
                last_name='User',
                role='client'
            )
            clients.append(user)
        
        # Create sample chefs
        chefs_data = [
            {
                'username': 'maria_chef',
                'email': 'maria@example.com',
                'first_name': 'Maria',
                'last_name': 'Rodriguez',
                'bio': 'Authentic Mexican cuisine specialist with 15 years of experience. I use traditional family recipes passed down through generations.',
                'cuisine': 'Mexican',
                'city': 'Los Angeles',
                'state': 'CA',
                'lat': 34.0522,
                'lng': -118.2437,
                'years_exp': 15
            },
            {
                'username': 'luigi_chef',
                'email': 'luigi@example.com',
                'first_name': 'Luigi',
                'last_name': 'Benedetti',
                'bio': 'Traditional Italian chef specializing in handmade pasta and authentic regional dishes from Tuscany.',
                'cuisine': 'Italian',
                'city': 'San Francisco',
                'state': 'CA',
                'lat': 37.7749,
                'lng': -122.4194,
                'years_exp': 20
            },
            {
                'username': 'kenji_chef',
                'email': 'kenji@example.com',
                'first_name': 'Kenji',
                'last_name': 'Tanaka',
                'bio': 'Master sushi chef and Japanese cuisine expert. Trained in Tokyo and brings authentic flavors to your home.',
                'cuisine': 'Japanese',
                'city': 'Seattle',
                'state': 'WA',
                'lat': 47.6062,
                'lng': -122.3321,
                'years_exp': 12
            },
            {
                'username': 'priya_chef',
                'email': 'priya@example.com',
                'first_name': 'Priya',
                'last_name': 'Sharma',
                'bio': 'Indian cuisine specialist focusing on regional dishes from Punjab and Gujarat. Vegetarian and vegan options available.',
                'cuisine': 'Indian',
                'city': 'New York',
                'state': 'NY',
                'lat': 40.7128,
                'lng': -74.0060,
                'years_exp': 8
            },
            {
                'username': 'pierre_chef',
                'email': 'pierre@example.com',
                'first_name': 'Pierre',
                'last_name': 'Dubois',
                'bio': 'French culinary artist specializing in classic French cuisine and modern interpretations of traditional dishes.',
                'cuisine': 'French',
                'city': 'Chicago',
                'state': 'IL',
                'lat': 41.8781,
                'lng': -87.6298,
                'years_exp': 18
            }
        ]
        
        chef_profiles = []
        for chef_data in chefs_data:
            user = User.objects.create_user(
                username=chef_data['username'],
                email=chef_data['email'],
                password='testpass123',
                first_name=chef_data['first_name'],
                last_name=chef_data['last_name'],
                role='chef'
            )
            
            chef_profile = ChefProfile.objects.create(
                user=user,
                bio=chef_data['bio'],
                address=f"123 {chef_data['cuisine']} Street",
                latitude=chef_data['lat'],
                longitude=chef_data['lng'],
                is_available=True,
                is_verified=True,
                minimum_order_amount=Decimal('15.00')
            )
            chef_profiles.append(chef_profile)
        
        # Create sample menu items
        # Store cuisine type for later use
        for i, chef_profile in enumerate(chef_profiles):
            cuisine = chefs_data[i]['cuisine']
            # We'll store this info in bio or use it for menu creation
            setattr(chef_profile, '_cuisine_temp', cuisine)
        
        menu_items_data = {
            'Mexican': [
                {'name': 'Authentic Tacos al Pastor', 'price': '12.99', 'category': 'Main Course', 
                 'description': 'Marinated pork with pineapple, served on handmade corn tortillas with cilantro and onions'},
                {'name': 'Homemade Guacamole', 'price': '8.99', 'category': 'Appetizer',
                 'description': 'Fresh avocados mashed with lime, cilantro, and jalapeños'},
                {'name': 'Chile Rellenos', 'price': '15.99', 'category': 'Main Course',
                 'description': 'Roasted poblano peppers stuffed with cheese, battered and fried'},
                {'name': 'Tres Leches Cake', 'price': '6.99', 'category': 'Dessert',
                 'description': 'Traditional sponge cake soaked in three types of milk'}
            ],
            'Italian': [
                {'name': 'Fresh Pasta Carbonara', 'price': '16.99', 'category': 'Main Course',
                 'description': 'Handmade fettuccine with pancetta, eggs, and pecorino romano'},
                {'name': 'Margherita Pizza', 'price': '14.99', 'category': 'Main Course',
                 'description': 'Wood-fired pizza with fresh mozzarella, basil, and San Marzano tomatoes'},
                {'name': 'Antipasto Platter', 'price': '18.99', 'category': 'Appetizer',
                 'description': 'Selection of cured meats, cheeses, olives, and roasted vegetables'},
                {'name': 'Tiramisu', 'price': '7.99', 'category': 'Dessert',
                 'description': 'Classic Italian dessert with mascarpone and espresso-soaked ladyfingers'}
            ],
            'Japanese': [
                {'name': 'Sushi Omakase Set', 'price': '45.99', 'category': 'Main Course',
                 'description': 'Chef\'s selection of 12 pieces of fresh nigiri sushi'},
                {'name': 'Chicken Teriyaki Bento', 'price': '18.99', 'category': 'Main Course',
                 'description': 'Grilled chicken with teriyaki sauce, rice, and assorted sides'},
                {'name': 'Miso Soup', 'price': '4.99', 'category': 'Appetizer',
                 'description': 'Traditional soybean paste soup with tofu and wakame seaweed'},
                {'name': 'Mochi Ice Cream', 'price': '8.99', 'category': 'Dessert',
                 'description': 'Sweet rice cake filled with premium ice cream (3 pieces)'}
            ],
            'Indian': [
                {'name': 'Butter Chicken', 'price': '16.99', 'category': 'Main Course',
                 'description': 'Tender chicken in creamy tomato-based curry with aromatic spices'},
                {'name': 'Vegetable Biryani', 'price': '14.99', 'category': 'Main Course',
                 'description': 'Fragrant basmati rice with mixed vegetables and traditional spices'},
                {'name': 'Samosas (4 pieces)', 'price': '7.99', 'category': 'Appetizer',
                 'description': 'Crispy pastries filled with spiced potatoes and peas'},
                {'name': 'Kulfi', 'price': '5.99', 'category': 'Dessert',
                 'description': 'Traditional Indian ice cream with cardamom and pistachios'}
            ],
            'French': [
                {'name': 'Coq au Vin', 'price': '22.99', 'category': 'Main Course',
                 'description': 'Braised chicken in red wine with mushrooms and pearl onions'},
                {'name': 'French Onion Soup', 'price': '9.99', 'category': 'Appetizer',
                 'description': 'Rich beef broth with caramelized onions and gruyère cheese'},
                {'name': 'Ratatouille', 'price': '12.99', 'category': 'Main Course',
                 'description': 'Traditional Provençal vegetable stew with herbs de Provence'},
                {'name': 'Crème Brûlée', 'price': '8.99', 'category': 'Dessert',
                 'description': 'Vanilla custard with caramelized sugar crust'}
            ]
        }
        
        # Create menu items for each chef
        for i, chef_profile in enumerate(chef_profiles):
            cuisine = chefs_data[i]['cuisine']
            if cuisine in menu_items_data:
                for item_data in menu_items_data[cuisine]:
                    # Convert category to match model choices
                    category_mapping = {
                        'Main Course': 'main_course',
                        'Appetizer': 'appetizer',
                        'Dessert': 'dessert'
                    }
                    category_value = category_mapping.get(item_data['category'], 'main_course')
                    
                    MenuItem.objects.create(
                        chef_profile=chef_profile,
                        name=item_data['name'],
                        description=item_data['description'],
                        price=Decimal(item_data['price']),
                        category=category_value,
                        is_available=True,
                        preparation_time_minutes=random.randint(15, 45)
                    )
        
        # Sample review comments
        review_comments = [
            "Amazing food! The flavors were authentic and delicious.",
            "Outstanding quality and presentation. Highly recommended!",
            "The best homemade meal I've had in years. Will order again!",
            "Incredible taste and generous portions. Worth every penny.",
            "Fresh ingredients and expertly prepared. Fantastic experience!",
            "Authentic flavors that remind me of home. Excellent chef!",
            "Professional service and incredible food. 5 stars!",
            "The attention to detail and flavor is remarkable.",
            "Perfectly seasoned and cooked to perfection.",
            "A culinary artist! The food was exceptional."
        ]
        
        # Create sample orders
        for _ in range(20):
            client = random.choice(clients)
            chef_profile = random.choice(chef_profiles)
            
            order = Order.objects.create(
                client=client,
                chef_profile=chef_profile,
                total_amount=Decimal('0.00'),
                subtotal=Decimal('0.00'),
                status=random.choice(['placed', 'confirmed', 'in_progress', 'ready', 'delivered']),
                delivery_address="456 Sample St, Sample City, SC"
            )
            
            # Add 1-3 items to each order
            menu_items = list(MenuItem.objects.filter(chef_profile=chef_profile))
            order_total = Decimal('0.00')
            
            for _ in range(random.randint(1, 3)):
                menu_item = random.choice(menu_items)
                quantity = random.randint(1, 2)
                
                OrderItem.objects.create(
                    order=order,
                    menu_item=menu_item,
                    quantity=quantity,
                    price=menu_item.price
                )
                
                order_total += menu_item.price * quantity
            
            order.subtotal = order_total
            order.total_amount = order_total
            order.save()
            
            # Create review for delivered orders
            if order.status == 'delivered' and random.choice([True, False]):  # 50% chance
                Review.objects.create(
                    order=order,
                    client=client,
                    chef_profile=chef_profile,
                    rating=random.randint(4, 5),  # High ratings for sample data
                    comment=random.choice(review_comments)
                )
        
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully created sample data:\n'
                        f'- {len(clients)} clients\n'
                        f'- {len(chef_profiles)} chef profiles\n'
                        f'- {MenuItem.objects.count()} menu items\n'
                        f'- {Review.objects.count()} reviews\n'
                        f'- {Order.objects.count()} orders'
                    )
                )
        
        finally:
            # Reconnect signals
            post_save.connect(order_created_notification, sender=Order)
            post_save.connect(order_status_updated, sender=Order)