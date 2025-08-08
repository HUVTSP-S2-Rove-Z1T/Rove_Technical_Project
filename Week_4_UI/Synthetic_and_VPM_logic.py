import sqlite3
import os
from dotenv import load_dotenv
from datetime import date, timedelta
import requests
import time
import json
import pandas as pd

# This uses "master_flight_list.db" to store its information

# @CHASE: the main function is "find_possible_routings_from_master_list()". This searches the master list of flights for all the flights that
# match segments of the trip from point A to point B, and also tells you which combinations of those segments actually get you to your destination.
# If you run the test code I left below, you'll see more clearly when you look at the output CSV files.
# You can solve it a different way if it makes sense, but I was thinking that what we need now is a few functions that take in the output of
# "find_possible_routings_from_master_list()" and return the top 5-10 options based on some criterion, like "best value" or just "cheapest", or
# any of the other ones we've discussed (most importantly, ones that let the user use their miles, but that will be easier once we
# have an example award chart to draw from). Once we have those, all we need to do is hook up this library to "Week_4_UI.py", and we'll get real
# recommendations.


CALL_UNIT_KEYS = ["origin", "destination", "passengers", "cabin_class", "departure_date", "return_date"]
LIST_AS_STRING_KEYS = ["departure_segment_ids", "return_segment_ids", "departure_segments", "return_segments"]


# Just for viewing purposes, for debugging
def save_dict_to_csv(data_dict, output_file='master_flight_list_test.csv'):
    df_final = pd.DataFrame(data_dict)
    df_final.to_csv(output_file, index=False)


