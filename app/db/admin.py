from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Product

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'username', 'first_name', 'last_name', 'is_employee', 'is_staff')
    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'employee_code')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'first_name', 'last_name', 'password1', 'password2', 'is_employee'),
        }),
    )
    search_fields = ('email', 'username')
    ordering = ('email',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'country_of_origin', 'distance', 'price1', 'price2', 'price3')
    search_fields = ('name', 'country_of_origin')
    list_filter = ('country_of_origin',)
    readonly_fields = ('id',)
    ordering = ('name',)

    fieldsets = (
        (None, {
            'fields': (
                'name',
                'description',
                'picture',
                'country_of_origin',
                'distance',
                'price1',
                'price2',
                'price3',
            )
        }),
    )
