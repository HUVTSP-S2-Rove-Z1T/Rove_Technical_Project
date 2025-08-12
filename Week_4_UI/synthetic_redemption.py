# synthetic_redemptions.py
import json
from collections import defaultdict

def load_redemptions(json_path="redemptions.json"):
    with open(json_path, "r") as f:
        return json.load(f)

def calculate_vpm(cash_value, miles):
    if miles == 0:
        return 0
    return round(cash_value / miles, 4)

def find_synthetic_routes(origin, destination, redemptions):
    graph = defaultdict(list)
    route_lookup = {}
    for option in redemptions:
        key = (option["origin"], option["destination"])
        graph[option["origin"]].append(option["destination"])
        route_lookup[key] = option

    synthetic_options = []
    for mid in graph.get(origin, []):
        if mid == destination:
            continue
        if destination in graph.get(mid, []):
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
                    "total_fees": f"${round(total_fees,2)}",
                    "total_cash": f"${round(total_cash,2)}",
                    "cabin_mix": f"{leg1['cabin']} + {leg2['cabin']}",
                    "vpm": vpm
                })

    # Highlight best options
    if synthetic_options:
        best_vpm = max(o["vpm"] for o in synthetic_options)
        lowest_fee = min(float(o["total_fees"].strip('$')) for o in synthetic_options)
        for o in synthetic_options:
            o["highlight"] = []
            if o["vpm"] == best_vpm:
                o["highlight"].append("🏆 Best VPM")
            if float(o["total_fees"].strip('$')) == lowest_fee:
                o["highlight"].append("💰 Lowest Fees")

        synthetic_options.sort(key=lambda x: (-x["vpm"], float(x["total_fees"].strip('$'))))
    return synthetic_options
