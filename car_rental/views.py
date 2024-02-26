from django.shortcuts import render, redirect, get_object_or_404
from .models import Location, Vehicle, VehicleCategory, Rental, Reservation, AvailabilityCalendar
from django.views import View
from django.contrib import messages
from django.views.generic import CreateView, ListView, DetailView, UpdateView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin, AccessMixin
from django.utils import timezone
from .forms import ReserveForm, RentalForm, ReturnForm, VehicleQueryForm
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Count, F, Sum
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from datetime import date, timedelta
from django.core.cache import cache

class StaffRequiredMixin(AccessMixin):
       def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.is_staff:
            messages.error(request, 'No access: personnel authorization required.')
            return redirect('index') 
        return super().dispatch(request, *args, **kwargs)

class UpdateVehicleView(StaffRequiredMixin, UpdateView):  
    model = Vehicle
    success_url = '/'
    fields = ['cost']
    template_name = 'car_rental/staff/edit_vehicle.html'
    context_object_name = 'vehicle'

class VehicleListView(ListView):  
    model = Vehicle
    template_name = 'car_rental/index.html'  
    context_object_name = 'vehicles'

    def get_template_names(self):
        return ['car_rental/staff/vehicle_list.html'] if self.request.user.is_staff else [self.template_name]

    def get_queryset(self):
        return  Vehicle.objects.select_related() if self.request.user.is_staff else Vehicle.objects.filter(active=True)

class VehiclesInLocationView(ListView):
    model = Vehicle
    template_name = 'car_rental/vehicles_list.html'
    context_object_name = 'vehicles'

    def get_queryset(self):
        location_slug = self.kwargs['slug']
        location = Location.objects.get(slug=location_slug)
        return Vehicle.objects.filter(location=location)

class VehiclesByCategoryView(ListView):
    model = Vehicle
    template_name = 'car_rental/vehicles_list.html'
    context_object_name = 'vehicles'

    def get_queryset(self):
        category_slug = self.kwargs['slug']
        category = VehicleCategory.objects.get(slug=category_slug)
        return Vehicle.objects.filter(category=category)

class VehicleDetailView(DetailView): 
    model = Vehicle
    template_name = 'car_rental/vehicle_detail.html'
    context_object_name = 'vehicle'

    def get_template_names(self):
        return ['car_rental/staff/vehicle_detail.html'] if self.request.user.is_staff else [self.template_name]
    
    def get_context_data(self, **kwargs):
        
        context = super(VehicleDetailView, self).get_context_data(**kwargs)
        vehicle_id = self.kwargs.get('pk')
       
        if self.request.user.is_staff:
            
            reservations = Reservation.objects.filter(vehicle_id=vehicle_id)
            rentals = Rental.objects.filter(vehicle=vehicle_id)

            reservations_filtered = [
                reservation for reservation in reservations
                if not any(
                    rental.availability_calendar.start_date == reservation.availability_calendar.start_date and
                    rental.availability_calendar.end_date == reservation.availability_calendar.end_date
                    for rental in rentals
                )
            ]

            reservations_json = [
                {
                    'title': f'Reservation {reservation.renter}',
                    'start': reservation.availability_calendar.start_date.isoformat(),
                     'end': (reservation.availability_calendar.end_date + timedelta(days=1)).isoformat(),
                    'color': 'gray' if reservation.availability_calendar.status in ['expired', 'cancelled'] else 'coralblue',
                }
                for reservation in reservations_filtered
            ]

            rentals_json = [
                {
                    'title': f'Rent {rental.renter}',
                    'start': rental.availability_calendar.start_date.isoformat(),
                    'end': (rental.availability_calendar.end_date + timedelta(days=1)).isoformat(),
                    'color': 'green',
                }
                for rental in rentals
            ]

            events_json = reservations_json + rentals_json

            context['events_json'] = events_json
            
        return context
 
class RentalSummaryView(LoginRequiredMixin,UserPassesTestMixin, View):  
    model = Rental    
    login_url = '/login'
    template_name = 'car_rental/rental_summary.html'
    
    def test_func(self): 
        rental = get_object_or_404(Rental, pk=self.kwargs['pk'])
        return  rental.renter == self.request.user or self.request.user.is_staff
    
    def get(self,request,pk):
        rental = get_object_or_404(Rental, pk=pk)

        if not self.test_func():
            raise PermissionDenied

        return render(request, self.template_name, {'rental': rental})

