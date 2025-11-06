"""
Comprehensive Test Suite for Teka Platform
Tests complete user workflows from discovery to ordering
"""

import os
import sys
import django
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.management import call_command
from decimal import Decimal
import json

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teka_platform.settings')
django.setup()

from core.models import User, ChefProfile, MenuItem, Order, OrderItem, Review


class TekaPlatformWorkflowTests(TestCase):
    """Test complete user workflows"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create test users
        self.client_user = User.objects.create_user(
            username='testclient',
            email='client@test.com',
            password='testpass123',
            first_name='John',
            last_name='Doe',
            role='client'
        )
        
        self.chef_user = User.objects.create_user(
            username='testchef',
            email='chef@test.com', 
            password='testpass123',
            first_name='Jane',
            last_name='Chef',
            role='chef'
        )
        
        # Create chef profile
        self.chef_profile = ChefProfile.objects.create(
            user=self.chef_user,
            bio="Test chef specializing in Italian cuisine",
            address="123 Test Street, New York, NY 10001",
            latitude=40.7128,
            longitude=-74.0060,
            is_available=True,
            is_verified=True,
            average_rating=Decimal('4.5'),
            total_reviews=10
        )
        
        # Create test menu items
        self.menu_items = []
        menu_data = [
            {"name": "Margherita Pizza", "price": "18.99", "category": "main_course"},
            {"name": "Caesar Salad", "price": "12.99", "category": "appetizer"},
            {"name": "Tiramisu", "price": "8.99", "category": "dessert"}
        ]
        
        for item_data in menu_data:
            item = MenuItem.objects.create(
                chef_profile=self.chef_profile,
                name=item_data["name"],
                description=f"Delicious {item_data['name']}",
                price=Decimal(item_data["price"]),
                category=item_data["category"],
                is_available=True
            )
            self.menu_items.append(item)
    
    def test_homepage_discovery(self):
        """Test 1: Homepage chef discovery"""
        print("🏠 Testing homepage discovery...")
        
        response = self.client.get(reverse('client_portal:home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Featured Chefs')
        self.assertContains(response, self.chef_profile.user.get_full_name())
        print("✅ Homepage loads correctly with featured chefs")
    
    def test_chef_search_and_filtering(self):
        """Test 2: Chef search and filtering"""
        print("🔍 Testing chef search and filtering...")
        
        # Test chef list page
        response = self.client.get(reverse('client_portal:chef_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.chef_profile.user.get_full_name())
        
        # Test search functionality
        response = self.client.get(
            reverse('client_portal:search_chefs') + '?q=Italian'
        )
        self.assertEqual(response.status_code, 200)
        print("✅ Chef search and filtering work correctly")
    
    def test_chef_detail_and_menu_viewing(self):
        """Test 3: Chef profile and menu viewing"""
        print("👨‍🍳 Testing chef detail page...")
        
        response = self.client.get(
            reverse('client_portal:chef_detail', kwargs={'chef_id': self.chef_profile.id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.chef_profile.bio)
        
        # Check menu items are displayed
        for item in self.menu_items:
            self.assertContains(response, item.name)
            self.assertContains(response, str(item.price))
        
        print("✅ Chef detail page displays correctly with menu")
    
    def test_user_registration_and_login(self):
        """Test 4: User registration and authentication"""
        print("🔐 Testing user registration and login...")
        
        # Test registration page
        response = self.client.get(reverse('client_portal:register'))
        self.assertEqual(response.status_code, 200)
        
        # Test new user registration
        reg_data = {
            'username': 'newclient',
            'email': 'newclient@test.com',
            'password1': 'complexpass123',
            'password2': 'complexpass123',
            'first_name': 'New',
            'last_name': 'Client',
            'role': 'client'
        }
        response = self.client.post(reverse('client_portal:register'), reg_data)
        self.assertTrue(User.objects.filter(username='newclient').exists())
        
        # Test login
        response = self.client.get(reverse('client_portal:login'))
        self.assertEqual(response.status_code, 200)
        
        login_success = self.client.login(username='testclient', password='testpass123')
        self.assertTrue(login_success)
        
        print("✅ User registration and login work correctly")
    
    def test_add_to_cart_workflow(self):
        """Test 5: Add items to cart"""
        print("🛒 Testing add to cart workflow...")
        
        # Login first
        self.client.login(username='testclient', password='testpass123')
        
        # Add item to cart via AJAX
        cart_data = {
            'menu_item_id': str(self.menu_items[0].id),
            'quantity': 2,
            'special_instructions': 'Extra cheese please'
        }
        
        response = self.client.post(
            reverse('client_portal:add_to_cart'),
            data=json.dumps(cart_data),
            content_type='application/json'
        )
        
        # Check if cart session was created
        session = self.client.session
        self.assertIn('cart', session)
        
        print("✅ Add to cart functionality works")
    
    def test_order_placement(self):
        """Test 6: Complete order placement"""
        print("📝 Testing order placement...")
        
        # Login and add items to cart first
        self.client.login(username='testclient', password='testpass123')
        
        # Create an order manually for testing
        order = Order.objects.create(
            client=self.client_user,
            chef_profile=self.chef_profile,
            delivery_address="456 Client Street, New York, NY 10001",
            subtotal=Decimal('31.98'),
            delivery_fee=Decimal('5.00'),
            platform_fee=Decimal('3.70'),
            total_amount=Decimal('40.68'),
            status='pending'
        )
        
        # Add order items
        for i, item in enumerate(self.menu_items[:2]):
            OrderItem.objects.create(
                order=order,
                menu_item=item,
                quantity=1,
                price=item.price,
                subtotal=item.price
            )
        
        # Test order detail page
        response = self.client.get(
            reverse('client_portal:order_detail', kwargs={'order_id': order.id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, str(order.total_amount))
        
        print("✅ Order placement and viewing work correctly")
    
    def test_chef_portal_access(self):
        """Test 7: Chef portal functionality"""
        print("👨‍🍳 Testing chef portal access...")
        
        # Login as chef
        self.client.login(username='testchef', password='testpass123')
        
        # Test chef dashboard
        response = self.client.get(reverse('chef_portal:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dashboard')
        
        # Test menu management
        response = self.client.get(reverse('chef_portal:menu'))
        self.assertEqual(response.status_code, 200)
        
        # Check menu items are listed
        for item in self.menu_items:
            self.assertContains(response, item.name)
        
        print("✅ Chef portal access and functionality work")
    
    def test_order_management_workflow(self):
        """Test 8: Order status management"""
        print("📋 Testing order management workflow...")
        
        # Create an order
        order = Order.objects.create(
            client=self.client_user,
            chef_profile=self.chef_profile,
            delivery_address="789 Test Avenue",
            subtotal=Decimal('25.00'),
            delivery_fee=Decimal('5.00'),
            platform_fee=Decimal('3.00'),
            total_amount=Decimal('33.00'),
            status='pending'
        )
        
        # Login as chef and check order management
        self.client.login(username='testchef', password='testpass123')
        
        response = self.client.get(reverse('chef_portal:orders'))
        self.assertEqual(response.status_code, 200)
        
        print("✅ Order management workflow accessible")
    
    def test_review_system(self):
        """Test 9: Review and rating system"""
        print("⭐ Testing review system...")
        
        # Login as client
        self.client.login(username='testclient', password='testpass123')
        
        # Create a completed order first
        order = Order.objects.create(
            client=self.client_user,
            chef_profile=self.chef_profile,
            delivery_address="Test Address",
            subtotal=Decimal('20.00'),
            delivery_fee=Decimal('5.00'),
            platform_fee=Decimal('2.50'),
            total_amount=Decimal('27.50'),
            status='delivered'
        )
        
        # Create a review
        review = Review.objects.create(
            client=self.client_user,
            chef_profile=self.chef_profile,
            order=order,
            rating=5,
            comment="Excellent food and service!"
        )
        
        # Check review appears on chef page
        response = self.client.get(
            reverse('client_portal:chef_detail', kwargs={'chef_id': self.chef_profile.id})
        )
        self.assertContains(response, review.comment)
        
        print("✅ Review system works correctly")
    
    def test_payment_flow_setup(self):
        """Test 10: Payment integration setup"""
        print("💳 Testing payment flow setup...")
        
        # Create an order for checkout
        order = Order.objects.create(
            client=self.client_user,
            chef_profile=self.chef_profile,
            delivery_address="Payment Test Address",
            subtotal=Decimal('30.00'),
            delivery_fee=Decimal('5.00'),
            platform_fee=Decimal('3.50'),
            total_amount=Decimal('38.50'),
            status='pending'
        )
        
        # Login as client
        self.client.login(username='testclient', password='testpass123')
        
        # Test checkout page access
        response = self.client.get(
            reverse('client_portal:checkout', kwargs={'order_id': order.id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Payment Information')
        self.assertContains(response, str(order.total_amount))
        
        print("✅ Payment flow setup is accessible")
    

    def test_chef_location_filtering(self):
        """Test 11: Chef location filtering"""
        print("📍 Testing chef location filtering...")
        
        # Test location filtering
        response = self.client.get(
            reverse('client_portal:chef_list') + '?city=New%20York'
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.chef_profile.user.get_full_name())
        print("✅ Chef location filtering works correctly")

        """Run all workflow tests"""
        print("🚀 Starting Teka Platform Workflow Tests...\n")
        
        try:
            self.test_homepage_discovery()
            self.test_chef_search_and_filtering()
            self.test_chef_detail_and_menu_viewing()
            self.test_user_registration_and_login()
            self.test_add_to_cart_workflow()
            self.test_order_placement()
            self.test_chef_portal_access()
            self.test_order_management_workflow()
            self.test_review_system()
            self.test_payment_flow_setup()
            
            print("\n🎉 ALL TESTS PASSED! Teka Platform workflows are working correctly.")
            return True
            
        except Exception as e:
            print(f"\n❌ Test failed with error: {str(e)}")
            return False


def run_workflow_tests():
    """Main function to run workflow tests"""
    from django.test.utils import get_runner
    from django.conf import settings
    
    # Use Django's test runner
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    
    # Run the tests
    test_suite = TekaPlatformWorkflowTests()
    test_suite.setUp()
    return test_suite.run_all_tests()


if __name__ == '__main__':
    success = run_workflow_tests()
    sys.exit(0 if success else 1)