from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin
)
from django.conf import settings


class UserManager(BaseUserManager):
    def create_user(self, email, username, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required.")
        if not username:
            raise ValueError("Username is required.")
        
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, username, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(max_length=255, unique=True)
    username = models.CharField(max_length=150, unique=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    is_employee = models.BooleanField(default=False)
    employee_code = models.CharField(max_length=50, blank=True, null=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = 'email' 
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email


class Product(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    picture = models.ImageField(upload_to='products/', blank=True, null=True)
    country_of_origin = models.CharField(max_length=100)
    distance = models.PositiveIntegerField(default=0)
    
    price1 = models.DecimalField(max_digits=10, decimal_places=2)
    price2 = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    price3 = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)


    added_data = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    dodany_przez = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='added_products'
)

