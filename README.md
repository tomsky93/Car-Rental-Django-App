# Car Rental
## Description
Welcome to Car Rental, a dynamic vehicle rental application developed using the Django framework. This application offers a comprehensive platform that facilitates the easy searching, booking, and management of vehicle rentals, providing an minimalistic interface for both users and staff.

### Features
- Vehicle Search by Location and Availability: Users can easily search for vehicles based on their desired location and the dates they are available. 

- Reservation Creation: Once a suitable vehicle is found, users can proceed to create a reservation with just a few clicks.

- Invoice Generation Post-Rental: After the return of the vehicle, the system automatically generates an invoice for the service

- Reservation Management for Users and Staff: Both users and staff members have the capability to manage reservations. Users can view, modify, or cancel their bookings, while staff can oversee all reservations, perform modifications, and manage vehicle returns.

- Dashboard for Staff: The staff dashboard provides a comprehensive overview of current reservations, returns, and other relevant information. 

- Insightful Vehicle and Reservation Information for Staff: Staff members have access to detailed information regarding reservations and vehicles. This includes the ability to inspect current bookings, availability status, and other vehicle data.


## Install 

1. Clone the repository: git clone [repository-url]
2. Navigate to the application directory
3. Create and activate virtual environment
   
`python -m venv env`

`.\env\Scripts\activate`

4. Install required dependencies: `pip install -r requirements.txt`
5. Make migrations: `python manage.py makemigrations`
6. Apply migrations: `python manage.py migrate`
7. Application is equipped with a initial dataset of vehicles located in the main directory. 
If you want to use them, enter the following command in the console

`python manage.py loaddata fixtures.json`

8. Start the Django development server: `python manage.py runserver`