class RentalListView(LoginRequiredMixin, ListView): 
    model = Rental
    template_name = 'car_rental/rental_list.html'
    context_object_name = 'rentals'
    paginate_by = 10

    def get_template_names(self):
        return ['car_rental/staff/rental_list.html'] if self.request.user.is_staff else [self.template_name]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Rental.objects.select_related('availability_calendar').all()
        else:
            return Rental.objects.select_related('availability_calendar').filter(renter=user)

    def get_context_data(self, **kwargs):
        context = super(RentalListView, self).get_context_data(**kwargs)
        queryset = self.get_queryset()
        paginator = Paginator(queryset, self.paginate_by)
        page = self.request.GET.get('page')

        try:
            rentals = paginator.page(page)
        except PageNotAnInteger:
            rentals = paginator.page(1)
        except EmptyPage:
            rentals = paginator.page(paginator.num_pages)

        context['rentals'] = rentals
        return context

class ReservationListView(LoginRequiredMixin, View):
    template_name = 'car_rental/reservation_list.html'
    paginate_by = 10

    def get_template_names(self):
        return ['car_rental/staff/reservation_list.html'] if self.request.user.is_staff else [self.template_name]

    def get(self, request, *args, **kwargs):
        queryset = Reservation.objects.select_related()

        if not self.request.user.is_staff:
            queryset = queryset.filter(renter=self.request.user)

        reservations = AvailabilityCalendar.objects.filter(
            reservation__in=queryset,
            start_date__lt=timezone.now(),
            status__in=['waiting', 'confirmed']
        ).update(status='expired')

        paginator = Paginator(queryset, self.paginate_by)
        page = self.request.GET.get('page')

        try:
            reservations = paginator.page(page)
        except PageNotAnInteger:
            reservations = paginator.page(1)
        except EmptyPage:
            reservations = paginator.page(paginator.num_pages)

        context = {'reservations': reservations}
        return render(request, self.get_template_names(), context)
    
class ReservationMixin(View, UserPassesTestMixin):  
    model = Reservation
    login_url = '/login'
    redirect_field_name = '/index'

    def test_func(self):
        reservation = get_object_or_404(Reservation, pk=self.kwargs['pk'])
        return self.request.user.is_staff or reservation.renter == self.request.user

class ManageReservationView(ReservationMixin,LoginRequiredMixin, View): 
    def get(self, request, pk):
        reservation = get_object_or_404(Reservation, pk=pk)
        return render(request, 'car_rental/reservation_summary.html', {'reservation': reservation})

    def post(self, request, pk):
        reservation = get_object_or_404(Reservation, pk=pk)

        status_mapping = {
            'waiting': 'confirmed',
            'confirmed': 'cancelled',
        }

        new_status = status_mapping.get(reservation.availability_calendar.status)

        if new_status:
            reservation.availability_calendar.status = new_status
            reservation.availability_calendar.save()
            messages.success(request, f'Reservation {new_status} successfully.')
        else:
            messages.error(request, 'Reservation cannot be confirmed or cancelled.')

        return redirect('reservation_summary', pk=pk)
    
class ReservationSummaryView(ReservationMixin, View):  
    template_name = 'car_rental/reservation_summary.html'
  
    def get(self, request, pk):
        reservation = get_object_or_404(Reservation, pk=pk)
        if not self.test_func():
            raise PermissionDenied
        return render(request, self.template_name, {'reservation': reservation})

class ReserveVehicleView(LoginRequiredMixin, CreateView):
    model = Reservation
    form_class = ReserveForm
    template_name = 'car_rental/reservation_form.html'
    context_object_name = 'reservation'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get('pk')
        vehicle = get_object_or_404(Vehicle, pk=pk)
        context['form'] = self.form_class(initial={'vehicle_id': pk})
        context['vehicle'] = vehicle
        return context

    def form_valid(self, form):
        pk = self.kwargs.get('pk')
        vehicle = get_object_or_404(Vehicle, pk=pk)
        renter = self.request.user
        start_date = form.cleaned_data['start_date']
        end_date = form.cleaned_data['end_date']
        pick_up_location = vehicle.location
        return_location = form.cleaned_data['return_location']

        reservation = Reservation.create_reservation(
            vehicle, renter, start_date, end_date, pick_up_location, return_location
        )

        if reservation:
            messages.success(self.request, "Your reservation has been sent.")
            return redirect('reservation_summary', pk=reservation.pk)
        else:
            messages.warning(self.request, "The selected date conflicts with another booking. Please select another date.")
            return super().form_invalid(form)

