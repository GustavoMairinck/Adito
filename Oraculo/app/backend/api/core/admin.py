from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Contexto, Tenant, User


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)
    ordering = ('name',)


@admin.register(Contexto)
class ContextoAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'tenant', 'is_active', 'updated_at')
    list_filter = ('is_active', 'tenant')
    search_fields = ('name', 'slug')


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'tenant', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_active', 'tenant')
    search_fields = ('username', 'email')
    ordering = ('username',)
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Tenant', {'fields': ('tenant',)}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Tenant', {'fields': ('tenant',)}),
    )

