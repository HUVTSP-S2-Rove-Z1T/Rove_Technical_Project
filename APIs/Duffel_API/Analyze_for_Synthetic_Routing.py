# This code is very messy, I can clean it up later

# This is the third program in the sequence "Month_of_5_Route_Data.py" -> "Gather_Possible_Routings.py" -> "Analyze_for_Synthetic_Routing.py"
# It takes the CSV output of "Month_of_5_Route_Data.py" as the input ORIGINAL_INPUT_FILE and the CSV output of "Gather_Possible_Routings.py"
# as the input ROUTING_INPUT_FILE


import pandas as pd
import ast
from dotenv import load_dotenv
import os
import requests
import time
import matplotlib.pyplot as plt
import numpy as np
import sqlite3



# ORIGINAL_INPUT_FILE = 'Duffel_API/Month_of_5.csv'
# ORIGINAL_INPUT_FILE = 'Duffel_API/Day_of_5.csv'  # Just checking one day keeps computation time reasonable; it takes a lot of Duffel calls to do synthetic routing

# ROUTING_INPUT_FILE = 'Duffel_API/Day_of_Possible_Routings_5.csv'  # This should be the output of "Gather Possible Routings.py" on ORIGINAL_INPUT_FILE

# Read from SQLite DB instead of CSV
conn = sqlite3.connect('Duffel_Flights.db')
c = conn.cursor()
# Original flights
c.execute('SELECT origin, destination, date, airline_name, airline_code, total_amount, total_currency, segments FROM flights')
rows = c.fetchall()
columns = ["origin", "destination", "date", "airline_name", "airline_code", "total_amount", "total_currency", "segments"]
original_data_dict = {col: [] for col in columns}
for row in rows:
    for i, col in enumerate(columns):
        original_data_dict[col].append(row[i])
# Routing flights
c.execute('SELECT root_origin, root_destination, date, origin, destination, airline_name, airline_code, total_amount, total_currency, segments FROM possible_routings')
routing_rows = c.fetchall()
routing_columns = ["root_origin", "root_destination", "date", "origin", "destination", "airline_name", "airline_code", "total_amount", "total_currency", "segments"]
routing_data_dict = {col: [] for col in routing_columns}
for row in routing_rows:
    for i, col in enumerate(routing_columns):
        routing_data_dict[col].append(row[i])
conn.close()


import ast
segment_list = original_data_dict['segments']
for i in range(len(segment_list)):
    segment_list[i] = ast.literal_eval(segment_list[i])
segment_list = routing_data_dict['segments']
for i in range(len(segment_list)):
    segment_list[i] = ast.literal_eval(segment_list[i])


def get_cheapest_flight_index_and_amount(flight_dict_list):
    min_index = 0
    min_value = flight_dict_list[min_index]['total_amount']
    for i in range(len(flight_dict_list)):
        current_value = flight_dict_list[i]['total_amount']
        if current_value < min_value:
            min_value = current_value
            min_index = i
    
    return [min_index, min_value]


def get_cheapest_leg_order_index_and_amount(leg_order_price_list):
    min_index = 0
    min_value = leg_order_price_list[min_index]
    for i in range(len(leg_order_price_list)):
        current_value = leg_order_price_list[i]
        if current_value < min_value:
            min_value = current_value
            min_index = i
    
    return [min_index, min_value]


# "leg_list" should be a list of pairs of [origin, destination]. This needs to be seriously reworked, I think it works but is very messy
def get_all_valid_leg_orders(root_origin, root_destination, leg_list):
    # This function returns all the possible ways that different legs can be put together to create the final trip.
    # This operates under the hopefully safe assumption that if [City A, City B] is in the list, [City B, City A] is not. Also
    # no larger cycles like [A, B], [B, C], and [C, A]
    total_legs = len(leg_list)

    all_valid_leg_orders = []

    # It searches in a tree
    current_leg_indices = [0]
    while current_leg_indices[-1] < total_legs and leg_list[current_leg_indices[-1]][0] != root_origin:  # Make sure the first leg starts at "root_origin"
        current_leg_indices[-1] += 1

    if current_leg_indices[-1] >= total_legs:  # This should never happen
        print('Error: none of the legs begin at the root_origin')
        return []

    add_new_leg = True
    while len(current_leg_indices) > 0:
        # Go deeper; add legs
        if add_new_leg:
            current_leg_indices.append(0)
        
        add_new_leg = True
        if len(current_leg_indices) > 1:
            while current_leg_indices[-1] < total_legs and leg_list[current_leg_indices[-1]][0] != leg_list[current_leg_indices[-2]][1]:
                current_leg_indices[-1] += 1
        else:
            while current_leg_indices[-1] < total_legs and leg_list[current_leg_indices[-1]][0] != root_origin:
                current_leg_indices[-1] += 1

        if current_leg_indices[-1] >= total_legs:  # If they have all been searched, remove a leg and update the previous leg as many times as necessary
            while current_leg_indices[-1] >= total_legs:
                current_leg_indices.pop()
                if len(current_leg_indices) == 0:
                    break
                else:
                    current_leg_indices[-1] += 1
                    if len(current_leg_indices) == 1:
                        while current_leg_indices[-1] < total_legs and leg_list[current_leg_indices[-1]][0] != root_origin:
                            current_leg_indices[-1] += 1
                    else:
                        while current_leg_indices[-1] < total_legs and leg_list[current_leg_indices[-1]][0] != leg_list[current_leg_indices[-2]][1]:
                            current_leg_indices[-1] += 1
            add_new_leg = False

        else:  # Then a leg clicked, and the tree can keep growing
            if leg_list[current_leg_indices[-1]][1] == root_destination:
                all_valid_leg_orders.append(current_leg_indices.copy())
                current_leg_indices[-1] += 1
                add_new_leg = False
            else:
                pass
    
    return all_valid_leg_orders







