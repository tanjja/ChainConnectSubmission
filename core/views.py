from django.shortcuts import render, get_object_or_404, redirect
from .models import *
from django.http import JsonResponse
import json
from django.views.decorators.csrf import csrf_exempt
import datetime
from .utils import cookieCart, cartData, guestOrder
from django import forms
from django.contrib import messages
from django.db.models import Sum, Avg, Count, F
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
import re
from django.http import HttpResponseForbidden


# Create your views here.

def index(request):
    featured_products = Product.objects.all()[:3]
    return render(request, 'core/index.html', {'featured_products': featured_products})

def store(request):
  data = cartData(request)

  cartItems = data['cartItems']
  order = data['order']
  items = data['items']

  # Get the search query from the GET request
  query = request.GET.get('q', '')

  # Filter products based on the search query if provided
  if query:
    products = Product.objects.filter(name__icontains=query)
  else:
    products = Product.objects.all()

  context = {'products':products, 'cartItems':cartItems, 'query': query}
  return render(request, 'core/store.html', context)

def cart(request):

  data = cartData(request)

  cartItems = data['cartItems']
  order = data['order']
  items = data['items']

  context = {'items': items, 'order': order, 'cartItems':cartItems}
  return render(request, 'core/cart.html', context)

def checkout(request):
  data = cartData(request)

  cartItems = data['cartItems']
  order = data['order']
  items = data['items']

  context = {'items': items, 'order': order, 'cartItems': cartItems}
  return render(request, 'core/checkout.html', context)

def updateItem(request):
  data = json.loads(request.body)
  print("update start")
  productId = data['productId']
  action = data['action']
  quantity = data.get('quantity') #Test
  print('Action:', action)
  print('Product:', productId)
  print('Quantity:', quantity)

  customer = request.user.customer
  product = Product.objects.get(id=productId)
  order, created= Order.objects.get_or_create(customer=customer, complete=False)

  orderItem, created= OrderItem.objects.get_or_create(order=order, product=product)

  """
  if action == 'add':
        orderItem.quantity = (orderItem.quantity + 1)
  elif action == 'remove':
        orderItem.quantity = (orderItem.quantity - 1)
  """

  if action == 'add' and quantity is None:
    # Increment the quantity by 1 if no specific quantity is provided (add-to-cart button)
    orderItem.quantity += 1
  elif action == 'remove' and quantity is None:
    # Decrement the quantity by 1 if no specific quantity is provided (remove button)
    orderItem.quantity -= 1
  elif quantity is not None:
    orderItem.quantity = int(quantity)

  orderItem.save()

  if orderItem.quantity <= 0:
    orderItem.delete()

  return JsonResponse('Item was added', safe=False)

def confirm(request):
    order_number = request.GET.get('order_number')
    order = get_object_or_404(Order, transaction_id=order_number)
    context = {'order': order}
    return render(request, 'core/confirm.html', context)

def processOrder(request):
    transaction_id = datetime.datetime.now().timestamp()
    data = json.loads(request.body)

    if request.user.is_authenticated:
      customer = request.user.customer
      order, created = Order.objects.get_or_create(customer=customer, complete=False)

    else:
        print('User is not logged in')
        print('COOKIES:', request.COOKIES)
        customer, order = guestOrder(request, data)

        total = float(data['form']['total'])
        order.transaction_id = transaction_id

        if total == order.get_cart_total:
          order.complete = True
          order.save()

        if order.shipping == True:
          ShippingAddress.objects.create(
          customer=customer,
          order=order,
          address=data['shipping']['address'],
          city=data['shipping']['city'],
          state=data['shipping']['state'],
          zipcode=data['shipping']['zipcode'],
          )

    return JsonResponse({'transaction_id': order.transaction_id}, safe=False)

########################################################
# Editing Product Listings
# Directly defining the ProductForm inside views.py
class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'price', 'image']

    def clean_price(self):
        price = self.cleaned_data['price']
        if price < 0:
            raise forms.ValidationError('Price must be a positive number.')
        return price

    def clean_stock(self):
        stock = self.cleaned_data['stock']
        if stock < 0:
            raise forms.ValidationError('Stock must be a positive number.')
        return stock

from django.shortcuts import render
from .models import Product

# Product List View
def productList(request):
    products = Product.objects.all()  # Fetch all products
    return render(request, 'core/product_list.html', {'products': products})

# Add Product View
def productAdd(request):
    if request.method == 'POST':
        # Handle adding new product
        pass
    return render(request, 'core/product_add.html')

