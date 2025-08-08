import pandas as pd

'''
This basically just gets the minimum price for synthetic and direct routes from the offers.csv file
Loads the data, also if it is static, we don't need to use a db in the app, csv is fine
and the dirs_dates and lays_dates dicts are just the minimums of the synthetic and direct routes
'''

def gen_syn_routes():
    df = pd.read_csv("CSV_NAME.csv")  # Replace with the real name

    dirs_dates = {}
    lays_dates = {}

    for _, row in df.iterrows():
        segments = eval(row['segments'])
        key = (row['origin'], row['destination'], row['date'])
        price = float(row['total_amount'])

        if len(segments) > 1:
            if key not in lays_dates or price < lays_dates[key]:
                lays_dates[key] = price
        else:
            if key not in dirs_dates or price < dirs_dates[key]:
                dirs_dates[key] = price
    return dirs_dates, lays_dates

gen_syn_routes()