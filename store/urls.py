from django.urls import path
from . import views


urlpatterns=[
    path('',views.home,name='home'),
    path('contact',views.contact,name='contact'),
    path('category/<slug:category_slug>',views.home,name='products_by_category'),
    path('about',views.about,name='about'),
    path('category/<slug:category_slug>/<slug:product_slug>',views.product,name='product_detail'),
    path('cart/add/<int:product_id>',views.add_cart,name='add_cart'),
    path('cart/',views.cart_detail,name='cart_detail'),
    path('cart/remove/<int:product_id>',views.cart_remove,name='cart_remove'),
    path('cart/remove/<int:product_id>',views.cart_remove_product,name='cart_remove_product'),
    path('thankyou/<int:order_id>',views.thanks_page,name='thanks_page'),
    path('accounts/create/',views.signupView,name='signup'),
    path('accounts/login/',views.signinView,name='signin'),
    path('accounts/logout/',views.signout,name='signout'),
    path('order_history/', views.orderHistory, name='order_history'),
    path('order/<int:order_id>', views.viewOrder, name='order_detail'),
    path('search/', views.searchProduct, name='search'),
    path('password-reset/', views.PasswordResetView.as_view(template_name='./password_reset.html'), name='password_reset'),
    path('password-reset/done/', views.PasswordResetDoneView.as_view(template_name='./password_done.html'), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', views.PasswordResetConfirmView.as_view(template_name='./password_reset_confirm.html'), name='password_reset_confirm'),
    path('password-reset-complete/', views.PasswordResetCompleteView.as_view(template_name='./password_reset_complete.html'), name='password_reset_complete'),
]