class UpdateReservationView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):   
    def test_func(self):
        reservation = get_object_or_404(Reservation, pk=self.kwargs['pk'])
        return self.request.user.is_staff or reservation.renter == self.request.user

    form_class = ReserveForm  
    template_name = 'car_rental/reservation_form.html'
       
    def get(self, request, pk):
        reservation = get_object_or_404(Reservation, pk=pk)
        if not reservation.can_be_changed:
            messages.error(request, "This reservation cannot be changed at this time.")
            return redirect('reservation_list')
        
        initial_data = {
        'start_date': reservation.availability_calendar.start_date,
        'end_date': reservation.availability_calendar.end_date,
        'vehicle_id': reservation.vehicle_id, 
            }

        form = self.form_class(initial=initial_data)
        return render(request, self.template_name, {'form': form, 'reservation': reservation})

    def post(self, request, pk):
        reservation = get_object_or_404(Reservation, pk=pk)
        form = self.form_class(request.POST, initial={'vehicle_id': reservation.vehicle_id})

        if form.is_valid():
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            if AvailabilityCalendar.check_availability(
                reservation.vehicle, start_date, end_date, reservation.availability_calendar.pk
            ):
                reservation.update_dates_and_cost(start_date, end_date)
                reservation.save()  
                messages.success(request, "Rental dates and cost have been updated successfully.")
                return redirect('reservation_summary', pk=reservation.pk)
            else:
                messages.error(request, "Vehicle is not available for the selected dates.")
                return render(request, self.template_name, {'form': form, 'reservation': reservation})
        
        messages.warning(request, "There was a problem with your submission. Please check your data.")
        return render(request, self.template_name, {'form': form, 'reservation': reservation})
     
class RentVehicleView(StaffRequiredMixin, View): 
    template_name = 'car_rental/staff/rental_form.html'
    form_class = RentalForm

    def get(self, request, pk):
        reservation, availability_calendar = self.get_reservation_details(pk)

        if not reservation.can_be_rented():
            return self.handle_cannot_rent(request, availability_calendar)

        return render(request, self.template_name, {'form': self.initialize_rental_form(reservation), 'reservation': reservation})

    def post(self, request, pk): 
        reservation = get_object_or_404(Reservation, pk=pk)
        form = RentalForm(request.POST)

        if form.is_valid():
            rental = self.prepare_rental(form, reservation)
            if AvailabilityCalendar.check_availability(reservation.vehicle, rental.start_date, rental.end_date, reservation_id=reservation.availability_calendar_id):
                self.handle_rent(reservation.availability_calendar, reservation.vehicle, rental)
                return redirect('rental_summary', pk=rental.pk)
            else:
                return self.handle_conflicting_booking(form)

        return self.form_invalid(form)

    def form_invalid(self, form):
        pk = self.kwargs.get('pk')  
        reservation, availability_calendar = self.get_reservation_details(pk)

        return render(self.request, self.template_name, {
            'form': self.initialize_rental_form(reservation),
            'reservation': reservation
        })

    def get_reservation_details(self, pk):  
        reservation = get_object_or_404(Reservation, pk=pk)  
        return reservation, reservation.availability_calendar

    def handle_vehicle_unavailable(self, request, vehicle): 
        messages.warning(request, f"{vehicle.brand}  {vehicle.model} is actually rented.")
        return redirect('reservation_list')

    def handle_conflicting_booking(self, form):  
        messages.warning(self.request, "The selected date conflicts with another booking. Please select another date.")
        return self.form_invalid(form)

    def handle_cannot_rent(self, request, availability_calendar): 
        messages.warning(request, f"You can't rent using this reservation. Pick up date is {availability_calendar.start_date}. Modify reservation or make a new one.")
        return redirect('reservation_list')

    def initialize_rental_form(self, reservation):
        return RentalForm(initial={
            'vehicle': reservation.vehicle,
            'renter': reservation.renter,
            'pick_up_location': reservation.pick_up_location,
            'return_location': reservation.return_location,
            'mileage_start': reservation.vehicle.mileage,
            'start_date': reservation.availability_calendar.start_date,
            'start_date_display': reservation.availability_calendar.start_date,
            'end_date': reservation.availability_calendar.end_date,
            'total_cost': reservation.total_cost,
            'days': reservation.availability_calendar.days,
        })

    def prepare_rental(self, form, reservation):
        rental = form.save(commit=False)
        rental.set_details_from_reservation(reservation, form.cleaned_data)
        return rental
    
    def handle_rent(self, availability_calendar, vehicle, rental):
        rental.rent()   
   
