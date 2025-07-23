# This is the third program in the sequence "Month_of_5_Route_Data.py" -> "Gather_Possible_Routings.py" -> "Analyze_for_Synthetic_Routing.py"
# It takes the CSV output of "Month_of_5_Route_Data.py" as the input ORIGINAL_INPUT_FILE and the CSV output of "Gather_Possible_Routings.py"
# as the input ROUTING_INPUT_FILE




import Duffel_Calls_Library as dcl
import sqlite3
import json
import numpy as np
import matplotlib.pyplot as plt




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


segment_list = original_data_dict['segments']
for i in range(len(segment_list)):
    segment_with_double_quotes = segment_list[i].replace("\'", "\"")
    segment_list[i] = json.loads(segment_with_double_quotes)
segment_list = routing_data_dict['segments']
for i in range(len(segment_list)):
    segment_with_double_quotes = segment_list[i].replace("\'", "\"")
    segment_list[i] = json.loads(segment_with_double_quotes)



# "leg_list" should be a list of pairs of [origin, destination]
def get_all_valid_leg_orders(root_origin, root_destination, leg_list):
    # This function returns all the possible ways that different legs can be put together to create the final trip. It searches in a tree until
    # all combinations are exhausted
    total_legs = len(leg_list)

    all_valid_leg_orders = []

    # We set up the main operations on the tree; they don't return anything, but change the list because it is mutable
    def append_zero(leg_indices):
        leg_indices.append(0)
    def increment(leg_indices):
        leg_indices[-1] += 1
    def increment_until_change(leg_indices):
        # This keeps incrementing until index -1 either has the same origin as the destination of index -2, or until index -1 has cycled through all legs
        if len(leg_indices) < 2:
            target_origin = root_origin
        else:
            penultimate_leg_index = leg_indices[-2]
            target_origin = leg_list[penultimate_leg_index][1]
        
        while True:
            last_leg_index = leg_indices[-1]
            if last_leg_index >= total_legs:
                break

            last_origin = leg_list[last_leg_index][0]
            if last_origin == target_origin:
                if last_leg_index not in leg_indices[:-1]:  # No loops allowed, not that they should ever come up, but better to be safe
                    break
            
            leg_indices[-1] += 1
    def remove_last(leg_indices):
        leg_indices.pop()
    def save(leg_indices):
        all_valid_leg_orders.append(leg_indices.copy())
    
    current_leg_indices = [0]
    increment_until_change(current_leg_indices)  # To make sure the first leg actually starts at the root_origin
    # Now we create the while loop that uses these operations
    while True:
        # Did the last index cycle through every leg?
        if current_leg_indices[-1] >= total_legs:
            remove_last(current_leg_indices)
            if len(current_leg_indices) == 0:  # Then we are done searching
                break
                
            increment(current_leg_indices)
            increment_until_change(current_leg_indices)
        else:
            last_leg_index = current_leg_indices[-1]
            last_destination = leg_list[last_leg_index][1]
            # Does the itinerary end at the destination?
            if last_destination == root_destination:
                save(current_leg_indices)
                increment(current_leg_indices)
                increment_until_change(current_leg_indices)
            else:
                # Then the itinerary is valid so far but incomplete
                append_zero(current_leg_indices)
                increment_until_change(current_leg_indices)

    return all_valid_leg_orders







# Now reorganize the SQLite data into a dictionary that uses the (origin, destination, date) tuple to group flights.
# We also find all the common layover flights at the same time, and organize them in the same way.
# This relies on the SQLite file being ordered so that every flight with some combination
# (origin, destination, date) is adjacent to all the others; they can't be scattered randomly along the lists.
# For the final product, we may want a better method for finding layover flights than just checking where the flights of the day have layovers,
# but for now it works.

original_flights = dcl.unpack_flight_array(original_data_dict, id_keys=('origin', 'destination', 'date'))
# Each (origin, destination, date) key of "original_flights" will lead to another dictionary of the form:
    # {'airline_name': [<Flight 0 airline_name>, <Flight 1 airline_name>, ...],
    #  'airline_code': [<Flight 0 airline_code>, <Flight 1 airline_code>, ...],
    #  'total_amount': [<Flight 0 total_amount>, <Flight 1 total_amount>, ...],
    #  'total_currency' : [<Flight 0 total_currency>, <Flight 1 total_currency>, ...],
    #  'segments' : [<Flight 0 segments>, <Flight 1 segments>, ...],
    # }

# We do something similar with routing_flights, but with extra nesting.
routing_flights_roots = dcl.unpack_flight_array(routing_data_dict, id_keys=('root_origin', 'root_destination', 'date'))
routing_flights = {}
for key in routing_flights_roots.keys():
    routing_flights[key] = dcl.unpack_flight_array(routing_flights_roots[key], id_keys=('origin', 'destination'))
# Each (root_origin, root_destination, date) key of "routing_flights" will lead to another dictionary with keys (origin, destination),
# which in turn lead to dictionaries of the form:
    # {'airline_name': [<Flight 0 airline_name>, <Flight 1 airline_name>, ...],
    #  'airline_code': [<Flight 0 airline_code>, <Flight 1 airline_code>, ...],
    #  'total_amount': [<Flight 0 total_amount>, <Flight 1 total_amount>, ...],
    #  'total_currency' : [<Flight 0 total_currency>, <Flight 1 total_currency>, ...],
    #  'segments' : [<Flight 0 segments>, <Flight 1 segments>, ...],
    # }



# Now both datasets are in useful formats, and we can search for synthetic routing. We can have a lot more detail for the final product, but for now,
# it is sufficient to find the least expensive flight from each City A to City B. We will store these in structures shaped like "original_flights"
# and "routing_flights", as seen below.

# First we find the cheapest original flights, before we try synthetic routing
original_cheapest_flights = {}
for key in original_flights.keys():
    min_amount = min(original_flights[key]['total_amount'])
    min_index = original_flights[key]['total_amount'].index(min_amount)
    original_cheapest_flights[key] = [min_index, min_amount]

# Now cheapest routing flights
routing_cheapest_flights = {}
for key1 in routing_flights.keys():
    routing_cheapest_flights[key1] = {}
    for key2 in routing_flights[key1].keys():
        min_amount = min(routing_flights[key1][key2]['total_amount'])
        min_index = routing_flights[key1][key2]['total_amount'].index(min_amount)
        routing_cheapest_flights[key1][key2] = [min_index, min_amount]

# Oh... the flights are already sorted by price. Ah well, it doesn't hurt to sort them again. We can skip that later if needed

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
    
    min_amount = min(synthetic_prices)
    min_index = synthetic_prices.index(min_amount)

    cheapest_synthetic_leg_indices = all_valid_leg_orders[min_index]
    cheapest_synthetic_legs = []
    for i in range(len(cheapest_synthetic_leg_indices)):
        cheapest_synthetic_legs.append(leg_list[cheapest_synthetic_leg_indices[i]])
    synthetic_price = min_amount

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
