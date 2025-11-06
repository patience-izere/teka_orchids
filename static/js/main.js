/* Custom JavaScript for Teka Platform */

// CSRF token setup for Django
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

const csrftoken = getCookie('csrftoken');

// WebSocket connection for real-time updates
class TekaWebSocket {
    constructor(userId) {
        this.userId = userId;
        this.socket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
        
        this.connect();
    }
    
    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/notifications/${this.userId}/`;
        
        this.socket = new WebSocket(wsUrl);
        
        this.socket.onopen = () => {
            console.log('WebSocket connected');
            this.reconnectAttempts = 0;
            this.showConnectionStatus('Connected', 'success');
        };
        
        this.socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleNotification(data);
        };
        
        this.socket.onclose = () => {
            console.log('WebSocket disconnected');
            this.showConnectionStatus('Disconnected', 'warning');
            this.reconnect();
        };
        
        this.socket.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.showConnectionStatus('Connection Error', 'danger');
        };
    }
    
    reconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            setTimeout(() => {
                this.reconnectAttempts++;
                console.log(`Reconnection attempt ${this.reconnectAttempts}`);
                this.connect();
            }, this.reconnectDelay * this.reconnectAttempts);
        }
    }
    
    handleNotification(data) {
        // Show toast notification
        this.showToast(data.message, data.type || 'info');
        
        // Update UI based on notification type
        if (data.type === 'order_status_update') {
            this.updateOrderStatus(data.order_id, data.status);
        } else if (data.type === 'new_order') {
            this.handleNewOrder(data.order_id);
        }
        
        // Update notification badge
        this.updateNotificationBadge();
    }
    
    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type} border-0`;
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        
        const container = document.getElementById('toast-container') || this.createToastContainer();
        container.appendChild(toast);
        
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
        
        // Auto-remove after hide
        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });
    }
    
    createToastContainer() {
        const container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container position-fixed top-0 end-0 p-3';
        container.style.zIndex = '9999';
        document.body.appendChild(container);
        return container;
    }
    
    showConnectionStatus(status, type) {
        const statusElement = document.getElementById('connection-status');
        if (statusElement) {
            statusElement.textContent = status;
            statusElement.className = `badge bg-${type}`;
        }
    }
    
    updateOrderStatus(orderId, status) {
        const orderElement = document.querySelector(`[data-order-id="${orderId}"]`);
        if (orderElement) {
            const statusBadge = orderElement.querySelector('.order-status');
            if (statusBadge) {
                statusBadge.textContent = status;
                statusBadge.className = `badge order-status ${this.getStatusBadgeClass(status)}`;
            }
        }
    }
    
    getStatusBadgeClass(status) {
        const statusClasses = {
            'pending': 'bg-warning',
            'confirmed': 'bg-info',
            'in_progress': 'bg-primary',
            'ready': 'bg-success',
            'delivered': 'bg-success',
            'cancelled': 'bg-danger'
        };
        return statusClasses[status] || 'bg-secondary';
    }
    
    handleNewOrder(orderId) {
        // Refresh orders list if on orders page
        if (window.location.pathname.includes('orders')) {
            location.reload();
        }
    }
    
    updateNotificationBadge() {
        const badge = document.querySelector('.notification-badge');
        if (badge) {
            const count = parseInt(badge.textContent) || 0;
            badge.textContent = count + 1;
            badge.style.display = 'inline';
        }
    }
}

// Shopping Cart functionality
class ShoppingCart {
    constructor() {
        this.items = JSON.parse(localStorage.getItem('teka_cart')) || [];
        this.updateCartUI();
    }
    
    addItem(menuItemId, name, price, chefId, chefName) {
        const existingItem = this.items.find(item => item.menuItemId === menuItemId);
        
        if (existingItem) {
            existingItem.quantity += 1;
        } else {
            this.items.push({
                menuItemId,
                name,
                price: parseFloat(price),
                quantity: 1,
                chefId,
                chefName
            });
        }
        
        this.saveCart();
        this.updateCartUI();
        this.showAddedNotification(name);
    }
    
