from django.shortcuts import render,get_object_or_404,redirect
import os
from .models import Category,Product,Cart,CartItem, Order, OrderItem,Review
from django.core.exceptions import ObjectDoesNotExist
import stripe
from django.conf import settings
from django.contrib.auth.models import User,Group
from .forms import SignUpForm
from django.contrib.auth import login,authenticate,logout
from django.contrib.auth.views import PasswordResetView,PasswordResetDoneView,PasswordResetConfirmView,PasswordResetCompleteView
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.core.mail import send_mail
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from python_http_client.exceptions import HTTPError


def home(request,category_slug=None):
    products=None
    particular_category=None
    if category_slug!= None:
        particular_category= get_object_or_404(Category,slug=category_slug)
        products=Product.objects.filter(category=particular_category,available=True)
    else:
        products=Product.objects.all().filter(available=True)
    return render(request,'home.html',{'category':particular_category,'products':products})
    

def about(request):
    return render(request,'about.html')

def product(request,category_slug,product_slug):
    try:
        product=Product.objects.get(category__slug=category_slug,slug=product_slug)
    except Exception as e:
        raise e
    if request.method == 'POST' and request.user.is_authenticated and request.POST['content'].strip() != '':
        Review.objects.create(  product=product,
                                user=request.user,
                                content=request.POST['content'])

    reviews = Review.objects.filter(product=product)

    return render(request, 'product.html', {'product': product, 'reviews': reviews})






def _cart_id(request):
    cart=request.session.session_key
    if not cart:
        cart=request.session.create()

    return cart


def add_cart(request,product_id):
    product=Product.objects.get(id=product_id)
    try:
        cart=Cart.objects.get(cart_id=_cart_id(request))
    except Cart.DoesNotExist:
        cart=Cart.objects.create(
            cart_id=_cart_id(request)
        )

        cart.save()

    try:
        cart_item=CartItem.objects.get(product=product,cart=cart)
        if cart_item.quantity <cart_item.product.stock:
            cart_item.quantity+=1
        cart_item.save()

    except CartItem.DoesNotExist:
        cart_item=CartItem.objects.create(
            product=product,
            quantity=1,
            cart=cart,
        )

        cart_item.save()

    return redirect('cart_detail')

def cart_detail(request,total=0,counter=0,cart_item=None):
    

    try:
        cart=Cart.objects.get(cart_id=_cart_id(request))
        cart_items=CartItem.objects.filter(cart=cart,active=True)

        for cart_item in cart_items:
            total+=(cart_item.product.price*cart_item.quantity)
            counter+=cart_item.quantity

    except ObjectDoesNotExist:
        pass

    stripe.api_key=settings.STRIPE_SECRET_KEY
    stripe_total=int(total*100)
    description='New order payment processing'
    data_key=settings.STRIPE_PUBLISHABLE_KEY
    if request.method=='POST':
        try:
            token=request.POST['stripeToken']
            email=request.POST['stripeEmail']
            billingName = request.POST['stripeBillingName']
            billingAddress1 = request.POST['stripeBillingAddressLine1']
            billingCity = request.POST['stripeBillingAddressCity']
            billingPostcode = request.POST['stripeBillingAddressZip']
            billingCountry = request.POST['stripeBillingAddressCountry']
            shippingName = request.POST['stripeShippingName']
            shippingAddress1 = request.POST['stripeShippingAddressLine1']
            shippingCity = request.POST['stripeShippingAddressCity']
            shippingPostcode = request.POST['stripeShippingAddressZip']
            shippingCountry = request.POST['stripeShippingAddressCountryCode']
            customer=stripe.Customer.create(
                email=email,
                source=token
            )
            charge=stripe.Charge.create(
                amount=stripe_total,
                currency='usd',
                description=description,
                customer=customer.id
                )

            ##creating the Order object
            try:
                order_details=Order.objects.create(
                    token=token,
                    total=total,
                    emailAddress=email,
                    billingName=billingName,
                    billingAddress1=billingAddress1,
                    billingCity=billingCity,
                    billingPostcode=billingPostcode,
                    billingCountry=billingCountry,
                    shippingName=shippingName,
                    shippingAddress1=shippingAddress1,
                    shippingCity=shippingCity,
                    shippingPostcode=shippingPostcode,
                    shippingCountry=shippingCountry
                )
                order_details.save()
                for order_item in cart_items:
                    or_item = OrderItem.objects.create(
                    product=order_item.product.name,
                    quantity=order_item.quantity,
                    price=order_item.product.price,
                    order=order_details
                )
                    or_item.save()


                    ##reduce stock in database
                    products = Product.objects.get(id=order_item.product.id)
                    products.stock = int(order_item.product.stock - order_item.quantity)
                    products.save()
                    order_item.delete()

                    print('the order has been created')
                try:
                    sendEmail(order_details.id)
                    print('email has been sent')
                except IOError as e:
                    return e
                     
                return redirect('thanks_page',order_details.id)
            except ObjectDoesNotExist as e:
                return False,e

        except stripe.error.CardError as e:
            return False,e


    return render(request,'cart.html',dict(cart_items=cart_items,total=total,counter=counter,data_key=data_key,stripe_total=stripe_total,description=description))
    

