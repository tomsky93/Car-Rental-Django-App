from django import template
from django.utils.html import format_html_join, format_html
from ..models import Location, VehicleCategory
from django.urls import reverse

register = template.Library()

@register.simple_tag
def get_location_links():
    locations = Location.objects.all()
    links = format_html_join(
        '\n', "<a href='{}'>{}</a><br>",
        ((location.get_absolute_url(), location.city) for location in locations)
    )
    return format_html("{}", links)

@register.simple_tag  
def get_category_links():
    categories = VehicleCategory.objects.all()
    links = format_html_join(
        '\n', "<a href='{}'>{}</a><br>",
        ((category.get_absolute_url(), category.category) for category in categories)
    )
    return format_html("{}", links)

@register.simple_tag
def admin_menu():
    menu_items = [
        {'name': 'Dashboard', 'url': 'dashboard', 'icon': 'fa-solid fa-gauge'},
        {'name': 'Vehicles', 'url': 'vehicles', 'icon': 'fa fa-car'},
        {'name': 'Reservations', 'url': 'reservation_list', 'icon': 'fa-regular fa-calendar-days'},
        {'name': 'Rentals', 'url': 'rental_list', 'icon': 'fa fa-book'},
    ]
    menu_html = ''.join([
        f'<a href="{reverse(item["url"])}"><i class="{item["icon"]}">&nbsp;</i> {item["name"]}</a>' 
        for item in menu_items
    ])
    return format_html(menu_html)
@register.simple_tag
def user_menu():
    menu_items = [
        {'name': 'Search a car', 'url': 'index', 'icon': 'fa fa-search'},
        {'name': 'Reservations', 'url': 'reservation_list', 'icon': 'fa-regular fa-calendar-days'},
        {'name': 'Rentals', 'url': 'rental_list', 'icon': 'fa fa-book'},
        {'name': 'Your account', 'url': 'users:profile', 'icon': 'fa fa-user'}, 
    ]
    
    menu_html = ''.join([
        f'<a href="{reverse(item["url"])}"><i class="{item["icon"]}"></i> {item["name"]}</a>' 
        for item in menu_items
    ])
    return format_html(menu_html)

