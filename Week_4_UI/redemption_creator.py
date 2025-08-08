import json
import random
import datetime

# Seed for reproducibility
random.seed(42)

airports = ['LAX', 'JFK', 'ORD', 'ATL', 'DFW', 'SFO', 'MIA', 'SEA', 'BOS', 'DEN', 'VIE', 'CDG', 'HND', 'DXB']
airlines = ['United', 'Delta', 'Emirates', 'Lufthansa', 'American', 'Air France']
cabins = ['Economy', 'Premium Economy', 'Business', 'First Class']

def random_date(start, end):
    """Generate random date between start and end"""
    delta = end - start
    rand_days = random.randint(0, delta.days)
    return (start + datetime.timedelta(days=rand_days)).strftime('%Y-%m-%d')

redemptions = []
num_flights = 220

for i in range(num_flights):
    origin = random.choice(airports)
    destination = random.choice([a for a in airports if a != origin])

    miles = random.randint(1500, 8000)
    base_fee = random.uniform(5, 75)
    cabin = random.choices(cabins, weights=[60, 20, 15, 5])[0]
    cabin_multiplier = {'Economy':1, 'Premium Economy':1.4, 'Business':2.5, 'First Class':3.5}[cabin]

    miles = int(miles * cabin_multiplier)
    fees = round(base_fee * cabin_multiplier, 2)
    cents_per_mile = random.uniform(0.8, 3.5)
    cash_value = round(miles * cents_per_mile / 100 + fees, 2)
    vpm = round(cash_value / miles * 100, 2)

    redemption = {
        "id": f"FL{i+1:04d}",
        "origin": origin,
        "destination": destination,
        "airline": random.choice(airlines),
        "miles": miles,
        "fees": f"${fees:.2f}",
        "cabin": cabin,
        "departure_date": random_date(datetime.date.today(), datetime.date.today() + datetime.timedelta(days=180)),
        "cash_value": cash_value,
        "vpm": vpm
    }
    redemptions.append(redemption)

with open("redemptions.json", "w") as f:
    json.dump(redemptions, f, indent=2)

print(f"Generated {len(redemptions)} synthetic redemption options in redemptions.json")