    removeItem(menuItemId) {
        this.items = this.items.filter(item => item.menuItemId !== menuItemId);
        this.saveCart();
        this.updateCartUI();
    }
    
    updateQuantity(menuItemId, quantity) {
        const item = this.items.find(item => item.menuItemId === menuItemId);
        if (item) {
            if (quantity <= 0) {
                this.removeItem(menuItemId);
            } else {
                item.quantity = quantity;
                this.saveCart();
                this.updateCartUI();
            }
        }
    }
    
    clear() {
        this.items = [];
        this.saveCart();
        this.updateCartUI();
    }
    
    getTotal() {
        return this.items.reduce((total, item) => total + (item.price * item.quantity), 0);
    }
    
    getItemCount() {
        return this.items.reduce((count, item) => count + item.quantity, 0);
    }
    
    saveCart() {
        localStorage.setItem('teka_cart', JSON.stringify(this.items));
    }
    
    updateCartUI() {
        // Update cart badge
        const cartBadge = document.querySelector('.cart-badge');
        const itemCount = this.getItemCount();
        
        if (cartBadge) {
            if (itemCount > 0) {
                cartBadge.textContent = itemCount;
                cartBadge.style.display = 'inline';
            } else {
                cartBadge.style.display = 'none';
            }
        }
        
        // Update cart dropdown
        this.updateCartDropdown();
        
        // Update cart page if we're on it
        if (window.location.pathname.includes('cart')) {
            this.updateCartPage();
        }
    }
    
    updateCartDropdown() {
        const cartDropdown = document.getElementById('cart-dropdown');
        if (!cartDropdown) return;
        
        if (this.items.length === 0) {
            cartDropdown.innerHTML = '<p class="text-muted p-3">Your cart is empty</p>';
            return;
        }
        
        let html = '';
        this.items.forEach(item => {
            html += `
                <div class="cart-item p-2 border-bottom">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <h6 class="mb-0">${item.name}</h6>
                            <small class="text-muted">by ${item.chefName}</small>
                        </div>
                        <div class="text-end">
                            <div>$${(item.price * item.quantity).toFixed(2)}</div>
                            <small class="text-muted">Qty: ${item.quantity}</small>
                        </div>
                    </div>
                </div>
            `;
        });
        
        html += `
            <div class="p-3">
                <div class="d-flex justify-content-between mb-2">
                    <strong>Total: $${this.getTotal().toFixed(2)}</strong>
                </div>
                <a href="/client/cart/" class="btn btn-primary btn-sm w-100">View Cart</a>
            </div>
        `;
        
        cartDropdown.innerHTML = html;
    }
    
    updateCartPage() {
        // This would be implemented on the cart page
        console.log('Updating cart page...');
    }
    
    showAddedNotification(itemName) {
        const toast = document.createElement('div');
        toast.className = 'toast align-items-center text-white bg-success border-0';
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    <i class="fas fa-check-circle me-2"></i>
                    ${itemName} added to cart
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        
        const container = document.getElementById('toast-container') || this.createToastContainer();
        container.appendChild(toast);
        
        const bsToast = new bootstrap.Toast(toast, { delay: 2000 });
        bsToast.show();
    }
    
    createToastContainer() {
        const container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container position-fixed top-0 end-0 p-3';
        container.style.zIndex = '9999';
        document.body.appendChild(container);
        return container;
    }
}

// Initialize cart on page load
let cart;
document.addEventListener('DOMContentLoaded', function() {
    cart = new ShoppingCart();
    
    // Initialize WebSocket if user is authenticated
    const userId = document.body.dataset.userId;
    if (userId) {
        new TekaWebSocket(userId);
    }
    
    // Add to cart button handlers
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('add-to-cart-btn')) {
            e.preventDefault();
            const btn = e.target;
            const menuItemId = btn.dataset.menuItemId;
            const name = btn.dataset.name;
            const price = btn.dataset.price;
            const chefId = btn.dataset.chefId;
            const chefName = btn.dataset.chefName;
            
            cart.addItem(menuItemId, name, price, chefId, chefName);
        }
    });
});