class ReturnVehicleView(StaffRequiredMixin, View):
    
    def handle_rental_return(self, rental):
        total_days, total_cost, message = rental.calculate_total_cost()
        messages.warning(self.request,message)
        return total_days, total_cost

    def get(self, request, rental_id):
        rental = get_object_or_404(Rental, id=rental_id)
        if rental.check_rental_status():
            messages.warning(request, "Vehicle has already been returned")
            return redirect('rental_list')
        total_days, total_cost = self.handle_rental_return(rental)
        form = ReturnForm(instance=rental)
        context = {
        'form': form,
        'rental': rental,
        'total_days': total_days,
        'total_cost': total_cost,
        }
        return render(request, 'car_rental/staff/return_form.html', context)

    def post(self, request, rental_id):
        rental = get_object_or_404(Rental, id=rental_id)
        form = ReturnForm(request.POST, instance=rental)
        if form.is_valid():
            rental.return_vehicle(date.today(), form.cleaned_data['mileage_end'])
            self.handle_rental_return(rental)
            return redirect('rental_list')
        return render(request, 'car_rental/staff/return_form.html', {'form': form, 'rental': rental})

class SearchVehiclesView(View):
    form_class = VehicleQueryForm
    template_name = 'car_rental/index.html'
    success_template_name = 'car_rental/vehicles_list.html'

    def get(self, request, *args, **kwargs):
        form = self.form_class()
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if form.is_valid():
            location = form.cleaned_data['location']
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']

            available_vehicles = Vehicle.objects.filter(location=location, availability=True)

            overlapping_bookings = AvailabilityCalendar.objects.filter(
                Q(start_date__lt=end_date, end_date__gt=start_date) |
                Q(start_date__gte=start_date, start_date__lt=end_date),
                vehicle__in=available_vehicles
            ).distinct()

            for booking in overlapping_bookings:
                if booking.vehicle.availability:
                    continue
                available_vehicles = available_vehicles.exclude(id=booking.vehicle.id)

            return render(request, self.success_template_name, {'vehicles': available_vehicles})

        return render(request, self.template_name, {'form': form})
    
class GenerateInvoiceView(UserPassesTestMixin, View):
    def test_func(self):
        self.rental = get_object_or_404(Rental, pk=self.kwargs['rental_id'])
        return self.rental.renter == self.request.user or self.request.user.is_staff

    def get(self, request, *args, **kwargs):  
        rent = self.rental
        
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'inline'

        p = canvas.Canvas(response, pagesize=letter)
        width, height = letter 
        
        theme_color = colors.HexColor("#03A64A")
     
        p.setFont("Helvetica-Bold", 24)
        p.setFillColor(colors.black)
        p.drawString(30, height - 60, "Car Rental")

      
        p.setStrokeColor(theme_color)
        p.setFillColor(theme_color)
        p.rect(0, height - 65, width, 5, fill=True, stroke=False)

        y_position = height - 80  

        p.setFont("Helvetica", 12)
        p.setFillColor(colors.black)

        p.setFont("Helvetica", 12)

        y_position -= 40
        p.drawString(30, y_position, f"Invoice Number: {rent.pk}")
        y_position -= 20
        p.drawString(30, y_position, f"Invoice Date: {rent.availability_calendar.return_date.strftime('%d-%m-%Y')}")
        y_position -= 20
        p.drawString(30, y_position, f"Customer: {rent.renter}")
        y_position -= 20
        p.drawString(30, y_position, f"Vehicle: {rent.vehicle}")
        y_position -= 20
        p.drawString(30, y_position, f"Rental Period: {rent.availability_calendar.start_date.strftime('%d-%m-%Y')} to {rent.availability_calendar.end_date.strftime('%d-%m-%Y')}")
        y_position -= 20
        p.drawString(30, y_position, f"Total Days: {rent.availability_calendar.days}")
        y_position -= 20
        p.drawString(30, y_position, f"Payment Method: Card")

        y_position -= 30
        p.setFont("Helvetica-Bold", 14)
        p.drawString(30, y_position, f"Total Cost: {rent.total_cost} €")
       
        p.setFillColor(theme_color)
        p.rect(0, 15, width, 20, fill=True, stroke=False)

        p.showPage()
        p.save()
       
        return response

