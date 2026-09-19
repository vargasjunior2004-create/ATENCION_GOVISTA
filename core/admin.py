from django.contrib import admin
from .models import User, Plan, Promotion, Sale, Backup


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'role', 'active')


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('id', 'code', 'label', 'type', 'speed', 'monthly',
                    'installation', 'active')


@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'plan', 'apply_installation', 'apply_monthly',
                    'installation_price', 'monthly_price', 'start_date',
                    'end_date', 'active')
    list_filter = ('active', 'apply_installation', 'apply_monthly')


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('id', 'date', 'clientCode', 'clientName', 'plan',
                    'total', 'createdBy')


@admin.register(Backup)
class BackupAdmin(admin.ModelAdmin):
    list_display = ('id', 'filename', 'backup_type', 'status', 'created_at',
                    'size', 'checksum')
    list_filter = ('backup_type', 'status')