// Chef availability toggle
function toggleAvailability() {
    fetch('/chef/toggle-availability/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrftoken,
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const badge = document.querySelector('.availability-badge');
            const toggle = document.querySelector('.availability-toggle');
            
            if (data.available) {
                badge.textContent = 'Available';
                badge.className = 'availability-badge badge bg-success';
                toggle.textContent = 'Go Offline';
                toggle.className = 'btn btn-outline-danger btn-sm availability-toggle';
            } else {
                badge.textContent = 'Offline';
                badge.className = 'availability-badge badge bg-secondary';
                toggle.textContent = 'Go Online';
                toggle.className = 'btn btn-outline-success btn-sm availability-toggle';
            }
        }
    })
    .catch(error => console.error('Error:', error));
}

// Order status update
function updateOrderStatus(orderId, status) {
    fetch(`/chef/orders/${orderId}/update-status/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrftoken,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ status })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            location.reload();
        } else {
            alert('Error updating order status');
        }
    })
    .catch(error => console.error('Error:', error));
}

// Location detection
function getCurrentLocation() {
    return new Promise((resolve, reject) => {
        if (!navigator.geolocation) {
            reject(new Error('Geolocation is not supported'));
            return;
        }
        
        navigator.geolocation.getCurrentPosition(
            position => {
                resolve({
                    latitude: position.coords.latitude,
                    longitude: position.coords.longitude
                });
            },
            error => reject(error),
            {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 300000
            }
        );
    });
}

// Chef search with location
async function searchChefs() {
    const searchInput = document.getElementById('chef-search');
    const query = searchInput ? searchInput.value : '';
    
    try {
        const location = await getCurrentLocation();
        
        const params = new URLSearchParams({
            q: query,
            lat: location.latitude,
            lng: location.longitude
        });
        
        window.location.href = `/client/chefs/?${params.toString()}`;
        
    } catch (error) {
        console.error('Location error:', error);
        // Search without location
        const params = new URLSearchParams({ q: query });
        window.location.href = `/client/chefs/?${params.toString()}`;
    }
}

// Initialize search
document.addEventListener('DOMContentLoaded', function() {
    const searchForm = document.getElementById('chef-search-form');
    if (searchForm) {
        searchForm.addEventListener('submit', function(e) {
            e.preventDefault();
            searchChefs();
        });
    }
});

// Rating stars interaction
function setRating(rating) {
    const stars = document.querySelectorAll('.rating-star');
    const ratingInput = document.getElementById('rating');
    
    stars.forEach((star, index) => {
        if (index < rating) {
            star.classList.add('fas');
            star.classList.remove('far');
        } else {
            star.classList.add('far');
            star.classList.remove('fas');
        }
    });
    
    if (ratingInput) {
        ratingInput.value = rating;
    }
}

// Initialize rating stars
document.addEventListener('DOMContentLoaded', function() {
    const stars = document.querySelectorAll('.rating-star');
    stars.forEach((star, index) => {
        star.addEventListener('click', () => setRating(index + 1));
        star.addEventListener('mouseover', () => {
            // Highlight stars on hover
            stars.forEach((s, i) => {
                if (i <= index) {
                    s.style.color = '#ffc107';
                } else {
                    s.style.color = '#dee2e6';
                }
            });
        });
    });
    
    // Reset on mouse leave
    const ratingContainer = document.querySelector('.rating-container');
    if (ratingContainer) {
        ratingContainer.addEventListener('mouseleave', () => {
            const currentRating = document.getElementById('rating')?.value || 0;
            setRating(currentRating);
        });
    }
});