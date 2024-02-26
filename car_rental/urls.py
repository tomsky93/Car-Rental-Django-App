from django.urls import path
from . views import *
from . import views

urlpatterns = [
    path('',views.SearchVehiclesView.as_view(), name='index'),
    path('vehicles/', VehicleListView.as_view(), name='vehicles'),   
    path('location/<slug:slug>/', VehiclesInLocationView.as_view(), name='vehicles_in_location'),
    path('category/<slug:slug>/', VehiclesByCategoryView.as_view(), name='vehicles_by_category'),
    path('return/<uuid:rental_id>/', ReturnVehicleView.as_view(), name= 'return_form'),
    path('rental-summary/<str:pk>', RentalSummaryView.as_view(), name='rental_summary'),
    path('rental-list/', RentalListView.as_view(), name='rental_list'),
    path('vehicle/detail/<int:pk>', VehicleDetailView.as_view(), name='vehicle_details'),
    path('vehicle/edit/<int:pk>', UpdateVehicleView.as_view(), name= 'edit_vehicle'),
    path('reserve/<int:pk>', ReserveVehicleView.as_view(), name='reserve'),
    path('reservation_list/', ReservationListView.as_view(), name='reservation_list'),
    path('reservation-summary/<int:pk>', ReservationSummaryView.as_view(), name='reservation_summary'),
    path('rent/<int:pk>/', RentVehicleView.as_view(), name='reserve_and_rent'),
    path('manage-reservation/<int:pk>/', ManageReservationView.as_view(), name='manage_reservation'),
    path('update-reservation/<int:pk>/', UpdateReservationView.as_view(), name='update_reservation'),
    path('invoice/<str:rental_id>/', GenerateInvoiceView.as_view(), name='generate_invoice'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
] 
