# This code is very messy, I can clean it up later

# This is the first program in the sequence "Month_of_5_Route_Data.py" -> "Gather_Possible_Routings.py" -> "Analyze_for_Synthetic_Routing.py"
# It doesn't take any CSV files as inputs


import requests
import os
from dotenv import load_dotenv
from datetime import date, timedelta
import pandas as pd
import time


DAYS_OF_DATA = 30

if __name__ == "__main__":
    # The information we want to save for each flight is:
        # The origin
        # The destination
        # The date
        # The carrier name
        # The carrier code
        # The price
        # The currency
        # For each segment (if there are layovers), a list containing the abbreviations of:
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

    '''
    Dubai to London (DXB - LHR)
    Singapore to Tokyo (SIN - NRT)
    New York to San Francisco (JFK - SFO)
    San Francisco to Tokyo (SFO - NRT)
    Miami to Bogotá (MIA - BOG)
    '''

    airlines = [("DXB", "LHR"), ("SIN", "NRT"), ("JFK", "SFO"), ("SFO", "NRT"), ("MIA", "BOG")]
    start_date = date.today() + timedelta(days=1)
    end_date = date.today() + timedelta(days=DAYS_OF_DATA)

    for origin, destination in airlines:
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
                    for offer in offers:
                        carrier = offer["owner"]
                        # carrier = offer["slices"][0]["segments"][0]["operating_carrier"]
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
                                       segment_origin_destination_pairs]
                        
                        for i, key in enumerate(data_csv.keys()):
                            data_csv[key].append(data_append[i])
            else:
                print(f"Error for {origin} to {destination} on {departure_str}: {response.status_code}")
                print(response.text)

            departure_date += timedelta(days=1)


    df = pd.DataFrame(data_csv)
    df.to_csv("Duffel_API/offers.csv", index=False)




