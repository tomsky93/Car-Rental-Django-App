from django import forms
from .models import Rental, Reservation, Location, Vehicle
from datetime import date
from django.utils import timezone
from datetime import timedelta
from django.core.exceptions import ValidationError
from django.urls import reverse

class ReserveForm(forms.ModelForm):
    pick_up_location_name = forms.CharField(label='Pick Up Location', disabled=True, required=None)
    pick_up_location = forms.CharField(widget=forms.HiddenInput())
    start_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    end_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
 
    class Meta:
        model = Reservation
        fields = ['return_location', 'start_date', 'end_date']
     
    def __init__(self, *args, **kwargs):
        super(ReserveForm, self).__init__(*args, **kwargs)
        self.fields['start_date'].initial = date.today()
        self.fields['end_date'].initial = date.today()
        start_date = self.initial.get('start_date', timezone.localtime(timezone.now()).date())
        min_end_date = start_date + timedelta(days=1)
        self.fields['start_date'].widget.attrs['min'] = start_date.isoformat()
        self.fields['end_date'].widget.attrs['min'] = min_end_date.isoformat()
        vehicle_id = kwargs['initial'].get('vehicle_id')
       
        if 'initial' in kwargs:
            vehicle_id = kwargs['initial'].get('vehicle_id')
            if vehicle_id:
                vehicle = Vehicle.objects.get(id=vehicle_id)
                self.fields['pick_up_location'].initial = vehicle.location.pk
                self.fields['pick_up_location_name'].initial = vehicle.location.city
                self.fields['return_location'].initial = vehicle.location.pk
        
        self.order_fields(('pick_up_location_name', 'return_location', 'start_date', 'end_date'))
                
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        current_date = timezone.now().date()

        if start_date < current_date or end_date < current_date:
            raise ValidationError("Dates must not be in the past.")
        
        if start_date >= end_date:
            raise ValidationError("End date must be after start date.")

        return cleaned_data

class RentalForm(forms.ModelForm): 
    start_date_display = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'disabled': 'disabled'}),
        label="Start date",
        required=False)
    start_date = forms.DateField(widget=forms.HiddenInput())
    end_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    
    class Meta:
        model = Rental
        fields = ['return_location']
      
    def __init__(self, *args, **kwargs):
        super(RentalForm, self).__init__(*args, **kwargs)
        self.fields['return_location'].label = "Return location"
        start_date = self.initial.get('start_date', timezone.localtime(timezone.now()).date())
        min_end_date = start_date + timedelta(days=1)
        self.fields['end_date'].widget.attrs['min'] = min_end_date.isoformat()
      
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        if start_date >= end_date: 
            raise ValidationError("End date must be after pick up date.")

        return cleaned_data
    
class ReturnForm(forms.ModelForm):  
    class Meta:
        model = Rental
        fields = ['mileage_end']

    def __init__(self, *args, **kwargs):
        super(ReturnForm, self).__init__(*args, **kwargs)
        self.fields['mileage_end'].label = "Mileage"

    def clean_mileage(self):
        mileage = self.cleaned_data['mileage_end']
        vehicle = self.instance.vehicle
        
        if mileage <= vehicle.mileage:
            raise forms.ValidationError("Mileage end must be greater than current vehicle mileage.")
        return mileage

    def clean(self):
        cleaned_data = super().clean()
        self.clean_mileage()
        return cleaned_data


class VehicleQueryForm(forms.Form):  
    location = forms.ModelChoiceField(
        queryset=Location.objects.all(),
        to_field_name="city",
        empty_label="Location"
    )
    start_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    end_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))

    def __init__(self, *args, **kwargs):
        super(VehicleQueryForm, self).__init__(*args, **kwargs)
        start_date = self.initial.get('start_date', timezone.localtime(timezone.now()).date())
        self.fields['start_date'].widget.attrs['min'] = start_date.isoformat()
        min_end_date = start_date + timedelta(days=1)
        self.fields['end_date'].widget.attrs['min'] = min_end_date.isoformat()

    def get_absolute_url(self):
        return reverse('search-vehicles')



