from django.db import models
from django.urls import reverse
from django.contrib.auth.models import AbstractUser
from .managers import UserManager
# Create your models here.

class CustomUser(AbstractUser):
    username = None
    email = models.EmailField(unique = True)
    phone_number = models.CharField(max_length= 12, blank= True, null=True, default=None)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ["first_name","last_name",]

    objects = UserManager()

    def __str__(self):
        return f'{self.first_name} {self.last_name}'

    