def cart_remove(request,product_id):
    cart=Cart.objects.get(cart_id=_cart_id(request))
    product=get_object_or_404(Product,id=product_id)
    cart_item=CartItem.objects.get(product=product,cart=cart)
    if cart_item.quantity > 1:
        cart_item.quantity -= 1
        cart_item.save()

    else:
        cart_item.delete()

    return redirect('cart_detail')

def cart_remove_product(request,product_id):
    cart=Cart.objects.get(cart_id=_cart_id(request))
    product=get_object_or_404(Product,id=product_id)
    cart_item=CartItem.objects.get(product=product,cart=cart)
    cart_item.delete()
    return redirect('cart_detail')

def thanks_page(request, order_id):
    if order_id:
        customer_order = get_object_or_404(Order, id=order_id)
    return render(request, 'thankyou.html', {'customer_order': customer_order})


def signupView(request):
    if request.method=='POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            form.save()
            email=form.cleaned_data.get('email')
            username=form.cleaned_data.get('username')
            signup_user=User.objects.get(username=username)
            customer_group=Group.objects.get(name='Customer')
            customer_group.user_set.add(signup_user)
            
    else:
        form =SignUpForm()
    return render(request,'signup.html',{'form':form})

def signinView(request):
    if request.method=='POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            username=request.POST['username']
            password=request.POST['password']
            
            user=authenticate(username=username,password=password)
            #above statement will return a user object
            if user is not None:
                login(request,user)
                return redirect('home')
            else:
                redirect('signup')
            
    else:
        form =AuthenticationForm()
    return render(request,'signin.html',{'form':form})

def signout(request):
    logout(request)
    return redirect('signin')


@login_required(redirect_field_name='next', login_url='signin')
def orderHistory(request):
    if request.user.is_authenticated:
        order_details = Order.objects.filter(emailAddress=request.user.email)
        print(request.user.email)
        print(order_details)
    return render(request, 'orders_list.html', {'order_details': order_details})


@login_required(redirect_field_name='next', login_url='signin')
def viewOrder(request, order_id):
    if request.user.is_authenticated:
        email = str(request.user.email)
        order = Order.objects.get(id=order_id, emailAddress=email)
        order_items = OrderItem.objects.filter(order=order)
    return render(request, 'order_detail.html', {'order': order, 'order_items': order_items})


def searchProduct(request):
    products=Product.objects.filter(name__contains=request.GET['name'])
    return render(request,'home.html',{'products':products})

def sendEmail(order_id):
    transaction=Order.objects.get(id=order_id)
    order_items=OrderItem.objects.filter(order=transaction)
   
    ######sending email 
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.ehlo()
    server.starttls()
    server.ehlo()  
    FROM = settings.EMAIL_HOST_USER
    PASSWORD = settings.EMAIL_HOST_PASSWORD
   
    # print('insendemail')
    # message = Mail(
    # from_email=settings.EMAIL_HOST_USER,
    # to_emails=['{}'.format(transaction.emailAddress)],
    # subject=' Shopper - New Order #{}'.format(transaction.id),
    # html_content='<strong>Hi, we have received your order. We will deliver your product within 5 business days. Happy Shopping!!</strong>')
    # #sending email
    # sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
    
    # try:
    #     response = sg.send(message)
    # except HTTPError as e:
    #     print(e.to_dict)

#     send_mail(
#     'Subject here',
#     'Here is the message.',
#     settings.EMAIL_HOST_USER,
#     ['{}'.format(transaction.emailAddress)],
#     fail_silently=False,
# )

    
    TOADDR = ['{}'.format(transaction.emailAddress)]
    SUBJECT = ' Shopper - New Order #{}'.format(transaction.id)
    TEXT = "Hi, we have received your order. We will deliver your product within 5 business days. Happy Shopping!!"

    message = MIMEMultipart()
    message['From'] = " Shopper <{}>".format(FROM)
    message['To'] = ', '.join(TOADDR)
    
    message['Subject'] = SUBJECT
    message.attach(MIMEText(TEXT))

    MSG = message.as_string()

    #Join reciever with CC
    FINAL_TO = TOADDR
    server.sendmail(FROM, FINAL_TO, MSG)

   
def about(request):
    return render(request,'about.html')

def contact(request):
    return render(request,'contact.html')