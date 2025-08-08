import json
from collections import defaultdict

# Load redemption data
with open("redemptions.json", "r") as f:
    redemptions = json.load(f)

# Build a graph of direct routes and a lookup for quick access
graph = defaultdict(list)
route_lookup = {}
for option in redemptions:
    key = (option["origin"], option["destination"])
    graph[option["origin"]].append(option["destination"])
    route_lookup[key] = option

def calculate_vpm(cash_value, miles):
    """Calculate value per mile, handling zero miles."""
    if miles == 0:
        return 0
    return round(cash_value / miles, 4)

def find_synthetic_routes(origin, destination):
    """Find synthetic 1-stop routes and rank them by VPM and fees."""
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
                total_cash = leg1["cash_value"] + leg2["cash_value"]

                vpm = calculate_vpm(total_cash, total_miles)

                synthetic_options.append({
                    "route": f"{origin} → {mid} → {destination}",
                    "airlines": [leg1["airline"], leg2["airline"]],
                    "total_miles": total_miles,
                    "total_fees": total_fees,
                    "total_cash": total_cash,
                    "cabin_mix": f"{leg1['cabin']} + {leg2['cabin']}",
                    "vpm": vpm
                })

    if not synthetic_options:
        return []

    best_vpm_value = max(option["vpm"] for option in synthetic_options)
    lowest_fee_value = min(option["total_fees"] for option in synthetic_options)

    for option in synthetic_options:
        option["highlight"] = []
        if option["vpm"] == best_vpm_value:
            option["highlight"].append("🏆 Best VPM")
        if option["total_fees"] == lowest_fee_value:
            option["highlight"].append("💰 Lowest Fees")

    # Sort primarily by descending VPM, then ascending fees
    synthetic_options.sort(key=lambda x: (-x["vpm"], x["total_fees"]))

    # Format fees and cash for display
    for option in synthetic_options:
        option["total_fees"] = f"${round(option['total_fees'], 2)}"
        option["total_cash"] = f"${round(option['total_cash'], 2)}"

    return synthetic_options

# Example usage
origin = "LAX"
destination = "VIE"
synthetic_routes = find_synthetic_routes(origin, destination)

print(f"Synthetic redemption options from {origin} to {destination} (ranked):\n")
for idx, route in enumerate(synthetic_routes, start=1):
    flags = " | ".join(route["highlight"]) if route["highlight"] else ""
    print(f"{idx}. {route['route']} | Miles: {route['total_miles']} | Fees: {route['total_fees']} | Cash: {route['total_cash']} | VPM: {route['vpm']} {flags}")
