import requests
import os
from dotenv import load_dotenv
from datetime import date, timedelta
import pandas as pd

# If anyone can find a way to query a range of dates at once that would be great
# We can prolly add some matplotlib plots and other data visualization stuff. also we r just fetching price data-can prolly expand functionality later

if __name__ == "__main__":
    data_csv = {
        "origin": [],
        "destination": [],
        "airline_name": [],
        "airline_code": [],
        "total_amount": []
    }

    load_dotenv()
    access_token = os.getenv("ACCESS_TOKEN")
    print(access_token)

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
    end_date = date.today() + timedelta(weeks=4)

    departure_date = start_date
    while departure_date <= end_date:
        departure_str = departure_date.strftime("%Y-%m-%d") 
        for origin, destination in airlines:
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
                os.getenv("URL"),
                headers=headers,
                json=data
            )

            if response.status_code == 201:
                offers = response.json()["data"]["offers"]
                if not offers:
                    print(f"No offers found for {origin} to {destination} on {departure_str}.")
                else:
                    print(f"{len(offers)} offers found for {origin} to {destination} on {departure_str}:")
                    for offer in offers:
                        carrier = offer["slices"][0]["segments"][0]["operating_carrier"]
                        airline_name = carrier["name"]
                        airline_code = carrier["iata_code"]
                        total_amount = offer["total_amount"]
                        currency = offer["total_currency"]
                        data_append = [origin, destination, airline_name, airline_code, total_amount]
                        for i, key in enumerate(data_csv.keys()):
                            data_csv[key].append(data_append[i])
            else:
                print(f"Error for {origin} to {destination} on {departure_str}: {response.status_code}")
                print(response.text)

        departure_date += timedelta(days=1)

    df = pd.DataFrame(data_csv)
    df.to_csv("offers.csv", index=False)


