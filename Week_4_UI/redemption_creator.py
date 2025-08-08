import json
import random
import datetime

# Sample realistic data pools
airports = [
    "LAX", "JFK", "SFO", "ORD", "ATL", "DFW", "SEA", "MIA",
    "LHR", "CDG", "FRA", "AMS", "MAD", "VIE", "ZRH", "DOH", "DXB", "NRT", "HND", "SIN", "SYD", "MEL"
]
airlines = [
    "American Airlines", "Delta Air Lines", "United Airlines",
    "British Airways", "Lufthansa", "Air France", "Emirates",
    "Qatar Airways", "Singapore Airlines", "ANA", "Qantas"
]
cabins = ["Economy", "Premium Economy", "Business", "First"]

def generate_random_flight():
    origin, destination = random.sample(airports, 2)
    airline = random.choice(airlines)
    cabin = random.choice(cabins)

    # Miles based on cabin type and distance estimate
    distance = random.randint(500, 9000)  # miles
    base_miles = distance + random.randint(-200, 200)  # add noise
    cabin_multiplier = {"Economy": 1, "Premium Economy": 1.2, "Business": 2, "First": 3}
    miles_required = int(base_miles * cabin_multiplier[cabin])

    # Fees based on cabin and airline
    base_fee = random.uniform(20, 500)  # USD
    fees = round(base_fee * (1.0 if cabin == "Economy" else 1.3), 2)

    # Simulated cash price based on distance, cabin, and airline prestige
    prestige_multiplier = 1.0 + (airlines.index(airline) % 5) * 0.1
    cash_price = round(distance * 0.15 * cabin_multiplier[cabin] * prestige_multiplier, 2)

    # Random travel date in the next 365 days
    days_ahead = random.randint(1, 365)
    date = (datetime.date.today() + datetime.timedelta(days=days_ahead)).isoformat()

    return {
        "origin": origin,
        "destination": destination,
        "airline": airline,
        "cabin": cabin,
        "miles": miles_required,
        "fees": f"${fees}",
        "cash_price": cash_price,
        "date": date
    }

# Generate dataset
redemptions = [generate_random_flight() for _ in range(250)]  # 250+ flights

# Save to JSON
with open("redemptions.json", "w") as f:
    json.dump(redemptions, f, indent=4)

print("Generated redemptions.json with", len(redemptions), "flights.")
