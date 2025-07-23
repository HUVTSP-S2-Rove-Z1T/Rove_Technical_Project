# This code is very messy, I can clean it up later

# This is the second program in the sequence "Month_of_5_Route_Data.py" -> "Gather_Possible_Routings.py" -> "Analyze_for_Synthetic_Routing.py"
# It takes the CSV output of "Month_of_5_Route_Data.py" as an input

# This code will run through every combination of (origin, destination, date), and then check where layovers are for those flights.
# Then it will call Duffel again to find the prices of flights going directly to and away from those layovers, and it will be possible to
# find synthetic routing opportunities.

import pandas as pd
import ast
from dotenv import load_dotenv
import os
import requests
import time



# INPUT_FILE = 'Duffel_API/Month_of_5.csv'
INPUT_FILE = 'Duffel_API/Day_of_5.csv'  # Just checking one day keeps computation time reasonable; it takes a lot of Duffel calls to do synthetic routing

OUTPUT_FILE = 'Duffel_API/Possible_Routings_5.csv'

df = pd.read_csv(INPUT_FILE)


# We will turn it back into a dictionary and fix the segment lists (they get turned into strings in the CSV file)
data_dict = df.to_dict()
segment_list = data_dict['segments']
for i in range(len(segment_list)):
    segment_list[i] = ast.literal_eval(segment_list[i])  # Remember that list mutability will carry the changes to "data_dict"

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
inbetween_flights = {}


csv_length = len(data_dict['origin'])
current_index = 0
while current_index < csv_length:  # This will go until we exhaust the CSV file
    identifiers = (data_dict['origin'][current_index],
                   data_dict['destination'][current_index],
                   data_dict['date'][current_index])
    # We add this to the two dictionaries
    original_flights[identifiers] = []
    inbetween_flights[identifiers] = []

    while True:  # This will go until it reaches a flight with a different origin, destination, or date
        other_data_dict = {'airline_name' : data_dict['airline_name'][current_index],
                           'airline_code' : data_dict['airline_code'][current_index],
                           'total_amount' : data_dict['total_amount'][current_index],
                           'total_currency' : data_dict['total_currency'][current_index],
                           'segments' : data_dict['segments'][current_index]}
        original_flights[identifiers].append(other_data_dict)

        flight_segments = data_dict['segments'][current_index]
        if len(flight_segments) > 1:  # We don't need to check direct flights, we've already done that
            for i in range(len(flight_segments)):
                considered_leg = flight_segments[i]

                if considered_leg not in inbetween_flights[identifiers]:
                    inbetween_flights[identifiers].append(considered_leg)

        current_index += 1
        if current_index >= csv_length or (data_dict['origin'][current_index],
                                           data_dict['destination'][current_index],
                                           data_dict['date'][current_index]) != identifiers:
            break

# for key in inbetween_flights.keys():
#     print(key)
#     for leg in inbetween_flights[key]:
#         print(leg)

load_dotenv()
access_token = os.getenv("ACCESS_TOKEN")
headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json",
    "Duffel-Version": "v2"
}

# Now we store all the possible synthetic flights the same way that the full flights were stored, except that along with their origin and
# destination, the "root" origin and destinations of the flights they are trying to replace also go in the CSV
data_csv = {
    "root_origin": [],
    "root_destination": [],
    "date": [],
    "origin": [],
    "destination": [],
    "airline_name": [],
    "airline_code": [],
    "total_amount": [],
    "total_currency": [],
    "segments": []
}
for key in inbetween_flights.keys():
    root_origin = key[0]
    root_destination = key[1]
    date = key[2]

    for leg in inbetween_flights[key]:
        origin = leg[0]
        destination = leg[1]

        data = {
            "data": {
                "slices": [{
                    "origin": origin,
                    "destination": destination,
                    "departure_date": date,
                }],
                "passengers": [{"type": "adult"}],
                "cabin_class": "economy"
            }
        }

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
                print(f"No offers found for {origin} to {destination} on {date}.")
            else:
                print(f"{len(offers)} offers found for {origin} to {destination} on {date}:")
                for offer in offers:
                    carrier = offer["owner"]
                    airline_name = carrier["name"]
                    airline_code = carrier["iata_code"]
                    total_amount = offer["total_amount"]
                    total_currency = offer["total_currency"]

                    # For all the segments (we put a "[0]" after "[slices]" because it is a one way ticket):
                    segments = offer["slices"][0]["segments"]
                    segment_origin_destination_pairs = []
                    for leg in segments:
                        leg_pair = [leg["origin"]["iata_code"], leg["destination"]["iata_code"]]
                        segment_origin_destination_pairs.append(leg_pair)

                    data_append = [root_origin,
                                   root_destination,
                                   date,
                                   origin,
                                   destination,
                                   airline_name,
                                   airline_code,
                                   total_amount,
                                   total_currency,
                                   segment_origin_destination_pairs]
                    

                    for i, key in enumerate(data_csv.keys()):
                        data_csv[key].append(data_append[i])
        else:
            print(f"Error for {origin} to {destination} on {date}: {response.status_code}")
            print(response.text)
    
df_final = pd.DataFrame(data_csv)
df_final.to_csv(OUTPUT_FILE, index=False)







