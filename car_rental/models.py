from django.db import models
from users.models import CustomUser
from datetime import date
import uuid
from django.urls import reverse
from django.utils.text import slugify
from django.core.cache import cache
# Create your models here.

class Brand(models.Model):
    name = models.CharField(null= False, max_length= 40, unique= True)
    
    def __str__(self):
        return self.name

class Location(models.Model):
    city = models.CharField(null=False, max_length=40, unique = True)
    slug = models.SlugField(max_length=50, unique=True, blank=True)

    def __str__(self):
        return self.city
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.city)
        super(Location, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('vehicles_in_location', kwargs={'slug': self.slug})
    
class VehicleCategory(models.Model):
    category = models.CharField(null=False, max_length=20, unique = True)
    slug = models.SlugField(max_length=25, unique=True, blank=True)
    
    class Meta:
        verbose_name_plural = "categories"
        ordering = ['category']

    def __str__(self):
        return self.category
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.category)
        super(VehicleCategory, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('vehicles_by_category', kwargs={'slug': self.slug})

class Vehicle(models.Model): 
    brand = models.ForeignKey(Brand, on_delete = models.CASCADE, null=False)
    model = models.CharField(max_length=50)
    registration_plate = models.CharField(max_length=10,default='0', null=False, unique= True) 
    VIN_number = models.CharField(max_length=17, null= False, unique=True) 
    mileage = models.PositiveIntegerField()
    cost = models.PositiveIntegerField(default= 500)
    availability = models.BooleanField(default= True)
    active = models.BooleanField(default= True)
    image = models.ImageField(upload_to="vehicles/", null=True)
    location = models.ForeignKey(Location, on_delete = models.CASCADE, null=True)
    category = models.ForeignKey(VehicleCategory, on_delete = models.CASCADE, null=True)

    def __str__(self):
        return (f'{self.brand} -  {self.model}')
    
    def get_absolute_url(self):
        return reverse('vehicle_details', kwargs={"pk": self.pk})
         
    def set_unavailable(self):
        self.availability = False
        self.save()

    def update_mileage_and_availability(self, mileage):
        self.mileage = mileage
        self.availability = True
        self.save()
    
class AvailabilityCalendar(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE)
    create_date = models.DateField(auto_now_add=True)
    start_date = models.DateField()
    end_date = models.DateField() #estimated return end date
    return_date = models.DateField(null=True,blank=True)  #real return date
    days = models.IntegerField(null=False,blank=False, default=0)
    type = models.CharField(max_length=11, choices=[('reservation', 'Reservation'), ('rental', 'Rental')])
    STATUS = [
         ('waiting', 'Waiting for confirmation'),
        ('confirmed', 'Reservation confirmed.'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
        ('rented', 'Rented'),
        ('returned', 'Returned'),
    ]
   
    status = models.CharField(
        max_length=25,
        choices= STATUS,
        blank=True,
        default='waiting',
        help_text='Status',
    )
    
    @classmethod 
    def check_availability(cls, vehicle, start_date, end_date, reservation_id=None):
        query = cls.objects.filter(
            vehicle=vehicle,
            end_date__gte=start_date,   
            start_date__lte=end_date, 
            status__in=['waiting', 'confirmed','rented']
        )
        
        if reservation_id:
            query = query.exclude(pk=reservation_id)  
        return not query.exists()  

class Reservation(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT)
    renter = models.ForeignKey(CustomUser, on_delete=models.PROTECT)
    pick_up_location = models.ForeignKey(Location, on_delete=models.PROTECT, related_name='reservations_pick_up_rentals', default = 1)
    return_location = models.ForeignKey(Location, on_delete=models.PROTECT, related_name='reservations_return_rentals', default = 1)
    total_cost = models.DecimalField(max_digits=8, decimal_places=2, null=True,)
    availability_calendar = models.ForeignKey(AvailabilityCalendar, on_delete=models.PROTECT, null=True, blank=True)
    
    class Meta:
        ordering = ['-pk']

    def __str__ (self):
        return f'{self.pk - self.vehicle - self.renter}'
    
    def get_absolute_url(self):
        return reverse('reservation_summary', kwargs={"pk": self.pk})
 
    @property  
    def can_rent_today(self): 
        return bool((self.availability_calendar.status == 'waiting' or self.availability_calendar.status == 'confirmed' )and date.today() == self.availability_calendar.start_date)
    
    def can_be_rented(self):
        return self.can_rent_today and self.vehicle.availability
    
    @property
    def can_be_changed(self):
        return bool(self.availability_calendar.status == 'waiting' or self.availability_calendar.status == 'confirmed' )
    
    @staticmethod
    def create_reservation(vehicle, renter, start_date, end_date, pick_up_location, return_location):
        days = (end_date - start_date).days + 1
        total_cost = days * vehicle.cost

        if AvailabilityCalendar.check_availability(vehicle, start_date, end_date):
            availability_calendar_entry = AvailabilityCalendar.objects.create(
                vehicle=vehicle,
                start_date=start_date,
                end_date=end_date,
                days=days,
                type='reservation'
            )
            reservation = Reservation.objects.create(
                vehicle=vehicle,
                renter=renter,
                total_cost=total_cost,
                pick_up_location = pick_up_location,
                return_location = return_location,
                availability_calendar=availability_calendar_entry
            )
            return reservation
        else:
            return None
        
    def update_dates_and_cost(self, start_date, end_date):
        self.availability_calendar.start_date = start_date
        self.availability_calendar.end_date = end_date
        self.availability_calendar.days = (end_date - start_date).days + 1
        self.availability_calendar.save()
        self.total_cost = self.availability_calendar.days * self.vehicle.cost
        self.save()

class Rental(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT)
    renter = models.ForeignKey(CustomUser, on_delete=models.PROTECT)
    pick_up_location = models.ForeignKey(Location, on_delete=models.PROTECT, related_name='pick_up_rentals', default = 1)
    return_location = models.ForeignKey(Location, on_delete=models.PROTECT, related_name='return_rentals', default = 1)
    mileage_start = models.PositiveIntegerField(null=True, blank=True)
    mileage_end = models.PositiveIntegerField(null=True, blank=True)
    total_cost = models.DecimalField(max_digits=8, decimal_places=2, null=True,) 
    availability_calendar = models.ForeignKey(AvailabilityCalendar, on_delete=models.PROTECT, null=True, blank=True)

    class Meta:
        ordering = ['-pk']

    def __str__(self):
        return (f'{self.vehicle} - {self.renter}')
    
    def get_absolute_url(self):
        return reverse('rental_summary', kwargs={"pk": self.pk})
    
    def check_rental_status(self):
        if self.availability_calendar.status == 'returned':
            return True
        return False
       
    def is_overdue(self):
        cache_key = f'{self.pk}_is_overdue'
        is_overdue = cache.get(cache_key)
        
        if is_overdue is None:
            is_overdue = self.availability_calendar.status == 'rented' and date.today() > self.availability_calendar.end_date
            cache.set(cache_key, is_overdue, timeout=3600)

        return is_overdue
        
    @property    
    def get_total_days(self):
        days = (date.today() - self.availability_calendar.start_date).days
        return days if days > 0 else 1

    @property  
    def price_per_day(self):
        return (self.total_cost / self.availability_calendar.days)
      
    def set_details_from_reservation(self, reservation, cleaned_data):
        self.vehicle = reservation.vehicle
        self.renter = reservation.renter
        self.mileage_start = reservation.vehicle.mileage
        self.start_date = cleaned_data['start_date']
        self.end_date = cleaned_data['end_date']
        self.days = (self.end_date - self.start_date).days
        self.total_cost = self.days * reservation.vehicle.cost
        self.availability_calendar_id = reservation.availability_calendar_id
        
    def rent(self):  
        self.availability_calendar.status = 'rented'
        self.availability_calendar.start_date = self.start_date
        self.availability_calendar.end_date = self.end_date
        self.availability_calendar.days = self.days
        self.availability_calendar.save()

        self.vehicle.availability = False
        self.vehicle.save()
        self.save()
    
    
    def calculate_total_cost(self):
        message = ""
        total_days = self.get_total_days
        total_cost = total_days * self.price_per_day
        if self.is_overdue():
            message = (f"Vehicle is returned with delay. Additional fees have been charged.")
        
        return total_days, total_cost, message
    
    def return_vehicle(self, return_date, end_mileage):   
        total_days, total_cost, message = self.calculate_total_cost()
        self.mileage_end = end_mileage
        self.total_cost = total_cost
        self.save()
       
        self.availability_calendar.days = total_days
        self.availability_calendar.return_date = return_date
        self.availability_calendar.status = 'returned'
        self.availability_calendar.save()

        self.vehicle.update_mileage_and_availability(end_mileage)

        self.vehicle.location = self.return_location
        self.vehicle.save()
        