# Now reorganize the csv data into a dictionary that uses the (origin, destination, date) tuple to group flights.
# We also find all the common layover flights at the same time, and organize them in the same way.
# This relies on the CSV file being ordered so that every flight with some combination
# (origin, destination, date) is adjacent to all the others; they can't be scattered randomly along the lists.
# For the final product, we may want a better method for finding layover flights than just checking where the flights of the day have layovers,
# but for now it works.

original_flights = {}
# Each (origin, destination, date) key of "original_flights" will lead to another dictionary of the form:
    # {'airline_name': <name>,
    #  'airline_code': <code>,
    #  'total_amount': <amount>,
    #  'total_currency' : <currency>,
    #  'segments' : <segments>,
    # }

original_csv_length = len(original_data_dict['origin'])
current_index = 0
while current_index < original_csv_length:  # This will go until we exhaust the CSV file
    identifiers = (original_data_dict['origin'][current_index],
                   original_data_dict['destination'][current_index],
                   original_data_dict['date'][current_index])
    # We add this to the dictionary
    original_flights[identifiers] = []

    while True:  # This will go until it reaches a flight with a different origin, destination, or date
        temp_data_dict = {'airline_name' : original_data_dict['airline_name'][current_index],
                           'airline_code' : original_data_dict['airline_code'][current_index],
                           'total_amount' : original_data_dict['total_amount'][current_index],
                           'total_currency' : original_data_dict['total_currency'][current_index],
                           'segments' : original_data_dict['segments'][current_index]}
        original_flights[identifiers].append(temp_data_dict)

        current_index += 1
        if current_index >= original_csv_length or (original_data_dict['origin'][current_index],
                                                    original_data_dict['destination'][current_index],
                                                    original_data_dict['date'][current_index]) != identifiers:
            break

# We do something similar with routing_flights, but with extra nesting.
routing_flights = {}
# Each (root_origin, root_destination, date) key of "routing_flights" will lead to another dictionary with keys (origin, destination),
# which in turn lead to dictionaries of the form:
    # {'airline_name': <name>,
    #  'airline_code': <code>,
    #  'total_amount': <amount>,
    #  'total_currency' : <currency>,
    #  'segments' : <segments>,
    # }

routing_csv_length = len(routing_data_dict['root_origin'])
current_index = 0
while current_index < routing_csv_length:  # This will go until we exhaust the CSV file
    identifiers = (routing_data_dict['root_origin'][current_index],
                   routing_data_dict['root_destination'][current_index],
                   routing_data_dict['date'][current_index])
    # We add this to the dictionary
    routing_flights[identifiers] = {}

    while True:  # This will go until it reaches a flight with a different root_origin, root_destination, or date
        next_identifiers = (routing_data_dict['origin'][current_index],
                            routing_data_dict['destination'][current_index])
        
        routing_flights[identifiers][next_identifiers] = []
        while True:  # This will go until it reaches a flight with a different origin or destination

            temp_data_dict = {'airline_name' : routing_data_dict['airline_name'][current_index],
                            'airline_code' : routing_data_dict['airline_code'][current_index],
                            'total_amount' : routing_data_dict['total_amount'][current_index],
                            'total_currency' : routing_data_dict['total_currency'][current_index],
                            'segments' : routing_data_dict['segments'][current_index]}
            routing_flights[identifiers][next_identifiers].append(temp_data_dict)

            current_index += 1

            if current_index >= routing_csv_length or (routing_data_dict['origin'][current_index],
                                                       routing_data_dict['destination'][current_index]) != next_identifiers:
                break

        if current_index >= routing_csv_length or (routing_data_dict['root_origin'][current_index],
                                                   routing_data_dict['root_destination'][current_index],
                                                   routing_data_dict['date'][current_index]) != identifiers:
            break


