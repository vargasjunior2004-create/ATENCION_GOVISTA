from django.contrib import admin
from .models import User, Plan, Sale, CashCount, Outflow, Backup


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'role', 'active')


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('id', 'code', 'label', 'type', 'speed', 'monthly',
                    'installation', 'active')


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('id', 'date', 'clientCode', 'clientName', 'plan',
                    'total', 'createdBy')


@admin.register(CashCount)
class CashCountAdmin(admin.ModelAdmin):
    list_display = ('id', 'date', 'total')


@admin.register(Outflow)
class OutflowAdmin(admin.ModelAdmin):
    list_display = ('id', 'date', 'personName', 'amount', 'concept')


@admin.register(Backup)
class BackupAdmin(admin.ModelAdmin):
    list_display = ('id', 'filename', 'backup_type', 'status', 'created_at',
                    'size', 'checksum')
    list_filter = ('backup_type', 'status')
