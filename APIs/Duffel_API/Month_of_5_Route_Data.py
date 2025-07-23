# This is the first program in the sequence "Month_of_5_Route_Data.py" -> "Gather_Possible_Routings.py" -> "Analyze_for_Synthetic_Routing.py"
# It doesn't take any CSV files as inputs





import Duffel_Calls_Library as dcl
import sqlite3
import os
from dotenv import load_dotenv
from datetime import date, timedelta


if __name__ == "__main__":
    OUTPUT_FILE = "Duffel_API/offers.csv"

    START_DATE = '2025-07-25'
    END_DATE = '2025-07-25'
    '''
    Dubai to London (DXB - LHR)
    Singapore to Tokyo (SIN - NRT)
    New York to San Francisco (JFK - SFO)
    San Francisco to Tokyo (SFO - NRT)
    Miami to Bogotá (MIA - BOG)
    '''
    ITINERARIES = [("DXB", "LHR"), ("SIN", "NRT"), ("JFK", "SFO"), ("SFO", "NRT"), ("MIA", "BOG")]

    
    # The "segments" key leads to a list containing the abbreviations of (for each leg of the flight):
        # The origin
        # The destination
    data_csv = {
        "origin": [],
        "destination": [],
        "date": [],
        "airline_name": [],
        "airline_code": [],
        "total_amount": [],
        "total_currency": [],
        "segments": []
    }

    load_dotenv()
    access_token = os.getenv("ACCESS_TOKEN")
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Duffel-Version": "v2"
    }

    start_date = date.fromisoformat(START_DATE)
    end_date = date.fromisoformat(END_DATE)

    # Set up SQLite database
    conn = sqlite3.connect('Duffel_Flights.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS flights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            origin TEXT,
            destination TEXT,
            date TEXT,
            airline_name TEXT,
            airline_code TEXT,
            total_amount REAL,
            total_currency TEXT,
            segments TEXT
        )
    ''')
    conn.commit()

    for origin, destination in ITINERARIES:
        departure_date = start_date

        while departure_date <= end_date:
            departure_str = departure_date.strftime("%Y-%m-%d")

            data = {
                "data": {
                    "slices": [{
                        "origin": origin,
                        "destination": destination,
                        "departure_date": departure_str,
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

                    data_append = [origin,
                                    destination,
                                    departure_str,
                                    airline_name,
                                    airline_code,
                                    total_amount,
                                    total_currency,
                                    str(segment_origin_destination_pairs)]
                    
                    c.execute('''
                            INSERT INTO flights (origin, destination, date, airline_name, airline_code, total_amount, total_currency, segments)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ''', data_append)
                    conn.commit()

            departure_date += timedelta(days=1)


    conn.close()