# Now both datasets are in useful formats, and we can search for synthetic routing. We can have a lot more detail for the final product, but for now,
# it is sufficient to find the least expensive flight from each City A to City B. We will store these in structures shaped like "original_flights"
# and "routing_flights", as seen below.

# First we find the cheapest original flights, before we try synthetic routing
original_cheapest_flights = {}
for key in original_flights.keys():
    original_cheapest_flights[key] = get_cheapest_flight_index_and_amount(original_flights[key])

# Now cheapest routing flights
routing_cheapest_flights = {}
for key1 in routing_flights.keys():
    routing_cheapest_flights[key1] = {}
    for key2 in routing_flights[key1].keys():
        routing_cheapest_flights[key1][key2] = get_cheapest_flight_index_and_amount(routing_flights[key1][key2])

# Oh... the flights are already sorted by price. Ah well, it doesn't hurt to sort them again. We can skip the "get_cheapest_flight_index_and_amount" part
# later on if needed.

for key1 in routing_flights.keys():
    direct_price = original_cheapest_flights[key1][1]

    key2_list = []
    for key2 in routing_flights[key1].keys():
        key2_list.append(key2)
    
    root_origin = key1[0]
    root_destination = key1[1]
    leg_list = key2_list

    all_valid_leg_orders = get_all_valid_leg_orders(root_origin=root_origin, root_destination=root_destination, leg_list=leg_list)

    synthetic_prices = []
    for i in range(len(all_valid_leg_orders)):
        this_leg_order = all_valid_leg_orders[i]
        total_price = 0
        for j in range(len(this_leg_order)):
            leg_index = this_leg_order[j]
            actual_leg = leg_list[leg_index]
            total_price += routing_cheapest_flights[key1][actual_leg][1]
        
        synthetic_prices.append(total_price)
    
    result = get_cheapest_leg_order_index_and_amount(synthetic_prices)
    cheapest_synthetic_leg_indices = all_valid_leg_orders[result[0]]
    cheapest_synthetic_legs = []
    for i in range(len(cheapest_synthetic_leg_indices)):
        cheapest_synthetic_legs.append(leg_list[cheapest_synthetic_leg_indices[i]])
    synthetic_price = result[1]

    print(f'For flights from {key1[0]} to {key1[1]} on {key1[2]}:')
    print(f'    The cheapest direct flight is {direct_price}')
    print(f'    The cheapest synthetic routing flight is {synthetic_price}')
    print(f'    That synthetic routing itinerary is {cheapest_synthetic_legs}')


route_dates = []
direct_prices = []
synthetic_prices = []
for key1 in routing_flights.keys():
    route = f"{key1[0]}->{key1[1]}"
    date = key1[2]
    direct_price = original_cheapest_flights[key1][1]
    key2_list = list(routing_flights[key1].keys())
    leg_list = key2_list
    all_valid_leg_orders = get_all_valid_leg_orders(root_origin=key1[0], root_destination=key1[1], leg_list=leg_list)
    synthetic_prices_list = []
    for i in range(len(all_valid_leg_orders)):
        this_leg_order = all_valid_leg_orders[i]
        total_price = 0
        for j in range(len(this_leg_order)):
            leg_index = this_leg_order[j]
            actual_leg = leg_list[leg_index]
            total_price += routing_cheapest_flights[key1][actual_leg][1]
        synthetic_prices_list.append(total_price)
    if synthetic_prices_list:
        synthetic_price = min(synthetic_prices_list)
    else:
        synthetic_price = np.nan
    route_dates.append(f"{route} {date}")
    direct_prices.append(float(direct_price))
    synthetic_prices.append(float(synthetic_price) if not np.isnan(synthetic_price) else np.nan)

plt.figure(figsize=(12, 6))
plt.plot(route_dates, direct_prices, label='Direct Price', marker='o')
plt.plot(route_dates, synthetic_prices, label='Synthetic Price', marker='x')
plt.xticks(rotation=90)
plt.xlabel('Route and Date')
plt.ylabel('Price')
plt.title('Direct vs Synthetic Flight Prices by Route and Date')
plt.legend()
plt.tight_layout()
plt.show()

print("\n--- Summary Statistics ---")
print(f"Average direct price: {np.nanmean(direct_prices):.2f}")
print(f"Average synthetic price: {np.nanmean(synthetic_prices):.2f}")
print(f"Number of routes cheaper with synthetic routing: {np.nansum(np.array(synthetic_prices) < np.array(direct_prices))}")
