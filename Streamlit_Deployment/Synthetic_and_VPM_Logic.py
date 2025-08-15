import sqlite3
from datetime import date, timedelta
import requests
import time
import json
import pandas as pd

DUFFEL_ACCESS_TOKEN = "duffel_test_0hhjFKDZZskobddilp6wH6oQd-fQWp0U3Mdv-3eogXN"

# This uses "master_flight_list.db" to store its information

DATABASE_COLUMNS = ["origin", "destination", "passengers", "cabin_class", "departure_date", "departure_time", "departure_arrival_time", "return_date", "return_time", "return_arrival_time", "airline_name", "airline_code", "order_id", "departure_slice_id", "return_slice_id", "departure_segment_ids", "return_segment_ids", "departure_segments", "return_segments", "total_amount", "estimated_price_in_miles", "overall_value", "total_currency", "duffel_call_time"]
DATABASE_COLUMNS_TYPES = ["TEXT", "TEXT", "INTEGER", "TEXT", "TEXT", "TEXT", "TEXT", "TEXT", "TEXT", "TEXT", "TEXT", "TEXT", "TEXT", "TEXT", "TEXT", "TEXT", "TEXT", "TEXT", "TEXT", "REAL", "REAL", "REAL", "TEXT", "TEXT"]

KEY_NUMBER = len(DATABASE_COLUMNS)
UNKNOWN_STRING = ''
COLUMNS_AS_ONE_STRING = ''
COLUMNS_WITH_TYPES_AS_ONE_STRING = ''
for i in range(KEY_NUMBER):
    UNKNOWN_STRING += '?'
    COLUMNS_AS_ONE_STRING += DATABASE_COLUMNS[i]
    COLUMNS_WITH_TYPES_AS_ONE_STRING += DATABASE_COLUMNS[i] + ' ' + DATABASE_COLUMNS_TYPES[i]
    if i != KEY_NUMBER - 1:
        UNKNOWN_STRING += ', '
        COLUMNS_AS_ONE_STRING += ', '
        COLUMNS_WITH_TYPES_AS_ONE_STRING += ', '


CALL_UNIT_KEYS = ["origin", "destination", "passengers", "cabin_class", "departure_date", "return_date"]
LIST_AS_STRING_KEYS = ["departure_segment_ids", "return_segment_ids", "departure_segments", "return_segments"]

AVERAGE_VPM_BY_AIRLINE = {
    "AS" : 1.3,
    "AA" : 1.6,
    "DL" : 1.2,
    "F9" : 1.5,
    "HA" : 1.0,
    "B6" : 1.5,
    "WN" : 1.3,
    "NK" : 1.3,
    "UA" : 1.2,
    "AC" : 1.1,
    "AV" : 1.6,
    "BA" : 1.2,
    "AF" : 0.8,
    "TK" : 0.7,
    "VS" : 1.4,
    "EK" : 0.6,
}
DEFAULT_VPM = 1

PERCEIVED_VALUE_BY_AIRLINE = {
    "AS" : 1.5,
    "AA" : 2,
    "DL" : 1.5,
    "F9" : 1,
    "HA" : 1.5,
    "B6" : 1.2,
    "WN" : 1.2,
    "NK" : 1,
    "UA" : 1.5,
    "AC" : 2,
    "AV" : 1.2,
    "BA" : 1.5,
    "AF" : 2,
    "TK" : 2,
    "VS" : 1.5,
    "EK" : 3,
}
DEFAULT_PERCEIVED_VALUE = 1

AIRLINE_CODE_TO_NAME = {
    "AS" : "Alaska Airlines",
    "AA" : "American Airlines",
    "DL" : "Delta Airlines",
    "F9" : "Frontier Airlines",
    "HA" : "Hawaiian Airlines",
    "B6" : "JetBlue Airways",
    "WN" : "Southwest Airlines",
    "NK" : "Spirit Airlines",
    "UA" : "United Airlines",
    "AC" : "Air Canada",
    "AV" : "Avianca",
    "BA" : "British Airways",
    "AF" : "Air France",
    "TK" : "Turkish Airlines",
    "VS" : "Virgin Atlantic",
    "EK" : "Emirates Airlines",
}

PARTNER_AIRLINES_IATA = list(AVERAGE_VPM_BY_AIRLINE.keys())

IGNORED_AIRLINES = ["ZZ"]

# Just for viewing purposes, for debugging
def save_dict_to_csv(data_dict, output_file='master_flight_list_test.csv'):
    df_final = pd.DataFrame(data_dict)
    df_final.to_csv(output_file, index=False)


def turn_master_flight_db_into_dict(database_name='master_flight_list.db'):
    conn = sqlite3.connect(database_name)
    c = conn.cursor()

    c.execute(f'''
        CREATE TABLE IF NOT EXISTS flights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            {COLUMNS_WITH_TYPES_AS_ONE_STRING}
        )
    ''')
    conn.commit()



    # Now we get all the flights currently in the database
    c.execute(f'SELECT {COLUMNS_AS_ONE_STRING} FROM flights')
    rows = c.fetchall()

    # Convert to dictionary format similar to previous CSV logic
    data_dict = {col: [] for col in DATABASE_COLUMNS}
    for row in rows:
        for i, col in enumerate(DATABASE_COLUMNS):
            data_dict[col].append(row[i])

    for list_key in LIST_AS_STRING_KEYS:
        list_key_values = data_dict[list_key]
        for i in range(len(list_key_values)):
            if list_key_values[i]:
                list_key_with_double_quotes = list_key_values[i].replace("\'", "\"")
                list_key_values[i] = json.loads(list_key_with_double_quotes)  # Remember that list mutability will carry the changes to "data_dict"
    
    return data_dict