def turn_master_flight_db_into_dict(database_name='master_flight_list.db'):
    conn = sqlite3.connect(database_name)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS flights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            origin TEXT,
            destination TEXT,
            passengers INTEGER,
            cabin_class TEXT,
            date TEXT,
            departure_date TEXT,
            departure_time TEXT,
            departure_arrival_time TEXT,
            return_date TEXT,
            return_time TEXT,
            return_arrival_time TEXT,
            airline_name TEXT,
            airline_code TEXT,
            order_id TEXT,
            departure_slice_id TEXT,
            return_slice_id TEXT,
            departure_segment_ids TEXT,
            return_segment_ids TEXT,
            departure_segments TEXT,
            return_segments TEXT,
            total_amount REAL,
            total_currency TEXT,
            duffel_call_time TEXT
        )
    ''')
    conn.commit()

    columns = ["origin", "destination", "passengers", "cabin_class", "departure_date", "departure_time", "departure_arrival_time", "return_date", "return_time", "return_arrival_time", "airline_name", "airline_code", "order_id", "departure_slice_id", "return_slice_id", "departure_segment_ids", "return_segment_ids", "departure_segments", "return_segments", "total_amount", "total_currency", "duffel_call_time"]
    key_number = len(columns)

    columns_as_one_string = ''
    for i in range(len(columns)):
        columns_as_one_string += columns[i]
        if i != key_number - 1:
            columns_as_one_string += ', '


    # Now we get all the flights currently in the database
    c.execute(f'SELECT {columns_as_one_string} FROM flights')
    rows = c.fetchall()

    # Convert to dictionary format similar to previous CSV logic
    data_dict = {col: [] for col in columns}
    for row in rows:
        for i, col in enumerate(columns):
            data_dict[col].append(row[i])

    for list_key in LIST_AS_STRING_KEYS:
        list_key_values = data_dict[list_key]
        for i in range(len(list_key_values)):
            if list_key_values[i]:
                list_key_with_double_quotes = list_key_values[i].replace("\'", "\"")
                list_key_values[i] = json.loads(list_key_with_double_quotes)  # Remember that list mutability will carry the changes to "data_dict"
    
    return data_dict


def call_flight_offers(headers, data):
    origin = data["data"]["slices"][0]["origin"]
    destination = data["data"]["slices"][0]["destination"]
    departure_str = data["data"]["slices"][0]["departure_date"]
    
    response = requests.post(
        "https://api.duffel.com/air/offer_requests",
        headers=headers,
        json=data
    )

    # Sometimes there is a problem with the rate limit; this if statement adjusts for that
    if response.status_code == 429:
        print("Rate limit exceeded; waiting until it cools down")
        start_time = time.time()

        # We wait at most a minute
        while time.time() - start_time < 60:
            time.sleep(1)
            response = requests.post(
                "https://api.duffel.com/air/offer_requests",
                headers=headers,
                json=data
            )

            if response.status_code == 429:
                pass
            else:
                break

    if response.status_code == 201:
        offers = response.json()["data"]["offers"]
        if not offers:
            print(f"No offers found for {origin} to {destination} on {departure_str}.")
        else:
            print(f"{len(offers)} offers found for {origin} to {destination} on {departure_str}:")

            return offers

    else:
        print(f"Error for {origin} to {destination} on {departure_str}: {response.status_code}")
        print(response.text)


# This will turn the flight data as it is stored in the SQLite files (a dictionary with keys like 'origin' and 'destination', that each lead
# to a list where the nth index corresponds to the origin/destination of the nth flight) into a new format: a dictionary with keys
# (<origin>, <destination>, <date>) that lead to another dictionary {'airline_name' : [], 'airline_code' : [], ...} where each key *now*
# leads to a list where the nth index corresponds to the origin/destination of the nth flight.
# That way, flights are indexed first and foremost by where they are going and when they leave.
def unpack_flight_array(flight_array, id_keys=tuple(CALL_UNIT_KEYS)):
    new_flight_dict = {}

    flight_array_keys = list(flight_array.keys())
    non_id_keys = []
    for array_key in flight_array_keys:
        if array_key not in id_keys:
            non_id_keys.append(array_key)

    array_length = len(flight_array[flight_array_keys[0]])
    if array_length < 1:
        print('Error, no flights to unpack')
        return {}
    
    current_index = 0

    identifiers_list = []
    for key in id_keys:
        identifiers_list.append(flight_array[key][current_index])
    identifiers = tuple(identifiers_list)
    while current_index < array_length:  # This will go until we exhaust the array
        # We add this to the two dictionaries
        new_flight_dict[identifiers] = {}
        for other_key in non_id_keys:
            new_flight_dict[identifiers][other_key] = []

        while True:  # This will go until it reaches a flight with a different origin, destination, or date
            for other_key in non_id_keys:
                new_flight_dict[identifiers][other_key].append(flight_array[other_key][current_index])

            current_index += 1
            if current_index >= array_length:
                break
            else:
                next_identifiers_list = []
                for key in id_keys:
                    next_identifiers_list.append(flight_array[key][current_index])
                next_identifiers = tuple(next_identifiers_list)

                if identifiers != next_identifiers:
                    identifiers = next_identifiers
                    break
    
    return new_flight_dict


def repack_flight_array(flight_array, id_keys=tuple(CALL_UNIT_KEYS)):
    new_flight_dict = {}
    dict_keys = list(flight_array.keys())
    inner_keys = list(flight_array[dict_keys[0]].keys())

    for key in id_keys:
        new_flight_dict[key] = []
    
    for key in inner_keys:
        new_flight_dict[key] = []

    for key in dict_keys:
        for i in range(len(flight_array[key][inner_keys[0]])):  # For each flight in a key
            for j in range(len(id_keys)):
                new_flight_dict[id_keys[j]].append(key[j])

            for inner_key in inner_keys:
                new_flight_dict[inner_key].append(flight_array[key][inner_key][i])
    
    return new_flight_dict


            


def combine_packed_flight_arrays(flight_array_list):
    final_array = {}
    dict_keys = list(flight_array_list[0].keys())

    for key in dict_keys:
        final_array[key] = []

    for flight_array in flight_array_list:
        if list(flight_array.keys()) == dict_keys:
            for key in dict_keys:
                for i in range(len(flight_array[key])):
                    final_array[key].append(flight_array[key][i])
        else:
            raise TypeError("The keys of the dictionaries must match")
    
    return final_array



# Options for cabin_class: "first", "business", "premium_economy", or "economy"
# The output of this function is called "packed format", and it is how "master_flight_list.db" is structured
def get_dict_for_route(origin, destination, passengers, cabin_class, departure_date_str, return_date_str=None):
    # "duffel_call_time" is when we actually make the call
    data_saved = {
        "origin": [],
        "destination": [],
        "passengers": [],
        "cabin_class": [],
        "departure_date": [],
        "departure_time": [],
        "departure_arrival_time": [],
        "return_date": [],
        "return_time": [],
        "return_arrival_time": [],
        "airline_name": [],
        "airline_code": [],
        "order_id": [],
        "departure_slice_id": [],
        "return_slice_id": [],
        "departure_segment_ids": [],
        "return_segment_ids": [],
        "departure_segments": [],
        "return_segments": [],
        "total_amount": [],
        "total_currency": [],
        "duffel_call_time": []
    }

    data_saved_keys = list(data_saved.keys())

    load_dotenv()
    access_token = os.getenv("ACCESS_TOKEN")
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Duffel-Version": "v2"
    }
    
    if return_date_str:
        slices = [{
                    "origin": origin,
                    "destination": destination,
                    "departure_date": departure_date_str,
                }, {
                    "origin": destination,
                    "destination": origin,
                    "departure_date": return_date_str,
                }, ]
    else:
        slices = [{
                    "origin": origin,
                    "destination": destination,
                    "departure_date": departure_date_str,
        }]

    passenger_data_list = []
    for i in range(passengers):
        passenger_data_list.append({"type": "adult"})

    data = {
        "data": {
            "slices": slices,
            "passengers": passenger_data_list,
            "cabin_class": cabin_class
        }
    }
            
    offers = call_flight_offers(headers=headers, data=data)

    if offers:
        for offer in offers:

            departure_time = offer["slices"][0]["segments"][0]["departing_at"]
            departure_arrival_time = offer["slices"][0]["segments"][-1]["arriving_at"]

            carrier = offer["owner"]
            airline_name = carrier["name"]
            airline_code = carrier["iata_code"]

            order_id = offer["id"]
            departure_slice_id = offer["slices"][0]["id"]
            departure_segment_ids = []
            for each_segment in offer["slices"][0]["segments"]:
                departure_segment_ids.append(each_segment["id"])
            
            departure_segments = offer["slices"][0]["segments"]
            departure_segments_str = []
            for leg in departure_segments:
                leg_pair = [leg["origin"]["iata_code"], leg["destination"]["iata_code"]]
                departure_segments_str.append(leg_pair)

            total_amount = offer["total_amount"]
            total_currency = offer["total_currency"]
            duffel_call_time = offer["created_at"]

            # For all the segments (we put a "[0]" after "[slices]" because it is a one way ticket):
            segments = offer["slices"][0]["segments"]
            segment_origin_destination_pairs = []
            for leg in segments:
                leg_pair = [leg["origin"]["iata_code"], leg["destination"]["iata_code"]]
                segment_origin_destination_pairs.append(leg_pair)

            if return_date_str:
                
                return_time = offer["slices"][1]["segments"][0]["departing_at"]
                return_arrival_time = offer["slices"][1]["segments"][-1]["arriving_at"]

                return_slice_id = offer["slices"][1]["id"]
                return_segment_ids = []
                for each_segment in offer["slices"][1]["segments"]:
                    return_segment_ids.append(each_segment["id"])
                
                return_segments = offer["slices"][1]["segments"]
                return_segments_str = []
                for leg in return_segments:
                    leg_pair = [leg["origin"]["iata_code"], leg["destination"]["iata_code"]]
                    return_segments_str.append(leg_pair)
            
            else:
                return_date_str = ""
                return_time = ""
                return_arrival_time = ""
                return_slice_id = ""
                return_segment_ids = ""
                return_segments_str = ""

            data_append = [origin,
                            destination,
                            passengers,
                            cabin_class,
                            departure_date_str,
                            departure_time,
                            departure_arrival_time,
                            return_date_str,
                            return_time,
                            return_arrival_time,
                            airline_name,
                            airline_code,
                            order_id,
                            departure_slice_id,
                            return_slice_id,
                            departure_segment_ids,
                            return_segment_ids,
                            departure_segments_str,
                            return_segments_str,
                            total_amount,
                            total_currency,
                            duffel_call_time]

            for i in range(len(data_saved_keys)):
                data_saved[data_saved_keys[i]].append(data_append[i])
            

    
    return data_saved



# "overwrite_previous_calls" is whether it should assume that if there is a flight being added with a certain combination of origin, destination,
# passengers, cabin_class, departure_date, and return_date, then all the flights with those same characteristics were just called, and it can
# safely overwrite any flights it currently has with those characteristics without worrying about losing data. In other words, the whole "call unit"
# is being refreshed
def add_flights_to_master_flight_list(flight_array, overwrite_previous_calls=True, database_name='master_flight_list.db'):
    # Connecting to the database
    data_dict = turn_master_flight_db_into_dict(database_name)

    columns = list(data_dict.keys())
    key_number = len(columns)
    
    # Now we delete outdated info
    if overwrite_previous_calls:
        call_unit_keys = CALL_UNIT_KEYS

        # Gathering all the different call units in the soon to be added flight_array
        all_call_units_added = []
        for i in range(len(flight_array[call_unit_keys[0]])):  # For each flight in flight_array
            call_units_i = []
            for key in call_unit_keys:
                call_units_i.append(flight_array[key][i])
            
            if call_units_i not in all_call_units_added:
                all_call_units_added.append(call_units_i)
        
        # Seeing which flights in the master list are now outdated
        deletion_index_list = []
        for i in range(len(data_dict[call_unit_keys[0]])):  # For each flight in the master list
            call_units_i = []
            for key in call_unit_keys:
                call_units_i.append(data_dict[key][i])
            
            if call_units_i in all_call_units_added:
                deletion_index_list.append(i)
        
        # Actually deleting them
        for i in range(len(deletion_index_list)):  # For each flight in the master list
            current_index = len(deletion_index_list) - 1 - i  # We work backwards when popping
            for key in columns:
                data_dict[key].pop(deletion_index_list[current_index])
    
    # Finally, we add the new flights
    for i in range(len(flight_array[call_unit_keys[0]])):  # For each flight in flight_array
        for key in columns:
            data_dict[key].append(flight_array[key][i])
    
    # And save it
    conn = sqlite3.connect('master_flight_list.db')
    c = conn.cursor()

    c.execute(f'''
                DELETE FROM flights
            ''')

    columns_as_one_string = ''
    for i in range(len(columns)):
        columns_as_one_string += columns[i]
        if i != key_number - 1:
            columns_as_one_string += ', '

    unknown_string = ''
    for i in range(key_number):
        unknown_string += '?'
        if i != key_number - 1:
            unknown_string += ', '

    for i in range(len(data_dict[call_unit_keys[0]])):  # For each flight in the master list
        data_append = []
        for key in columns:
            if type(data_dict[key][i]) == list:
                data_append.append(str(data_dict[key][i]))
            else:
                data_append.append(data_dict[key][i])

        c.execute(f'''
                INSERT INTO flights ({columns_as_one_string})
                VALUES ({unknown_string})
            ''', data_append)
        conn.commit()

    conn.close()



def get_all_call_unit_keys_in_dict(data_dict):
    call_unit_keys = CALL_UNIT_KEYS

    all_dict_call_units = []
    for i in range(len(data_dict[call_unit_keys[0]])):  # For each flight in flight_array
        call_units_i = []
        for key in call_unit_keys:
            call_units_i.append(data_dict[key][i])
        
        if call_units_i not in all_dict_call_units:
            all_dict_call_units.append(call_units_i)
    
    return all_dict_call_units


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


# This calls all the possible routings from Duffel
def get_dict_for_all_possible_routings(origin, destination, passengers, cabin_class, departure_date_str, return_date_str=None):
    whole_flights = get_dict_for_route(origin, destination, passengers, cabin_class, departure_date_str, return_date_str=return_date_str)
    columns = list(whole_flights.keys())

    final_flight_array = {}
    for key in columns:
        final_flight_array[key] = []
    
    # We make sure to add whole_flights to the master list if it isn't there
    final_flight_array = combine_packed_flight_arrays([final_flight_array, whole_flights])
    

    if not return_date_str:
        return_date_str = ""

    # We search for all the flights that fill segments of the whole flights
    relevant_departure_segments = []
    relevant_return_segments = []
    
    for i in range(len(whole_flights[columns[0]])):  # For every whole flight found
        flight_segments = whole_flights['departure_segments'][i]
        if len(flight_segments) > 1 or return_date_str:  # We don't need to check direct flights if it is one way, we've already done that
            for i in range(len(flight_segments)):
                considered_leg = flight_segments[i]

                if considered_leg not in relevant_departure_segments:
                    relevant_departure_segments.append(considered_leg)
        
        if return_date_str:  # If it is roundtrip
            flight_segments = whole_flights['return_segments'][i]
            for i in range(len(flight_segments)):
                considered_leg = flight_segments[i]

                if considered_leg not in relevant_return_segments:
                    relevant_return_segments.append(considered_leg)

    all_relevant_segments = relevant_departure_segments + relevant_return_segments

    # We call them all and add them to final_flight_array. Only one way flights for synthetic routing
    for segment in all_relevant_segments:
        print(segment)
        all_flights_in_segment = get_dict_for_route(segment[0], segment[1], passengers, cabin_class, departure_date_str)
        final_flight_array = combine_packed_flight_arrays([final_flight_array, all_flights_in_segment])
    
    return final_flight_array


# This looks for the segments, to be able to do synthetic routing. Different from "call_all_possible_routings()" because it only looks in the master list, doesn't call new ones. Also finds possible leg orderings
def find_possible_routings_from_master_list(origin, destination, passengers, cabin_class, departure_date_str, return_date_str=None, database_name='master_flight_list.db'):
    data_dict = turn_master_flight_db_into_dict(database_name=database_name)
    columns = list(data_dict.keys())

    call_units_in_master = get_all_call_unit_keys_in_dict(data_dict)

    if not return_date_str:
        return_date_str = ""
    
    whole_call_unit = [origin, destination, passengers, cabin_class, departure_date_str, return_date_str]

    if whole_call_unit not in call_units_in_master:
        raise FileNotFoundError("The whole flight is not in the master list; add it before synthetic routings can be found")
    else:
        # We search for all the flights that fill segments of the whole flights
        relevant_departure_segments = []
        relevant_return_segments = []
        
        for i in range(len(data_dict[columns[0]])):  # For every flight in the master list
            same_call_unit = True
            for call_unit_key in CALL_UNIT_KEYS:
                if data_dict[call_unit_key][i] != whole_call_unit[CALL_UNIT_KEYS.index(call_unit_key)]:  # If any of the details of the flight differ
                    same_call_unit = False

            if same_call_unit:  # Then we add its segments to the list
                flight_segments = data_dict['departure_segments'][i]
                if len(flight_segments) > 1 or return_date_str:  # We don't need to check direct flights if it is one way, we've already done that
                    for i in range(len(flight_segments)):
                        considered_leg = flight_segments[i]

                        if considered_leg not in relevant_departure_segments:
                            relevant_departure_segments.append(considered_leg)
                
                if return_date_str:  # If it is roundtrip
                    flight_segments = data_dict['return_segments'][i]
                    for i in range(len(flight_segments)):
                        considered_leg = flight_segments[i]

                        if considered_leg not in relevant_return_segments:
                            relevant_return_segments.append(considered_leg)
        
        # Now we actually find the flights we need, not just their origins and destinations. We only look at one way flights for synthetic routing
        inbetween_departure_flights = {}
        for key in columns:
            inbetween_departure_flights[key] = []
        
        for segment in relevant_departure_segments:
            wanted_call_unit = [segment[0], segment[1], passengers, cabin_class, departure_date_str, ""]

            for i in range(len(data_dict[columns[0]])):  # For every flight in the master list
                same_call_unit = True
                for call_unit_key in CALL_UNIT_KEYS:
                    if data_dict[call_unit_key][i] != wanted_call_unit[CALL_UNIT_KEYS.index(call_unit_key)]:  # If any of the details of the flight differ
                        same_call_unit = False
                
                if same_call_unit:
                    for key in columns:
                        inbetween_departure_flights[key].append(data_dict[key][i])
        
        if return_date_str:
            inbetween_return_flights = {}
            for key in columns:
                inbetween_return_flights[key] = []
            
            for segment in relevant_return_segments:
                wanted_call_unit = [segment[0], segment[1], passengers, cabin_class, return_date_str, ""]

                for i in range(len(data_dict[columns[0]])):  # For every flight in the master list
                    same_call_unit = True
                    for call_unit_key in CALL_UNIT_KEYS:
                        if data_dict[call_unit_key][i] != wanted_call_unit[CALL_UNIT_KEYS.index(call_unit_key)]:  # If any of the details of the flight differ
                            same_call_unit = False
                    
                    if same_call_unit:
                        for key in columns:
                            inbetween_return_flights[key].append(data_dict[key][i])
        
        # And we unpack the flights according to their origin and destination (the passengers, cabin class, and dates will be the same across them all), and start looking for synthetic routings
        inbetween_dep = unpack_flight_array(inbetween_departure_flights, id_keys=("origin", "destination"))
        
        dep_leg_list = []
        for origin_destination in list(inbetween_dep.keys()):
            dep_leg_list.append(origin_destination)
        
        dep_all_leg_orders = get_all_valid_leg_orders(origin, destination, dep_leg_list)


        if return_date_str:
            inbetween_ret = unpack_flight_array(inbetween_return_flights, id_keys=("origin", "destination"))

            ret_leg_list = []
            for origin_destination in list(inbetween_ret.keys()):
                ret_leg_list.append(origin_destination)
            
            ret_all_leg_orders = get_all_valid_leg_orders(destination, origin, ret_leg_list)
        else:
            inbetween_ret = {}
            ret_all_leg_orders = []
        
        return [inbetween_dep, dep_all_leg_orders, inbetween_ret, ret_all_leg_orders]
        












# For testing (note that no synthetic routing works for the example below, since the return flights are all direct. I just chose
# it because the results are few and manageable for first class):

lhr_dxb_all_routings = get_dict_for_all_possible_routings('LHR', 'DXB', 2, 'first', '2025-08-14', return_date_str='2025-08-21')

add_flights_to_master_flight_list(lhr_dxb_all_routings)

result = find_possible_routings_from_master_list('LHR', 'DXB', 2, 'first', '2025-08-14', return_date_str='2025-08-21')

if result[0]:
    departure_dict = repack_flight_array(result[0], ("origin", "destination"))
else:
    departure_dict = {}

if result[2]:
    return_dict = repack_flight_array(result[2], ("origin", "destination"))
else:
    return_dict = {}

save_dict_to_csv(departure_dict, 'test_departure_synthetic_routing_segments.csv')
print('All leg orders for the departure:', result[1])
save_dict_to_csv(return_dict, 'test_return_synthetic_routing_segments.csv')
print('All leg orders for the return:', result[3])


