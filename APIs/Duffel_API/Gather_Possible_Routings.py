# This is the second program in the sequence "Month_of_5_Route_Data.py" -> "Gather_Possible_Routings.py" -> "Analyze_for_Synthetic_Routing.py"
# It takes the CSV output of "Month_of_5_Route_Data.py" as an input

# This code will run through every combination of (origin, destination, date), and then check where layovers are for those flights.
# Then it will call Duffel again to find the prices of flights going directly to and away from those layovers, and it will be possible to
# find synthetic routing opportunities.

import Duffel_Calls_Library as dcl
import sqlite3
import json
import os
from dotenv import load_dotenv



if __name__ == '__main__':
    # Set up possible_routings table in DB
    conn = sqlite3.connect('Duffel_Flights.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS possible_routings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            root_origin TEXT,
            root_destination TEXT,
            date TEXT,
            origin TEXT,
            destination TEXT,
            airline_name TEXT,
            airline_code TEXT,
            total_amount REAL,
            total_currency TEXT,
            segments TEXT
        )
    ''')
    conn.commit()

    c = conn.cursor()
    c.execute('SELECT origin, destination, date, airline_name, airline_code, total_amount, total_currency, segments FROM flights')
    rows = c.fetchall()

    # Convert to dictionary format similar to previous CSV logic
    columns = ["origin", "destination", "date", "airline_name", "airline_code", "total_amount", "total_currency", "segments"]
    data_dict = {col: [] for col in columns}
    for row in rows:
        for i, col in enumerate(columns):
            data_dict[col].append(row[i])


    segment_list = data_dict['segments']
    for i in range(len(segment_list)):
        # I had to add the line below to make json.loads() work, it didn't like single quotes. Did it work for you Madhava?
        segment_with_double_quotes = segment_list[i].replace("\'", "\"")
        segment_list[i] = json.loads(segment_with_double_quotes)  # Remember that list mutability will carry the changes to "data_dict"

    # Each (origin, destination, date) key of "original_flights" will lead to another dictionary of the form below
        # {'airline_name': [<Flight 0 airline_name>, <Flight 1 airline_name>, ...],
        #  'airline_code': [<Flight 0 airline_code>, <Flight 1 airline_code>, ...],
        #  'total_amount': [<Flight 0 total_amount>, <Flight 1 total_amount>, ...],
        #  'total_currency' : [<Flight 0 total_currency>, <Flight 1 total_currency>, ...],
        #  'segments' : [<Flight 0 segments>, <Flight 1 segments>, ...],
        # }
    original_flights = dcl.unpack_flight_array(data_dict, id_keys=('origin', 'destination', 'date'))

    # "inbetween_flights" contains all the possible intermediate flights found when looking at the layovers of flights for a given (origin, destination, date) combo
    inbetween_flights = {}
    for identifiers in original_flights.keys():
        inbetween_flights[identifiers] = []
        for flight_segments in original_flights[identifiers]['segments']:
            if len(flight_segments) > 1:  # We don't need to check direct flights, we've already done that
                for i in range(len(flight_segments)):
                    considered_leg = flight_segments[i]

                    if considered_leg not in inbetween_flights[identifiers]:
                        inbetween_flights[identifiers].append(considered_leg)

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

            offers = dcl.call_flight_offers(headers=headers, data=data)

            if offers:
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
                                    str(segment_origin_destination_pairs)]
                    

                    c.execute('''
                        INSERT INTO possible_routings (root_origin, root_destination, date, origin, destination, airline_name, airline_code, total_amount, total_currency, segments)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', data_append)
                    conn.commit()
        
    conn.close()








