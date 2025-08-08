import json
from collections import defaultdict

with open("redemptions.json", "r") as f:
    redemptions = json.load(f)

graph = defaultdict(list)
route_lookup = {}
for option in redemptions:
    key = (option["origin"], option["destination"])
    graph[option["origin"]].append(option["destination"])
    route_lookup[key] = option

def find_synthetic_routes(origin, destination, sort_by="vpm"):
    synthetic_options = []

    for mid in graph[origin]:
        if mid == destination:
            continue
        if destination in graph[mid]:
            leg1 = route_lookup.get((origin, mid))
            leg2 = route_lookup.get((mid, destination))
            if leg1 and leg2:
                total_miles = leg1["miles"] + leg2["miles"]
                total_fees = float(leg1["fees"].strip('$')) + float(leg2["fees"].strip('$'))
                total_cash_value = leg1["cash_value"] + leg2["cash_value"]
                vpm = round(total_cash_value / total_miles * 100, 2)

                synthetic_options.append({
                    "route": f"{origin} → {mid} → {destination}",
                    "airlines": [leg1["airline"], leg2["airline"]],
                    "total_miles": total_miles,
                    "total_fees": total_fees,
                    "total_fees_str": f"${round(total_fees, 2)}",
                    "cabin_mix": f"{leg1['cabin']} + {leg2['cabin']}",
                    "total_cash_value": round(total_cash_value, 2),
                    "vpm": vpm
                })

    if sort_by == "vpm":
        # Sort descending by value per mile
        synthetic_options.sort(key=lambda x: x['vpm'], reverse=True)
    elif sort_by == "fees":
        # Sort ascending by total fees
        synthetic_options.sort(key=lambda x: x['total_fees'])
    elif sort_by == "score":
        # Custom combined score: higher vpm better, lower fees better
        # Example: score = vpm - 0.1 * fees (weights can be adjusted)
        synthetic_options.sort(key=lambda x: x['vpm'] - 0.1 * x['total_fees'], reverse=True)

    return synthetic_options

if __name__ == "__main__":
    origin = "LAX"
    destination = "VIE"

    print("Sorted by highest VPM:")
    for route in find_synthetic_routes(origin, destination, sort_by="vpm")[:5]:
        print(route)
    print("\nSorted by lowest fees:")
    for route in find_synthetic_routes(origin, destination, sort_by="fees")[:5]:
        print(route)
    print("\nSorted by combined score (vpm - 0.1*fees):")
    for route in find_synthetic_routes(origin, destination, sort_by="score")[:5]:
        print(route)
