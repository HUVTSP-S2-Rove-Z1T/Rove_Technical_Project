'''
This queries the VPM CSV and returns a list of the results. You can treat it as a module and call it from another file.
'''

import pandas as pd

df = pd.read_csv("name.csv")

airs = set(df["Airlines"])

deps = set(df["Departures"])

def get_results(arr, dep, air):
    if air not in airs:
        raise ValueError("Invalid Airline")
    if dep not in deps:
        raise ValueError("Invalid Departure")
    arrs = set(df[df["Departures"] == dep]["Arrivals"])
    if arr not in arrs:
        raise ValueError("Invalid Arrival")
    filt = df[(df["Arrivals"] == arr) & (df["Departures"] == dep) & (df["Airlines"] == air)]
    if filt.empty:
        raise ValueError("Invalid Combination")
    return filt.values.to_list()[0]
