from flask import Flask, request, render_template
import pandas as pd
import requests
from geopy.distance import geodesic
from datetime import datetime
import os

app = Flask(__name__)

# Load customer databases into memory
customers_co = pd.read_csv('CustomerDB-CO.csv')
customers_il = pd.read_csv('CustomerDB-IL.csv')

# Debugging: Print column names to ensure "Customer ID" exists
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

    # Find the customer with the minimum distance and select only the first one if there are ties
    nearest_customer = customers.loc[customers['Distance'].idxmin()].iloc[0]

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
    city = request.form
