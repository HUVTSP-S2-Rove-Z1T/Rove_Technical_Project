import pandas as pd
import ast

# Load data
df = pd.read_csv("offers.csv")

# Parse 'segments' strings into actual Python lists
df['segments'] = df['segments'].apply(ast.literal_eval)

# Calculate number of stops (segments minus 1)
df['num_stops'] = df['segments'].apply(lambda x: len(x) - 1)

# Ensure price is float
df['total_amount'] = df['total_amount'].astype(float)

# Group by origin, destination, date
grouped = df.groupby(['origin', 'destination', 'date'])

# Store results for multi-stop cheaper offers
cheaper_multi_offers = []

for (orig, dest, date), group in grouped:
    # Separate direct and multi-stop offers
    direct_offers = group[group['num_stops'] == 0]
    multi_offers = group[group['num_stops'] > 0]

    if direct_offers.empty or multi_offers.empty:
        continue

    # Cheapest direct price
    min_direct_price = direct_offers['total_amount'].min()

    # Multi-stop offers cheaper than cheapest direct
    cheaper_multi = multi_offers[multi_offers['total_amount'] < min_direct_price]

    for _, row in cheaper_multi.iterrows():
        cheaper_multi_offers.append({
            'origin': orig,
            'destination': dest,
            'date': date,
            'multi_stop_price': row['total_amount'],
            'direct_price': min_direct_price,
            'num_stops': row['num_stops'],
            'segments': row['segments']
        })

# Make DataFrame of cheaper multi-stop offers
cheaper_multi_df = pd.DataFrame(cheaper_multi_offers)

print(f"Found {len(cheaper_multi_df)} examples where adding a stop is cheaper than direct:\n")

print(cheaper_multi_df.head(10))  # Show up to 10 examples

# Find airports where adding a stop often yields cheaper prices

# Count by origin airport
origin_counts = cheaper_multi_df['origin'].value_counts().head(10)
print("\nTop 10 origin airports where adding a stop is often cheaper:")
print(origin_counts)

# Count by destination airport
destination_counts = cheaper_multi_df['destination'].value_counts().head(10)
print("\nTop 10 destination airports where adding a stop is often cheaper:")
print(destination_counts)

# Save to CSV for further inspection
cheaper_multi_df.to_csv("cheaper_multi_stop_offers.csv", index=False)
