from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Product, ShelfState


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
    list_display = (
        'name',
        'country_of_origin',
        'price1',
        'price2',
        'price3',
        'shelf_number',
        'telemetry_d1',
        'telemetry_d2',
        'telemetry_weight',
    )
    search_fields = ('name', 'country_of_origin')
    list_filter = ('country_of_origin', 'shelf_number')
    readonly_fields = ('id',)
    ordering = ('name',)

    fieldsets = (
        (None, {
            'fields': (
                'name',
                'description',
                'picture',
                'country_of_origin',
                'price1',
                'price2',
                'price3',
                'shelf_number',
            )
        }),
    )

    # helper do powiązania z ShelfState
    def _get_shelfstate(self, obj):
        if not obj.shelf_number:
            return None
        try:
            return ShelfState.objects.get(shelf=obj.shelf_number)
        except ShelfState.DoesNotExist:
            return None

    def telemetry_d1(self, obj):
        ss = self._get_shelfstate(obj)
        return ss.d1_mm if ss else None
    telemetry_d1.short_description = "d1 (mm)"

    def telemetry_d2(self, obj):
        ss = self._get_shelfstate(obj)
        return ss.d2_mm if ss else None
    telemetry_d2.short_description = "d2 (mm)"

    def telemetry_weight(self, obj):
        ss = self._get_shelfstate(obj)
        return ss.weight_g if ss else None
    telemetry_weight.short_description = "weight (g)"


@admin.register(ShelfState)
class ShelfStateAdmin(admin.ModelAdmin):
    list_display = ('shelf', 'd1_mm', 'd2_mm', 'weight_g', 'updated_at')
    ordering = ('shelf',)
