from django.contrib import admin
from .models import *


# 1. Define the Inline
# This tells Django: "Show PrescriptionItems inside the Prescription page"
class PrescriptionItemInline(admin.TabularInline):
    model = PrescriptionItem
    extra = 0  # Removes empty blank rows
    can_delete = True


# 2. Define the Main Admin
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'status', 'assigned_pharmacy', 'handled_by')
    list_filter = ('status', 'delivery_type')

    # Link the Inline here
    inlines = [PrescriptionItemInline]


# 3. Register Models
admin.site.register(Prescription, PrescriptionAdmin)
admin.site.register(Order)
admin.site.register(OrderHistory)
admin.site.register(Register)
admin.site.register(Pharmacy)
admin.site.register(Pharmacist)
admin.site.register(DeliveryAgent)
admin.site.register(Category)
admin.site.register(Medicine)
admin.site.register(Cart)
# admin.site.register(PrescriptionItem) # You don't need this separate if you use Inline