class DashboardView(StaffRequiredMixin, TemplateView):   
    template_name = 'car_rental/staff/dashboard.html'

    def get_cached_data(self, key, query_function, timeout=300):      
        data = cache.get(key)
        if data is None:
            data = query_function()
            cache.set(key, data, timeout)
        return data

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        current_date = date.today()

        def available_vehicles_query():
            return Vehicle.objects.filter(availability=True, active=True).count()

        def rented_vehicles_query():
            return AvailabilityCalendar.objects.filter(
            status='rented'
            ).count()

        def pending_reservations_query():
            return AvailabilityCalendar.objects.filter(status='waiting').count()
            
        def vehicles_per_location_query():
            return Vehicle.objects.values(city=F('location__city')).annotate(total=Count('location')).order_by('city')
        
        def vehicles_awaiting_return_query():
            return AvailabilityCalendar.objects.filter(
                status='rented',
                return_date__isnull=True
            ).count()

        def overdue_rentals_query(current_date=current_date):
            return AvailabilityCalendar.objects.filter(
            Q(status='rented') & 
            Q(end_date__lt=current_date)
            ).count()

        def today_earnings_query(current_date=current_date):
            today_earnings = Rental.objects.filter(
                availability_calendar__return_date=current_date,
                availability_calendar__status='returned'
            ).aggregate(Sum('total_cost'))
            
            today_earnings_value = today_earnings.get('total_cost__sum') or 0
            return today_earnings_value

        def today_reservations_query(current_date=current_date):
            return AvailabilityCalendar.objects.filter(
            Q(type='reservation',
              create_date=current_date)
            ).count()
        
        def today_rentals_query(current_date=current_date):
             return AvailabilityCalendar.objects.filter(
            Q(status='rented',
              start_date=current_date)
            ).count()
            
        def monthly_earnings_query(current_date=current_date):
            monthly_earnings = Rental.objects.filter(
                Q(availability_calendar__status='returned') &
                (
                    Q(availability_calendar__start_date__year=current_date.year, availability_calendar__start_date__month=current_date.month) |
                    Q(availability_calendar__return_date__year=current_date.year, availability_calendar__return_date__month=current_date.month)
                )
            ).aggregate(Sum('total_cost'))
            
            monthly_earnings_value = monthly_earnings.get('total_cost__sum') or 0
            return monthly_earnings_value
    
              
        def monthly_rentals_query(current_date=current_date):
            monthly_rentals = AvailabilityCalendar.objects.filter(
                Q(status__in=['rented', 'returned']) &
                (
                    Q(start_date__year=current_date.year, start_date__month=current_date.month) |
                    Q(return_date__year=current_date.year, return_date__month=current_date.month)
                )
            ).count()
            
            return monthly_rentals
        
        def latest_rentals_query():
            return Rental.objects.select_related()[:10]

        def latest_reservations_query():
            return Reservation.objects.select_related()[:10]

        
        query_mappings = {
             'available_vehicles': (available_vehicles_query, 300),
             'rented_vehicles' : (rented_vehicles_query),
             'pending_reservations' : (pending_reservations_query),
             'today_earnings_value' : (today_earnings_query,900),
             'today_rentals' : (today_rentals_query,900),
             'today_reservations' : (today_reservations_query,900),
             'monthly_rentals' : (monthly_rentals_query,1800),
             'monthly_earnings' : (monthly_earnings_query, 1800),
             'vehicles_per_location' : (vehicles_per_location_query, 900),
             'vehicles_awaiting_return': (vehicles_awaiting_return_query),
             'overdue_rentals' : (overdue_rentals_query,3600),
             'latest_rentals' : (latest_rentals_query),
             'latest_reservations' : (latest_reservations_query)
        }

        for key, value in query_mappings.items():
            if isinstance(value, tuple):
                query_function, timeout = value
            else:
                query_function = value
                timeout = 300  

            context[key] = self.get_cached_data(key, query_function, timeout)
            context['date'] = current_date

        return context