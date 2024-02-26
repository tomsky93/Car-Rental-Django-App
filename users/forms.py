from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser
from django import forms
from django.core.validators import RegexValidator


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(label='Enter email')
    first_name = forms.CharField(label="First name", )
    last_name = forms.CharField(label= "Last name",)
    password1 = forms.CharField(label='Enter password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Confirm password', widget=forms.PasswordInput)
    phone_number = forms.CharField(label='Enter phone number',required= False, validators=[RegexValidator("^\d{9}$", message="Enter a valid contact number")])  
    
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'password1','password2','phone_number']
        