# Edit Product View
def productEdit(request, id):
    # Get the product based on the provided id (primary key)
    product = get_object_or_404(Product, id=id)

    if request.method == 'POST':
        # Update product details based on form submission
        product.name = request.POST.get('name')
        product.price = request.POST.get('price')
        
        # Check if a new image is uploaded
        if 'image' in request.FILES:
            product.image = request.FILES['image']
        
        # Save updated product data
        product.save()

        # Show a success message
        messages.success(request, 'Product updated successfully!')
        return redirect('product_list')  # Redirect to product list page after editing
    
    return render(request, 'core/product_edit.html', {'product': product})


#######################################
# Order Management

def orderList(request):
    # Fetch all orders
    orders = Order.objects.all()

    # Add shipping addresses to the orders
    order_data = []
    for order in orders:
        shipping_address = ShippingAddress.objects.filter(order=order).first()
        order_data.append({
            'order': order,
            'shipping_address': shipping_address,
        })

    return render(request, 'core/order_list.html', {'order_data': order_data})

# View to see the details of a specific order
def orderDetail(request, id):
    # Retrieve the specific order
    order = get_object_or_404(Order, id=id)

    # Retrieve the associated shipping address
    shipping_address = ShippingAddress.objects.filter(order=order).first()

    return render(request, 'core/order_detail.html', {
        'order': order,
        'shipping_address': shipping_address,
    })


# Sales Data

def salesDashboard(request):
    # Total Sales
    total_sales = Order.objects.filter(complete=True).aggregate(
        total_sales=Sum(F('orderitem__quantity') * F('orderitem__product__price'))
    )['total_sales'] or 0

    # Number of Orders
    number_of_orders = Order.objects.filter(complete=True).count()

    # Average Order Value
    average_order_value = Order.objects.filter(complete=True).aggregate(
        avg_order_value=Avg(F('orderitem__quantity') * F('orderitem__product__price'))
    )['avg_order_value'] or 0

    # Product Performance
    product_performance = (
        OrderItem.objects.values('product__name')
        .annotate(
            total_quantity=Sum('quantity'),
            total_sales=Sum(F('quantity') * F('product__price'))
        )
        .order_by('-total_sales')
    )

    # Revenue Trends
    revenue_trends = (
        Order.objects.filter(complete=True)
        .annotate(order_date=F('date_ordered__date'))
        .values('order_date')
        .annotate(daily_sales=Sum(F('orderitem__quantity') * F('orderitem__product__price')))
        .order_by('order_date')
    )

    context = {
        'total_sales': total_sales,
        'number_of_orders': number_of_orders,
        'average_order_value': average_order_value,
        'product_performance': product_performance,
        'revenue_trends': revenue_trends,
    }
    return render(request, 'core/sales_dashboard.html', context)

  
def login_view(request):
    error_message = None

    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')

        # Try to authenticate the user
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            # If authentication is successful, log the user in
            login(request, user)
            return redirect(index)  # Redirect to the home page after login
        else:
            # If authentication fails, set the error message
            error_message = "Invalid username or password."

    return render(request, 'core/login.html', {'error_message': error_message})

def signup_view(request):
     if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']

            user = User.objects.create_user(username=username, email=email, password=password)
            user.save()

            return redirect('login')
        else:
           print(form.errors)

     else:
       form = CustomUserCreationForm()
     return render(request, 'core/signup.html', {'form': form})

def customLogout(request):
    logout(request)
    # Optional: add logic here (e.g., a success message)
    return redirect('index')  # Redirect to home page or any other page after logging out.

# Define the CustomUserCreationForm directly in views.py
class CustomUserCreationForm(forms.Form):
    username = forms.CharField(max_length=150)
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput())
    confirm_password = forms.CharField(widget=forms.PasswordInput())

    def clean_username(self):
        username = self.cleaned_data['username']
        if len(username) < 4 or len(username) > 20:
            raise ValidationError("Username must be between 4-20 characters.")
        if not re.match(r'^[A-Za-z0-9_]+$', username):
            raise ValidationError("Username can only contain letters, numbers, and underscores.")
        return username

    def clean_password(self):
        password = self.cleaned_data['password']
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters long.")
        if not re.search(r'[A-Z]', password):
            raise ValidationError("Password must contain at least one uppercase letter.")
        if not re.search(r'[0-9]', password):
            raise ValidationError("Password must contain at least one number.")
        if not re.search(r'[\W_]', password):
            raise ValidationError("Password must contain at least one special character.")
        return password

    def clean_confirm_password(self):
        password = self.cleaned_data.get('password')
        confirm_password = self.cleaned_data.get('confirm_password')
        
        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords do not match.")
        return confirm_password

def adminDashboard(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden("You are not authorized to view this page.")
    return render(request, 'core/admin_dashboard.html')
