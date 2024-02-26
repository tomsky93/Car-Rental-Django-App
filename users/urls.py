from django.urls import path, include
from users import views as user_views
from django.contrib.auth import views as auth_views
app_name = "users"

urlpatterns = [
    path('', include('car_rental.urls')), 
    path('register/', user_views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name="users/login.html"), name ='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='index'), name='logout'),  
    path('profile/', user_views.profile, name='profile'),
]