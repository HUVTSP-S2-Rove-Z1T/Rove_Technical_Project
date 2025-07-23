import requests
import os
import time

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
def unpack_flight_array(flight_array, id_keys=('origin', 'destination', 'date')):
    new_flight_dict = {}

    flight_array_keys = list(flight_array.keys())
    non_id_keys = []
    for array_key in flight_array_keys:
        if array_key not in id_keys:
            non_id_keys.append(array_key)

    array_length = len(flight_array[flight_array_keys[0]])
    if array_length < 1:
        print('Error, no flights to unpack')
        return None
    
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








