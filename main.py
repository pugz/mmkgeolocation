import os
from flask import Flask, request, render_template, jsonify
import pandas as pd
import requests
from geopy.distance import geodesic
from datetime import datetime

app = Flask(__name__)

# Load customer databases into memory
customers_co = pd.read_csv('CustomerDB-CO.csv')
customers_il = pd.read_csv('CustomerDB-IL.csv')

# Function to download CSV files
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
    def distance_from_input(row):
        customer_loc = (row['Latitude'], row['Longitude'])
        return geodesic((input_lat, input_lon), customer_loc).miles

    customers['Distance'] = customers.apply(distance_from_input, axis=1)
    nearest_customer = customers.loc[customers['Distance'].idxmin()]
    return nearest_customer

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/find_customer', methods=['POST'])
def find_customer():
    address = request.form['address']

    # For demonstration purposes, let's assume the lat/lon is already available
    # Replace this section with a real geocoding API if necessary.
    address_lat = 40.730610  # Hardcoded latitude for now
    address_lon = -73.935242  # Hardcoded longitude for now

    # Combine CO and IL customers
    all_customers = pd.concat([customers_co, customers_il])

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
