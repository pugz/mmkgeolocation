from flask import Flask, request, render_template, jsonify
import pandas as pd
import requests
from geopy.distance import geodesic
from datetime import datetime
import os

app = Flask(__name__)

# Load customer databases into memory
customers_co = pd.read_csv('CustomerDB-CO.csv')
customers_il = pd.read_csv('CustomerDB-IL.csv')

# Debugging: Print column names to ensure CustomerID exists
print("CO Customer Columns:", customers_co.columns)
print("IL Customer Columns:", customers_il.columns)

# Geoapify API key
GEOAPIFY_API_KEY = '2ca56f585d314b4faa0b4114d5c48a8c'

# Function to download CSV files (if needed)
def download_csv_files():
    today = datetime.now().date()

    links_file = 'Links-to-update.csv'
    with open(links_file, 'r') as file:
        reader = pd.read_csv(links_file)
        for _, row in reader.iterrows():
            filename, url, _, date_str = row
            update_date = datetime.strptime(date_str, '%Y-%m-%d').date()

            if today > update_date:
                return f"Please update the links file for {filename}."
            else:
                response = requests.get(url)
                with open(filename, 'wb') as f:
                    f.write(response.content)

# Function to find nearest customer
def find_nearest_customer(input_lat, input_lon, customers):
    # Drop rows where Latitude or Longitude is missing
    customers = customers.dropna(subset=['Latitude', 'Longitude'])

    def distance_from_input(row):
        customer_lat = row['Latitude']
        customer_lon = row['Longitude']
        
        # Check if latitude and longitude are valid numbers (not NaN or None)
        if pd.isna(customer_lat) or pd.isna(customer_lon):
            return float('inf')  # Return a large distance if coordinates are missing
        
        customer_loc = (customer_lat, customer_lon)
        return geodesic((input_lat, input_lon), customer_loc).miles

    # Apply the distance calculation to valid rows only
    customers['Distance'] = customers.apply(distance_from_input, axis=1)

    # Find the customer with the minimum distance
    nearest_customer = customers.loc[customers['Distance'].idxmin()]

    # Debugging: Print nearest customer details
    print("Nearest Customer Details:", nearest_customer)
    
    return nearest_customer

# Function to geocode the address using Geoapify
def geocode_address(address):
    api_url = f"https://api.geoapify.com/v1/geocode/search?text={address}&apiKey={GEOAPIFY_API_KEY}"
    response = requests.get(api_url).json()

    if response['features']:
        # Get latitude and longitude from the response
        lat = response['features'][0]['properties']['lat']
        lon = response['features'][0]['properties']['lon']
        
        # Check if lat/lon are valid numbers
        if lat is None or lon is None:
            return None, None
        
        return lat, lon
    return None, None

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/find_customer', methods=['POST'])
def find_customer():
    # Get the separate fields from the form
    street = request.form['street']
    city = request.form['city']
    state = request.form['state']

    # Combine the fields into a full address string
    address = f"{street}, {city}, {state}"

    # Geocode the entered address using Geoapify
    address_lat, address_lon = geocode_address(address)
    
    if address_lat is None or address_lon is None:
        return jsonify({'error': 'Could not geocode the address. Please check the address and try again.'})

    # Combine CO and IL customers and remove rows with missing latitude/longitude
    all_customers = pd.concat([customers_co, customers_il])
    all_customers = all_customers.dropna(subset=['Latitude', 'Longitude'])

    # Ensure 'CustomerID' column exists
    if 'CustomerID' not in all_customers.columns:
        return jsonify({'error': 'CustomerID column not found in customer data.'})

    # Find the nearest customer
    nearest_customer = find_nearest_customer(address_lat, address_lon, all_customers)

    # Generate the custom link
    customer_id = nearest_customer['CustomerID']
    link_template = "https://mmkgroup.encompass8.com/Home?DashboardID=100100&TableName=Customers&SelectDisplayInParent=CustomerID%2CCompany%2CAddress%2CCity%2CCustomerTypeID%2CLocationID%2CAccountStatus&SubTableJoinID=Customers_TableTranslations%2CCustomersZones_Customers%2CSplitInvoices_Customers%2CServiceWindows_Customers&Parameters=F:CustomerID~V:999999~O:E|F:AccountStatus~V:Active^Inactive^OutOfBus~O:E"
    custom_link = link_template.replace("999999", str(customer_id))

    return jsonify({
        'customer_id': int(customer_id),
        'distance': nearest_customer['Distance'],
        'link': custom_link
    })

if __name__ == '__main__':
    # Bind to the dynamic port assigned by Render
    port = int(os.environ.get('PORT', 5000))  # Default to port 5000 if not set
    app.run(host='0.0.0.0', port=port)
