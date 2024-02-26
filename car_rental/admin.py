from django.contrib import admin
from .models import Brand, Location, Vehicle, VehicleCategory

# Register your models here.

class VehiclesAdmin(admin.ModelAdmin):
    list_display = ['brand', 'model','mileage','VIN_number', 'availability']

admin.site.register(Vehicle, VehiclesAdmin)
admin.site.register(Brand)
admin.site.register(Location)
admin.site.register(VehicleCategory)