def airline_code_to_name(code):
    try:
        return AIRLINE_CODE_TO_NAME[code]
    except:
        raise IndexError("Not an airline in the dictionary")


def airline_name_to_code(name):
    for key in list(AIRLINE_CODE_TO_NAME.keys()):
        if AIRLINE_CODE_TO_NAME[key] == name:
            return key
        
    raise IndexError("Not an airline in the dictionary")


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
    data_saved = {}
    for key in DATABASE_COLUMNS:
        data_saved[key] = []

    data_saved_keys = list(data_saved.keys())

    access_token = DUFFEL_ACCESS_TOKEN
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
            total_amount_float = float(total_amount)
            if airline_code in PARTNER_AIRLINES_IATA:
                estimated_price_in_miles = str(round(total_amount_float * 100 / AVERAGE_VPM_BY_AIRLINE[airline_code]))
                overall_value = str(round(total_amount_float / PERCEIVED_VALUE_BY_AIRLINE[airline_code], 2))
            else:
                estimated_price_in_miles = str(round(total_amount_float * 100 / DEFAULT_VPM))
                overall_value = str(round(total_amount_float / DEFAULT_PERCEIVED_VALUE, 2))

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
                            estimated_price_in_miles,
                            overall_value,
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

    DATABASE_COLUMNS
    
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
            for key in DATABASE_COLUMNS:
                data_dict[key].pop(deletion_index_list[current_index])
    
    # Finally, we add the new flights
    for i in range(len(flight_array[call_unit_keys[0]])):  # For each flight in flight_array
        for key in DATABASE_COLUMNS:
            data_dict[key].append(flight_array[key][i])
    
    # And save it
    conn = sqlite3.connect('master_flight_list.db')
    c = conn.cursor()

    c.execute(f'''
                DELETE FROM flights
            ''')

    for i in range(len(data_dict[call_unit_keys[0]])):  # For each flight in the master list
        data_append = []
        for key in DATABASE_COLUMNS:
            if type(data_dict[key][i]) == list:
                data_append.append(str(data_dict[key][i]))
            else:
                data_append.append(data_dict[key][i])

        c.execute(f'''
                INSERT INTO flights ({COLUMNS_AS_ONE_STRING})
                VALUES ({UNKNOWN_STRING})
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
    
    # Now we turn the indices back into the real legs when we return it

    valid_leg_orders_unindexed = []
    for leg_order in all_valid_leg_orders:
        valid_leg_orders_unindexed.append([])
        for index in leg_order:
            valid_leg_orders_unindexed[-1].append(leg_list[index])

    return valid_leg_orders_unindexed


# This gets flights from the db
def find_flights_in_master_list(origin, destination, passengers, cabin_class, departure_date_str, return_date_str=None, database_name='master_flight_list.db'):
    flight_array = {}
    for key in DATABASE_COLUMNS:
        flight_array[key] = []
    
    data_dict = turn_master_flight_db_into_dict(database_name=database_name)

    call_units_in_master = get_all_call_unit_keys_in_dict(data_dict)

    if not return_date_str:
        return_date_str = ""
    
    whole_call_unit = [origin, destination, passengers, cabin_class, departure_date_str, return_date_str]

    if whole_call_unit not in call_units_in_master:
        return flight_array
    else:
        for i in range(len(data_dict[DATABASE_COLUMNS[0]])):  # For every flight in the master list
            same_call_unit = True
            for call_unit_key in CALL_UNIT_KEYS:
                if data_dict[call_unit_key][i] != whole_call_unit[CALL_UNIT_KEYS.index(call_unit_key)]:  # If any of the details of the flight differ
                    same_call_unit = False
            
            if same_call_unit:
                for key in DATABASE_COLUMNS:
                    flight_array[key].append(data_dict[key][i])
    
    return flight_array


# This calls all the possible routings from Duffel
def get_dict_for_all_possible_routings(origin, destination, passengers, cabin_class, departure_date_str, return_date_str=None, use_old_calls=True):
    if use_old_calls:
        in_master = find_flights_in_master_list(origin, destination, passengers, cabin_class, departure_date_str, return_date_str=return_date_str)
        if len(in_master[DATABASE_COLUMNS[0]]) > 0:
            whole_flights = in_master
        else:
            whole_flights = get_dict_for_route(origin, destination, passengers, cabin_class, departure_date_str, return_date_str=return_date_str)
    else:
        whole_flights = get_dict_for_route(origin, destination, passengers, cabin_class, departure_date_str, return_date_str=return_date_str)

    final_flight_array = {}
    for key in DATABASE_COLUMNS:
        final_flight_array[key] = []
    
    # We make sure to add whole_flights to the master list if it isn't there
    final_flight_array = combine_packed_flight_arrays([final_flight_array, whole_flights])
    

    if not return_date_str:
        return_date_str = ""

    # We search for all the flights that fill segments of the whole flights
    relevant_departure_segments = []
    relevant_return_segments = []
    
    for i in range(len(whole_flights[DATABASE_COLUMNS[0]])):  # For every whole flight found
        flight_segments = whole_flights['departure_segments'][i]
        if len(flight_segments) > 1 or return_date_str:  # We don't need to check direct flights if it is one way, we've already done that
            for j in range(len(flight_segments)):
                considered_leg = flight_segments[j]

                if considered_leg not in relevant_departure_segments:
                    relevant_departure_segments.append(considered_leg)
        
        if return_date_str:  # If it is roundtrip
            flight_segments = whole_flights['return_segments'][i]
            for j in range(len(flight_segments)):
                considered_leg = flight_segments[j]

                if considered_leg not in relevant_return_segments:
                    relevant_return_segments.append(considered_leg)

    # We call them all and add them to final_flight_array. Only one way flights for synthetic routing
    for segment in relevant_departure_segments:
        if use_old_calls:
            in_master = find_flights_in_master_list(segment[0], segment[1], passengers, cabin_class, departure_date_str)
            if len(in_master[DATABASE_COLUMNS[0]]) > 0:
                all_flights_in_segment = in_master
            else:
                all_flights_in_segment = get_dict_for_route(segment[0], segment[1], passengers, cabin_class, departure_date_str)
        else:
            all_flights_in_segment = get_dict_for_route(segment[0], segment[1], passengers, cabin_class, departure_date_str)

        final_flight_array = combine_packed_flight_arrays([final_flight_array, all_flights_in_segment])
    
    for segment in relevant_return_segments:
        if use_old_calls:
            in_master = find_flights_in_master_list(segment[0], segment[1], passengers, cabin_class, return_date_str)
            if len(in_master[DATABASE_COLUMNS[0]]) > 0:
                all_flights_in_segment = in_master
            else:
                all_flights_in_segment = get_dict_for_route(segment[0], segment[1], passengers, cabin_class, return_date_str)
        else:
            all_flights_in_segment = get_dict_for_route(segment[0], segment[1], passengers, cabin_class, return_date_str)

        final_flight_array = combine_packed_flight_arrays([final_flight_array, all_flights_in_segment])
    
    return final_flight_array


# This looks for the segments, to be able to do synthetic routing. Different from "call_all_possible_routings()" because it only looks in the master list, doesn't call new ones. Also finds possible leg orderings
def find_possible_routings_from_master_list(origin, destination, passengers, cabin_class, departure_date_str, return_date_str=None, database_name='master_flight_list.db'):
    data_dict = turn_master_flight_db_into_dict(database_name=database_name)

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
        
        for i in range(len(data_dict[DATABASE_COLUMNS[0]])):  # For every flight in the master list
            same_call_unit = True
            for call_unit_key in CALL_UNIT_KEYS:
                if data_dict[call_unit_key][i] != whole_call_unit[CALL_UNIT_KEYS.index(call_unit_key)]:  # If any of the details of the flight differ
                    same_call_unit = False

            if same_call_unit:  # Then we add its segments to the list
                flight_segments = data_dict['departure_segments'][i]  # We include whole flights
                for j in range(len(flight_segments)):
                    considered_leg = flight_segments[j]

                    if considered_leg not in relevant_departure_segments:
                        relevant_departure_segments.append(considered_leg)
                
                if return_date_str:  # If it is roundtrip
                    flight_segments = data_dict['return_segments'][i]
                    for j in range(len(flight_segments)):
                        considered_leg = flight_segments[j]

                        if considered_leg not in relevant_return_segments:
                            relevant_return_segments.append(considered_leg)
        
        # Now we actually find the flights we need, not just their origins and destinations. We only look at one way flights for synthetic routing
        inbetween_departure_flights = {}
        for key in DATABASE_COLUMNS:
            inbetween_departure_flights[key] = []
        
        for segment in relevant_departure_segments:
            wanted_call_unit = [segment[0], segment[1], passengers, cabin_class, departure_date_str, ""]

            for i in range(len(data_dict[DATABASE_COLUMNS[0]])):  # For every flight in the master list
                same_call_unit = True
                for call_unit_key in CALL_UNIT_KEYS:
                    if data_dict[call_unit_key][i] != wanted_call_unit[CALL_UNIT_KEYS.index(call_unit_key)]:  # If any of the details of the flight differ
                        same_call_unit = False
                
                if same_call_unit:
                    for key in DATABASE_COLUMNS:
                        inbetween_departure_flights[key].append(data_dict[key][i])
        
        if return_date_str:
            inbetween_return_flights = {}
            for key in DATABASE_COLUMNS:
                inbetween_return_flights[key] = []
            
            for segment in relevant_return_segments:
                wanted_call_unit = [segment[0], segment[1], passengers, cabin_class, return_date_str, ""]

                for i in range(len(data_dict[DATABASE_COLUMNS[0]])):  # For every flight in the master list
                    same_call_unit = True
                    for call_unit_key in CALL_UNIT_KEYS:
                        if data_dict[call_unit_key][i] != wanted_call_unit[CALL_UNIT_KEYS.index(call_unit_key)]:  # If any of the details of the flight differ
                            same_call_unit = False
                    
                    if same_call_unit:
                        for key in DATABASE_COLUMNS:
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
        

def delete_unchosen_airline_flights(unpacked_flight_array, chosen_airlines_IATA):
    # Note this uses an "unpacked" flight array, so the keys will be like "(LHR, DXB)"
    if not unpacked_flight_array:
        print("Error, empty flight array")
        return None

    trimmed_dict = {}
    outer_keys = list(unpacked_flight_array.keys())
    inner_keys = list(unpacked_flight_array[outer_keys[0]].keys())
    for key in outer_keys:
        trimmed_dict[key] = {}
        for inner_key in inner_keys:
            trimmed_dict[key][inner_key] = []

        for i in range(len(unpacked_flight_array[key]["airline_code"])):
            if unpacked_flight_array[key]["airline_code"][i] in chosen_airlines_IATA:
                for inner_key in inner_keys:
                    trimmed_dict[key][inner_key].append(unpacked_flight_array[key][inner_key][i])
    
    return trimmed_dict


# This to get rid of the fake "Duffel Airways" flights
def delete_chosen_airline_flights(unpacked_flight_array, chosen_airlines_IATA):
    # Note this uses an "unpacked" flight array, so the keys will be like "(LHR, DXB)"
    if not unpacked_flight_array:
        print("Error, empty flight array")
        return None

    trimmed_dict = {}
    outer_keys = list(unpacked_flight_array.keys())
    inner_keys = list(unpacked_flight_array[outer_keys[0]].keys())
    for key in outer_keys:
        trimmed_dict[key] = {}
        for inner_key in inner_keys:
            trimmed_dict[key][inner_key] = []

        for i in range(len(unpacked_flight_array[key]["airline_code"])):
            if unpacked_flight_array[key]["airline_code"][i] not in chosen_airlines_IATA:
                for inner_key in inner_keys:
                    trimmed_dict[key][inner_key].append(unpacked_flight_array[key][inner_key][i])
    
    return trimmed_dict



def get_sort_indices(sort_list):
    list_copy = sort_list.copy()
    iterable = []
    for i in range(len(list_copy)):
        iterable.append(i)
    
    current_index = 1
    while current_index < len(list_copy):
        if list_copy[current_index] < list_copy[current_index - 1]:
            old = list_copy[current_index]
            list_copy[current_index] = list_copy[current_index - 1]
            list_copy[current_index - 1] = old

            old_index = iterable[current_index]
            iterable[current_index] = iterable[current_index - 1]
            iterable[current_index - 1] = old_index
            if current_index > 1:
                current_index -= 1
        else:
            current_index += 1
    
    return iterable


def sort_dict_by_one_list(main_dict, sort_key, reverse=False):
    new_dict = {}
    key_list = list(main_dict.keys())

    sort_indices = get_sort_indices(main_dict[sort_key])

    for key in key_list:
        new_dict[key] = []
        for i in range(len(main_dict[key])):
            if not reverse:
                new_dict[key].append(main_dict[key][sort_indices[i]])
            else:
                backwards_index = len(main_dict[key]) - 1 - i
                new_dict[key].append(main_dict[key][sort_indices[backwards_index]])
    
    return new_dict



def sort_dict_by_lists_sequentially(main_dict, sort_key_list, reverse_list=None):
    if not reverse_list:
        reverse_list = [False] * len(sort_key_list)
    
    new_dict_pieces = [main_dict]
    key_list = list(main_dict.keys())

    for i in range(len(sort_key_list)):
        this_sort_key = sort_key_list[i]

        old_dict_pieces = new_dict_pieces
        new_dict_pieces = []
        for dict_piece in old_dict_pieces:
            sort_indices = get_sort_indices(dict_piece[this_sort_key])

            sorted_piece = {}
            for key in key_list:
                sorted_piece[key] = []
                for j in range(len(dict_piece[key])):
                    if not reverse_list[i]:
                        sorted_piece[key].append(dict_piece[key][sort_indices[j]])
                    else:
                        backwards_index = len(dict_piece[key]) - 1 - j
                        sorted_piece[key].append(dict_piece[key][sort_indices[backwards_index]])
            
            gathering_dict = {}
            for j in range(len(sorted_piece[this_sort_key])):
                item = sorted_piece[this_sort_key][j]
                if item not in list(gathering_dict.keys()):
                    gathering_dict[item] = []
                
                gathering_dict[item].append(j)
            
            for item in list(gathering_dict.keys()):
                temp_dict = {}
                for key in key_list:
                    temp_dict[key] = []
                
                for index in gathering_dict[item]:
                    for key in key_list:
                        temp_dict[key].append(sorted_piece[key][index])

                new_dict_pieces.append(temp_dict)
    
    final_dict = {}
    for key in key_list:
        final_dict[key] = []
    
    for i in range(len(new_dict_pieces)):
        final_dict = combine_packed_flight_arrays([final_dict, new_dict_pieces[i]])
    
    return final_dict




def get_all_lists_of_length_n_with_base_b(b, n):
    all_lists = []
    starter_list = [0] * n

    while starter_list != [b - 1] * n:
        all_lists.append(starter_list.copy())
        if starter_list[-1] == b - 1:
            search_index = -2
            while True:
                if starter_list[search_index] == b - 1:
                    search_index -= 1
                else:
                    break
            starter_list[search_index] += 1
            fill_index = search_index + 1
            while fill_index < 0:
                starter_list[fill_index] = 0
                fill_index += 1
        else:
            starter_list[-1] += 1
    
    all_lists.append(starter_list.copy())
    
    return all_lists




def get_top_n_flight_combos(unpacked_flight_array, n, all_leg_orders, sort_key):
    # We sort the list
    all_flight_keys = list(unpacked_flight_array.keys())
    for key in all_flight_keys:
        unpacked_flight_array[key] = sort_dict_by_one_list(unpacked_flight_array[key], sort_key)

    total_itineraries = len(all_leg_orders)
    itinerary_min_list = [0] * total_itineraries
    itinerary_base_list = [1] * total_itineraries
    tapped_out_itineraries = [False] * total_itineraries

    itinerary_attempted_search_indices = []
    for i in range(len(all_leg_orders)):
        itinerary_attempted_search_indices.append([])

    indexing_dicts = {
        "key_lists" : [],
        "index_lists" : [],
        "values" : [],
    }

    while len(indexing_dicts["key_lists"]) < n and False in tapped_out_itineraries:
        last_least_itinerary_value = min(itinerary_min_list)
        last_least_itinerary_index = itinerary_min_list.index(last_least_itinerary_value)
        while tapped_out_itineraries[last_least_itinerary_index]:
            itinerary_min_list[last_least_itinerary_index] = max(itinerary_min_list) + 1000000  # We just don't want to choose this itinerary again

            last_least_itinerary_value = min(itinerary_min_list)
            last_least_itinerary_index = itinerary_min_list.index(last_least_itinerary_value)

        current_leg_order = all_leg_orders[last_least_itinerary_index]

        # We figure out which untried combination results in the cheapest total
        all_leg_flight_index_combos = get_all_lists_of_length_n_with_base_b(itinerary_base_list[last_least_itinerary_index], len(current_leg_order))

        untried_combos = []
        matching_values = []
        for i in range(len(all_leg_flight_index_combos)):
            current_combo = all_leg_flight_index_combos[i]
            if current_combo not in itinerary_attempted_search_indices[last_least_itinerary_index]:
                indices_too_high = False
                for j in range(len(current_combo)):
                    if current_combo[j] >= len(unpacked_flight_array[current_leg_order[j]][sort_key]):
                        indices_too_high = True

                if not indices_too_high:
                    value_sum = 0
                    for j in range(len(current_combo)):
                        key_flight_dict = unpacked_flight_array[current_leg_order[j]]
                        value_contribution = key_flight_dict[sort_key][current_combo[j]]
                        value_sum += value_contribution
                    
                    untried_combos.append(current_combo)
                    matching_values.append(value_sum)
        
        if len(untried_combos) == 0:
            tapped_out = True
            for attempt in itinerary_attempted_search_indices[last_least_itinerary_index]:
                if itinerary_base_list[last_least_itinerary_index] - 1 in attempt:
                    tapped_out = False
            
            if tapped_out:
                tapped_out_itineraries[last_least_itinerary_index] = True
            else:
                itinerary_base_list[last_least_itinerary_index] += 1
        else:
            min_combo_index = matching_values.index(min(matching_values))

            indexing_dicts["key_lists"].append([])
            indexing_dicts["index_lists"].append([])
            indexing_dicts["values"].append(matching_values[min_combo_index])

            for i in range(len(current_leg_order)):
                indexing_dicts["key_lists"][-1].append(current_leg_order[i])
                indexing_dicts["index_lists"][-1].append(untried_combos[min_combo_index][i])
            
            itinerary_min_list[last_least_itinerary_index] = matching_values[min_combo_index]
            itinerary_attempted_search_indices[last_least_itinerary_index].append(untried_combos[min_combo_index])
    
    return indexing_dicts


def get_top_n_dep_ret_combos(dep_indexing_dicts, ret_indexing_dicts, n):
    # We sort the lists
    dep_indexing_dicts = sort_dict_by_one_list(dep_indexing_dicts, "values")
    dep_length = len(dep_indexing_dicts["values"])
    ret_indexing_dicts = sort_dict_by_one_list(ret_indexing_dicts, "values")
    ret_length = len(ret_indexing_dicts["values"])
    tapped_out = False

    current_base = 1

    attempted_search_indices = []

    dep_ret_pairs = {
        "dep_key_lists" : [],
        "dep_index_lists" : [],
        "ret_key_lists" : [],
        "ret_index_lists" : [],
        "values" : [],
    }

    while len(dep_ret_pairs["values"]) < n and not tapped_out:
        all_index_combos = get_all_lists_of_length_n_with_base_b(current_base, 2)

        untried_combos = []
        matching_values = []
        for i in range(len(all_index_combos)):
            current_combo = all_index_combos[i]
            a = current_combo[0]
            b = current_combo[1]
            if current_combo not in attempted_search_indices:
                if a < dep_length and b < ret_length:
                    value_sum = dep_indexing_dicts["values"][a] + ret_indexing_dicts["values"][b]
                    
                    untried_combos.append(current_combo)
                    matching_values.append(value_sum)
        
        if len(untried_combos) == 0:
            tapped_out = True
            for attempt in attempted_search_indices:
                if current_base - 1 in attempt:
                    tapped_out = False
            current_base += 1
        else:
            min_combo_index = matching_values.index(min(matching_values))

            a = untried_combos[min_combo_index][0]
            b = untried_combos[min_combo_index][1]
            dep_ret_pairs["dep_key_lists"].append(dep_indexing_dicts["key_lists"][a])
            dep_ret_pairs["dep_index_lists"].append(dep_indexing_dicts["index_lists"][a])
            dep_ret_pairs["ret_key_lists"].append(ret_indexing_dicts["key_lists"][b])
            dep_ret_pairs["ret_index_lists"].append(ret_indexing_dicts["index_lists"][b])
            dep_ret_pairs["values"].append(matching_values[min_combo_index])
            
            
            attempted_search_indices.append(untried_combos[min_combo_index])
    
    return dep_ret_pairs
        

def get_dicts_of_top_n_sorted_synthetic_flights(n, sort_key, origin, destination, passengers, cabin_class, departure_date_str, return_date_str=None, deleted_airlines=None, kept_airlines=None, database_name='master_flight_list.db'):
    result = find_possible_routings_from_master_list(origin, destination, passengers, cabin_class, departure_date_str, return_date_str=return_date_str, database_name=database_name)

    full_departure_list = []
    full_return_list = []

    departure_dict = result[0]
    dep_leg_orders = result[1]
    return_dict = result[2]
    ret_leg_orders = result[3]

    # First we do any trimming of the dicts
    if deleted_airlines:
        departure_dict = delete_chosen_airline_flights(departure_dict, deleted_airlines)
        return_dict = delete_chosen_airline_flights(return_dict, deleted_airlines)
    if kept_airlines:
        departure_dict = delete_unchosen_airline_flights(departure_dict, kept_airlines)
        return_dict = delete_unchosen_airline_flights(return_dict, kept_airlines)


    for i in range(len(dep_leg_orders)):
        dep_leg_orders[i] = tuple(dep_leg_orders[i])
    for i in range(len(ret_leg_orders)):
        ret_leg_orders[i] = tuple(ret_leg_orders[i])
    
    full_values_list = []
    dep_indexing_dicts = get_top_n_flight_combos(departure_dict, n, dep_leg_orders, sort_key)
    if return_date_str:
        ret_indexing_dicts = get_top_n_flight_combos(return_dict, n, ret_leg_orders, sort_key)

        dep_ret_pairs = get_top_n_dep_ret_combos(dep_indexing_dicts, ret_indexing_dicts, n)
        dep_ret_pairs = sort_dict_by_one_list(dep_ret_pairs, "values")

        inner_dep_keys = list(departure_dict[dep_leg_orders[0][0]].keys())
        inner_ret_keys = list(return_dict[ret_leg_orders[0][0]].keys())

        for i in range(len(dep_ret_pairs["values"])):
            this_departure_dict = {}
            for key in dep_ret_pairs["dep_key_lists"][i]:
                this_departure_dict[key] = {}
                for inner_key in inner_dep_keys:
                    this_departure_dict[key][inner_key] = []
            
            this_return_dict = {}
            for key in dep_ret_pairs["ret_key_lists"][i]:
                this_return_dict[key] = {}
                for inner_key in inner_ret_keys:
                    this_return_dict[key][inner_key] = []
            
            for j in range(len(dep_ret_pairs["dep_key_lists"][i])):
                current_key = dep_ret_pairs["dep_key_lists"][i][j]
                for inner_key in inner_dep_keys:
                    this_departure_dict[current_key][inner_key].append(departure_dict[current_key][inner_key][dep_ret_pairs["dep_index_lists"][i][j]])

            for j in range(len(dep_ret_pairs["ret_key_lists"][i])):
                current_key = dep_ret_pairs["ret_key_lists"][i][j]
                for inner_key in inner_ret_keys:
                    this_return_dict[current_key][inner_key].append(return_dict[current_key][inner_key][dep_ret_pairs["ret_index_lists"][i][j]])
            
            this_departure_dict_repacked = repack_flight_array(this_departure_dict, ("origin", "destination"))
            this_return_dict_repacked = repack_flight_array(this_return_dict, ("origin", "destination"))

            full_departure_list.append(this_departure_dict_repacked)
            full_return_list.append(this_return_dict_repacked)

            full_values_list.append(dep_ret_pairs["values"][i])
    else:

        dep_indexing_dicts = sort_dict_by_one_list(dep_indexing_dicts, "values")
        inner_dep_keys = list(departure_dict[dep_leg_orders[0][0]].keys())

        for i in range(len(dep_indexing_dicts["values"])):
            this_departure_dict = {}
            for key in dep_indexing_dicts["key_lists"][i]:
                this_departure_dict[key] = {}
                for inner_key in inner_dep_keys:
                    this_departure_dict[key][inner_key] = []
            
            for j in range(len(dep_indexing_dicts["key_lists"][i])):
                current_key = dep_indexing_dicts["key_lists"][i][j]
                for inner_key in inner_dep_keys:
                    this_departure_dict[current_key][inner_key].append(departure_dict[current_key][inner_key][dep_indexing_dicts["index_lists"][i][j]])
            
            this_departure_dict_repacked = repack_flight_array(this_departure_dict, ("origin", "destination"))

            full_departure_list.append(this_departure_dict_repacked)
            this_return_dict = None
            full_return_list.append(this_return_dict)

            full_values_list.append(dep_indexing_dicts["values"][i])
    
    return [full_departure_list, full_return_list, full_values_list]
    
    
# The difference between this and "get_dicts_of_top_n_sorted_synthetic_flights" is that this includes whole flights for roundtrip bookings
def get_dicts_of_top_n_sorted_all_types_flights(n, sort_key, origin, destination, passengers, cabin_class, departure_date_str, return_date_str=None, deleted_airlines=None, kept_airlines=None, database_name='master_flight_list.db'):
    result = get_dicts_of_top_n_sorted_synthetic_flights(n, sort_key, origin, destination, passengers, cabin_class, departure_date_str, return_date_str=return_date_str, deleted_airlines=deleted_airlines, kept_airlines=kept_airlines, database_name=database_name)

    if not return_date_str:
        return result
    else:
        full_departure_list = result[0]
        full_return_list = result[1]
        full_values_list = result[2]

        synthetic_dict = {
            "dep_list" : full_departure_list,
            "ret_list" : full_return_list,
            "values" : full_values_list,
        }

        all_whole_flights = find_flights_in_master_list(origin, destination, passengers, cabin_class, departure_date_str, return_date_str=return_date_str)
        unpacked_whole_flights = unpack_flight_array(all_whole_flights, ("origin", "destination"))
        # Make sure to remove any undesired airlines
        if deleted_airlines:
            unpacked_whole_flights = delete_chosen_airline_flights(unpacked_whole_flights, deleted_airlines)
        if kept_airlines:
            unpacked_whole_flights = delete_unchosen_airline_flights(unpacked_whole_flights, kept_airlines)

        all_whole_flights = repack_flight_array(unpacked_whole_flights, ("origin", "destination"))
        # And sort
        all_whole_flights = sort_dict_by_one_list(all_whole_flights, sort_key)

        whole_dict = {
            "dep_list" : [],
            "ret_list" : [],
            "values" : [],
        }

        for i in range(len(all_whole_flights[DATABASE_COLUMNS[0]])):  # For flight in "all_whole_flights"
            dep_list_dict = {}
            for key in DATABASE_COLUMNS:
                dep_list_dict[key] = [all_whole_flights[key][i]]
            
            whole_dict["dep_list"].append(dep_list_dict)
            whole_dict["ret_list"].append(None)
            whole_dict["values"].append(dep_list_dict[sort_key][0])

        combined_dict = combine_packed_flight_arrays([synthetic_dict, whole_dict])  # The function is badly named, it is very general

        sorted_dict = sort_dict_by_one_list(combined_dict, "values")
        truncated_dict = {}
        for key in list(sorted_dict.keys()):
            truncated_dict[key] = sorted_dict[key][:n]
        

        final_departure_list = truncated_dict["dep_list"]
        final_return_list = truncated_dict["ret_list"]
        final_values_list = truncated_dict["values"]
    
        return [final_departure_list, final_return_list, final_values_list]
    
    
# "sort_mode" can be: "cheapest", "overall_value"
def get_useful_info_of_top_n_sorted_flights(n, sort_mode, origin, destination, passengers, cabin_class, departure_date_str, return_date_str=None, only_flights_with_award_airlines=False, airlines_with_miles=None, deleted_airlines=IGNORED_AIRLINES, database_name='master_flight_list.db'):
    useful_dict = {
        "is_synthetic" : [],
        "unique_id" : [],
        "dep_segments_str" : [],
        "dep_airline_codes" : [],
        "dep_airline_names" : [],
        "dep_time" : [],
        "ret_segments_str" : [],
        "ret_airline_codes" : [],
        "ret_airline_names" : [],
        "ret_time" : [],
        "cash_price" : [],
        "miles_price_by_airline_or_cash" : [],
        "vpm" : [],
        "overall_value" : [],
        "average_perceived_value": []
    }

    if sort_mode == "cheapest":
        sort_key = "total_amount"
    if sort_mode == "overall_value":
        sort_key = "overall_value"

    if only_flights_with_award_airlines:
        kept_airlines = airlines_with_miles
    else:
        kept_airlines = None
    
    if not airlines_with_miles:
        airlines_with_miles = []
    
    sorted_flights_result = get_dicts_of_top_n_sorted_all_types_flights(n, sort_key, origin, destination, passengers, cabin_class, departure_date_str, return_date_str=return_date_str, deleted_airlines=deleted_airlines, kept_airlines=kept_airlines, database_name=database_name)
    final_departure_list = sorted_flights_result[0]
    final_return_list = sorted_flights_result[1]
    final_values_list = sorted_flights_result[2]
    
    if not return_date_str:
        for i in range(len(final_departure_list)):
            this_dep_dict = final_departure_list[i]
            if len(this_dep_dict[DATABASE_COLUMNS[0]]) == 1:
                is_synthetic = False
            else:
                is_synthetic = True
            
            dep_segments_str = []
            dep_airline_codes = []
            dep_airline_names = []
            cash_price = 0
            overall_value = 0
            unique_id = ""
            miles_price_by_airline_or_cash = {}
            for i in range(len(this_dep_dict[DATABASE_COLUMNS[0]])):
                flight_segments = this_dep_dict["departure_segments"][i]
                constructing_str = ""
                for leg in flight_segments:
                    constructing_str += leg[0] + " -> "
                constructing_str += flight_segments[-1][-1]

                dep_segments_str.append(constructing_str)

                airline_code = this_dep_dict["airline_code"][i]
                dep_airline_codes.append(airline_code)
                airline_name = this_dep_dict["airline_name"][i]
                dep_airline_names.append(airline_name)

                cash_price += this_dep_dict["total_amount"][i]
                overall_value += this_dep_dict["overall_value"][i]

                unique_id += this_dep_dict["order_id"][i]

                if airline_code in airlines_with_miles:
                    if airline_code not in list(miles_price_by_airline_or_cash.keys()):
                        miles_price_by_airline_or_cash[airline_code] = 0
                    
                    miles_price_by_airline_or_cash[airline_code] += this_dep_dict["estimated_price_in_miles"][i]
                else:
                    if "cash" not in list(miles_price_by_airline_or_cash.keys()):
                        miles_price_by_airline_or_cash["cash"] = 0
                    
                    miles_price_by_airline_or_cash["cash"] += this_dep_dict["total_amount"][i]
                
            dep_time = this_dep_dict["departure_time"][0]

            ret_segments_str = None
            ret_airline_codes = None
            ret_airline_names = None
            ret_time = None

            useful_dict["is_synthetic"].append(is_synthetic)
            useful_dict["dep_segments_str"].append(dep_segments_str)
            useful_dict["dep_airline_codes"].append(dep_airline_codes)
            useful_dict["dep_airline_names"].append(dep_airline_names)
            useful_dict["dep_time"].append(dep_time)
            useful_dict["ret_segments_str"].append(ret_segments_str)
            useful_dict["ret_airline_codes"].append(ret_airline_codes)
            useful_dict["ret_airline_names"].append(ret_airline_names)
            useful_dict["ret_time"].append(ret_time)
            useful_dict["unique_id"].append(unique_id)
            useful_dict["cash_price"].append(cash_price)
            useful_dict["overall_value"].append(overall_value)
            useful_dict["miles_price_by_airline_or_cash"].append(miles_price_by_airline_or_cash)
    else:
        for i in range(len(final_departure_list)):
            this_dep_dict = final_departure_list[i]
            this_ret_dict = final_return_list[i]

            if this_ret_dict == None:
                is_synthetic = False
            else:
                is_synthetic = True
            


            dep_segments_str = []
            dep_airline_codes = []
            dep_airline_names = []
            cash_price = 0
            overall_value = 0
            unique_id = ""
            miles_price_by_airline_or_cash = {}
            for i in range(len(this_dep_dict[DATABASE_COLUMNS[0]])):
                flight_segments = this_dep_dict["departure_segments"][i]
                constructing_str = ""
                for leg in flight_segments:
                    constructing_str += leg[0] + " -> "
                constructing_str += flight_segments[-1][-1]

                dep_segments_str.append(constructing_str)

                airline_code = this_dep_dict["airline_code"][i]
                dep_airline_codes.append(airline_code)
                airline_name = this_dep_dict["airline_name"][i]
                dep_airline_names.append(airline_name)

                cash_price += this_dep_dict["total_amount"][i]
                overall_value += this_dep_dict["overall_value"][i]

                unique_id += this_dep_dict["order_id"][i]

                if airline_code in airlines_with_miles:
                    if airline_code not in list(miles_price_by_airline_or_cash.keys()):
                        miles_price_by_airline_or_cash[airline_code] = 0
                    
                    miles_price_by_airline_or_cash[airline_code] += this_dep_dict["estimated_price_in_miles"][i]
                else:
                    if "cash" not in list(miles_price_by_airline_or_cash.keys()):
                        miles_price_by_airline_or_cash["cash"] = 0
                    
                    miles_price_by_airline_or_cash["cash"] += this_dep_dict["total_amount"][i]
            
            dep_time = this_dep_dict["departure_time"][0]


            if is_synthetic:
                ret_segments_str = []
                ret_airline_codes = []
                ret_airline_names = []
                for i in range(len(this_ret_dict[DATABASE_COLUMNS[0]])):
                    flight_segments = this_ret_dict["departure_segments"][i]
                    constructing_str = ""
                    for leg in flight_segments:
                        constructing_str += leg[0] + " -> "
                    constructing_str += flight_segments[-1][-1]

                    ret_segments_str.append(constructing_str)

                    airline_code = this_ret_dict["airline_code"][i]
                    ret_airline_codes.append(airline_code)
                    airline_name = this_ret_dict["airline_name"][i]
                    ret_airline_names.append(airline_name)

                    cash_price += this_ret_dict["total_amount"][i]
                    overall_value += this_ret_dict["overall_value"][i]

                    unique_id += this_ret_dict["order_id"][i]

                    if airline_code in airlines_with_miles:
                        if airline_code not in list(miles_price_by_airline_or_cash.keys()):
                            miles_price_by_airline_or_cash[airline_code] = 0
                        
                        miles_price_by_airline_or_cash[airline_code] += this_ret_dict["estimated_price_in_miles"][i]
                    else:
                        if "cash" not in list(miles_price_by_airline_or_cash.keys()):
                            miles_price_by_airline_or_cash["cash"] = 0
                        
                        miles_price_by_airline_or_cash["cash"] += this_ret_dict["total_amount"][i]
                    
                ret_time = this_ret_dict["departure_time"][0]
            else:
                ret_segments_str = []
                ret_airline_codes = []
                ret_airline_names = []
                for i in range(len(this_dep_dict[DATABASE_COLUMNS[0]])):
                    flight_segments = this_dep_dict["return_segments"][i]
                    constructing_str = ""
                    for leg in flight_segments:
                        constructing_str += leg[0] + " -> "
                    constructing_str += flight_segments[-1][-1]

                    ret_segments_str.append(constructing_str)

                    airline_code = this_dep_dict["airline_code"][i]
                    ret_airline_codes.append(airline_code)
                    airline_name = this_dep_dict["airline_name"][i]
                    ret_airline_names.append(airline_name)

                    unique_id += this_dep_dict["order_id"][i]

                    # Already handled cash, don't need it again
                    
                ret_time = this_dep_dict["return_time"][0]

            useful_dict["is_synthetic"].append(is_synthetic)
            useful_dict["dep_segments_str"].append(dep_segments_str)
            useful_dict["dep_airline_codes"].append(dep_airline_codes)
            useful_dict["dep_airline_names"].append(dep_airline_names)
            useful_dict["dep_time"].append(dep_time)
            useful_dict["ret_segments_str"].append(ret_segments_str)
            useful_dict["ret_airline_codes"].append(ret_airline_codes)
            useful_dict["ret_airline_names"].append(ret_airline_names)
            useful_dict["ret_time"].append(ret_time)
            useful_dict["unique_id"].append(unique_id)
            useful_dict["cash_price"].append(cash_price)
            useful_dict["overall_value"].append(overall_value)
            useful_dict["miles_price_by_airline_or_cash"].append(miles_price_by_airline_or_cash)
    

    # Now we do vpm and similar ones
    for i in range(len(useful_dict["is_synthetic"])):
        miles_sum = 0

        for code in airlines_with_miles:
            if code in list(useful_dict["miles_price_by_airline_or_cash"][i].keys()):
                code_miles = round(useful_dict['miles_price_by_airline_or_cash'][i][code])
                miles_sum += code_miles

        if miles_sum == 0:
            useful_dict["vpm"].append(0)
        else:

            if 'cash' in list(useful_dict["miles_price_by_airline_or_cash"][i].keys()):
                cash_remainder = useful_dict['miles_price_by_airline_or_cash'][i]['cash']
                value = useful_dict["cash_price"][i] - cash_remainder
            else:
                value = useful_dict["cash_price"][i]
            
            vpm = value / miles_sum * 100
            useful_dict["vpm"].append(vpm)

    for i in range(len(useful_dict["is_synthetic"])):
        if useful_dict["ret_airline_codes"]:
            airline_code_list = useful_dict["dep_airline_codes"][i] + useful_dict["ret_airline_codes"][i]
        else:
            airline_code_list = useful_dict["dep_airline_codes"][i]
        
        perceived_sum = 0
        for code in airline_code_list:
            if code in list(PERCEIVED_VALUE_BY_AIRLINE.keys()):
                perceived_sum += PERCEIVED_VALUE_BY_AIRLINE[code]
            else:
                perceived_sum += DEFAULT_PERCEIVED_VALUE
        
        perceived_average = perceived_sum / len(airline_code_list)

        useful_dict["average_perceived_value"].append(perceived_average)
    
    return useful_dict

            


# # For testing purposes

# if __name__ == "__main__":
#     lhr_dxb_all_routings = get_dict_for_all_possible_routings('LHR', 'DXB', 2, 'first', '2025-08-14', return_date_str='2025-08-21')
#     add_flights_to_master_flight_list(lhr_dxb_all_routings)

#     useful_dict = get_useful_info_of_top_n_sorted_flights(100, "cheapest", 'LHR', 'DXB', 2, 'first', '2025-08-14', return_date_str='2025-08-21')

#     save_dict_to_csv(useful_dict, 'test_useful_dict.csv')

#     see_db = turn_master_flight_db_into_dict()
#     save_dict_to_csv(see_db, "see_db.csv")



