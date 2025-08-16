# MaxMiles, By Rove

## Overview

### Product Description

For a product demo, visit https://week4uipy-gv6gjhn8kvbm9eg6jbfywi.streamlit.app/.

The MaxMiles program is meant to be deployed as a Streamlit website, which is available to anyone with the link. In the site, users can search for flights and see the itineraries with the cheapest prices, including both individual bookings and synthetic routings. Beyond this basic functionality, by entering the airlines where they have rewards, users will be able to see estimated prices in miles for each flight and the value per mile (VPM) they would receive from paying with miles. Filters also allow users to only see flights they can pay for with miles, sort by VPM, or sort by overall value (a combination of low price and high quality of the airline).

This core use case is supported by a login system, where a user's data is stored according to their unique username and only accessible given their password, and a user profile, where users can see their past flight searches.

### Data Sources

All flight data except VPM and perceived airline value is gathered from a free "Pay as you go" Duffel API account.

**Duffel API**: For this application, the only Duffel endpoint used is "Offer Requests”. Calling this endpoint returns a wealth of information for all the flights that have openings given: the origin airport, the destination airport, the departure day, the return day (if not one way), the number of passengers, and the cabin class. The most crucial information returned for MaxMiles is the price in USD of the booking, the "segments" of the flight (all the connecting flights along the way, which allows the program to find synthetic routing alternatives), and the departure and arrival times of each segment. This one endpoint drives the whole program.

**Value Per Mile**: Despite Duffel's utility, it cannot provide a flight's price in award miles. The only API our team found which can do so is seats.aero (see https://developers.seats.aero/reference/getting-started-p), which requires a paid account to access that endpoint. Additionally, so many airlines use dynamic pricing these days that trying to process award charts and apply those to flights would have been highly inaccurate. Instead, our team used the average VPM for miles across a list of major airlines, with data collected from NerdWallet (source: https://www.nerdwallet.com/article/travel/airline-miles-and-hotel-points-valuations).

**Perceived Airline Value**: Due to the subjectivity of "perceived airline value", our team created a list of values for major airlines based on our own experience and research.

With Rove's resources, each of these data sources can be improved tremendously. See the "Limitations" section for more details.

### Limitations

As the product of only a five week timeline and without access to Enterprise resources, there are plenty of areas in which Rove can improve on MaxMiles.

**API Call Time and Breadth**: Duffel provides a lot of information, but the free version of their services is rate limited, so the MaxMiles website is constrained by the time it takes to for Duffel to return flight information. Additionally, Duffel only has access to 142 airlines, and includes notable gaps like Delta Airlines. Rove will likely want to invest in a Duffel Enterprise account, or leave Duffel entirely in favor of a more business-oriented API with connections to more airlines.

**VPM and Perceived Value Data**: Either through Rove's existing partnerships with airlines or through paid API accounts with services like the aforementioned seats.aero, Rove will be able to find specific miles prices for each flight and calculate the real VPM instead of an estimation across all the services of an airline. This will greatly increase the accuracy and therefore the utility of MaxMiles. Additionally, basing the perceived value calculations on real world data (for example, annual ratings of airline quality) will increase the credibility of the site.

**Security**: There is currently very little security behind the user authentication process. Rove should integrate professional cybersecurity measures to ensure that the site is not vulnerable to bad actors.

**Database Updating**: Currently, once a type of flight is called (determined by origin, destination, departure date, return date, number of passengers, and cabin class), it will stay in the database indefinitely. This means that when other users call the same flight, they will immediately see results instead of waiting for Duffel to find the information again. However, this means that they may see some expired offers or not see new openings. Once Rove replaces the free version of Duffel, they will likely want to delete entries in the database after a certain amount of time (e.g., one hour) to call new data regularly and stay up to date. Depending on the speed of the new API, Rove may also want to continuously call it for common flights so that users of the website receive instant results from a comprehensive database rather than waiting for the API each time.

**Layover Timing**: The program is not yet sensitive to the fact that if a connecting flight leaves before the prior one arrives, then that combination cannot be a valid synthetic routing itinerary. However, the departure times of every flight are already saved in the database, so Rove can customize how timing affects synthetic routing options as much as they like.

**Streamlit and API Accounts**: The program runs on the personal Duffel and Streamlit accounts of our team. To attach the program to its own accounts, Rove should: 1. Replace the access token in the file “Streamlit_Deployment/Synthetic_and_VPM_Logic.py” with their own Duffel access token, and 2. Create their own Streamlit account and create an app linked to the Github file “Streamlit_Deployment/Final_UI.py". At the time of writing, the current access token is on line 8 of “Streamlit_Deployment/Synthetic_and_VPM_Logic.py", set as the constant “DUFFEL_ACCESS_TOKEN". After completing these steps, MaxMiles will no longer be dependent on any accounts of the members of the team.

### Instructions for Updating Datasets

The MaxMiles program automatically updates its dataset as users search for flights. For more details, see "Database Updating" under "Limitations”. The heading “Streamlit and API Accounts” under "Limitations" describes how Rove can deploy the program without relying on the personal accounts of our team.

## Technical Description

### Github Organization

The most important directory in the Github is “Streamlit_Deployment". All the other directories contain older, intermediate files that were eventually worked into the files contained in “Streamlit_Deployment".

In “Streamlit_Deployment", there are three files: “Final_UI.py", “Synthetic_and_VPM_Logic.py", and “requirements.txt".

**Final_UI.py**: This contains all the frontend Streamlit code used to generate the website. It contains the code that creates the UI, and stores data about users’ search histories and passwords. It connects to the backend, “Synthetic_and_VPM_Logic.py", in order to get the information it needs to display when users search for flights. If Rove chooses to deploy their own Streamlit app, they should connect it to this file in the repository.

**Synthetic_and_VPM_Logic.py**: This is the backend code, which calls the Duffel API and processes the data it receives into a useful format. It also searches for synthetic routings across those flights and handles sorting the search results by various filters.

**requirements.txt**: This tells Streamlit how to import the libraries used in the other two files of the directory.

More detail about the first two files can be found below.

### Final_UI.py

The MaxMiles website is divided into several pages, and the page the user is on is determined by the variable “st.session_state.mode”.

The program uses an SQL database (file name: “user_auth.db”) to record usernames and passwords (under the table “users”), and search history organized by user (under the table f“search_history_{username}”, where {username} is replaced with the username of a particular user).

The bulk of the functionality is in the Find Flights page of the site, where the program accesses flights from the database constructed in “Streamlit_Deployment/Synthetic_and_VPM_Logic.py” or calls new flights with Duffel if necessary (described in further detail under the “Synthetic_and_VPM_Logic.py” heading below). Then it sorts the list of offerings it finds to apply different tags, like “Premium Value” or “Best VPM”, before filtering and presenting its data for the user.

The rest of the code is fairly self-explanatory (mostly just design and straightforward data management), and in-line comments in the appropriate sections should clarify how it works.

### Synthetic_and_VPM_Logic.py

The two most important parts of the backend are the data storage format and the main functions used to create the clean flight info shown in the frontend.

#### Data Storage

There are two common forms used for storing flight data. The first, a “packed flight array”, is a dictionary with various keys that represent important flight data. These include the origin airport, destination, departure date, and many others. In each of those keys is a list of different values, and the *i*th entry in each of those lists together represent the data of the *i*th flight.

An “unpacked flight array” is very similar; it is a dictionary with a set of keys that are tuples of the keys of the packed flight arrays. For example, an unpacked flight array with the unpacking “(origin, destination, departure date)” might have keys like “(LHR, DXB, 2025-09-27)” and “(JFK, LAX, 2025-09-13)”. Then the value corresponding to each of those keys is a normal packed flight array, just missing the keys “origin”, “destination”, and “departure date”. Essentially, the unpacked flight array groups flights by useful characteristics like departure date. Each function in the file should specify whether it takes packed or unpacked flights as inputs.

#### Data Manipulation Functions

To get from a list of desired flight data (origin, destination, departure date, return date if applicable, number of passengers, cabin class) to the final list of offerings (which includes all the different bookings for synthetic routings, the cash price of the whole offering, the award miles information, and more), the following functions are used. Some are skipped for brevity, and are self-explanatory.

**call_flight_offers**: This makes the actual Duffel API call, given the headers and data that are fed into the API endpoint. It directly outputs the JSON file that Duffel spits out.

**get_dict_for_route**: This takes in the (origin, destination, departure date, return date if applicable, number of passengers, cabin class) info and outputs the packed flight array of all the flights that Duffel found with those characteristics (by calling “call_flight_offers”). It just extracts the useful data from the JSON file that “call_flight_offers” returns.

**get_dict_for_all_possible_routings**: This takes in the (origin, destination, departure date, return date if applicable, number of passengers, cabin class) info and returns *all* the possible flights that cover common segments of the flights from the origin to the destination. Essentially, instead of just finding whole bookings like "get_dict_for_route", it finds the booking for every possible flight that can be used in a synthetic routing that reaches the same destination. It finds this by calling “get_dict_for_route” with the input (origin, destination, departure date, return date if applicable, number of passengers, cabin class), gathering every segment of every flight in the database, then calling “get_dict_for_route” for each of them with the input (segment start, segment end, departure date, return date if applicable, number of passengers, cabin class). In the end, it returns a packed flight array of any flight that either gets from the origin to the destination or could possibly be a step in that process. Note: if any of the flights to be called in this function are already in the master flight database, it pulls them from there instead with “find_flights_in_master_list”.

**find_possible_routings_from_master_list**: This finds every possible synthetic routing from the origin to the destination, using flights from the master database (unless you are sure that every possible flight that could be used in a synthetic routing is already in the master database, this function should be called after putting the output of “get_dict_for_all_possible_routings” into the database with “add_flights_to_master_flight_list”). The output “dep_all_leg_orders” (and its parallel “ret_all_leg_orders” for the return) will contain every possible set of legs to get from the origin to the destination (for example, if the origin is LHR and the destination is DXB, it might include LHR -> DXB, LHR -> JED -> DXB, and LHR -> RUH -> DXB. They are encoded as lists of pairs of airports, like “[[“LHR”, “RUH”], [“RUH”, “DXB”]]”). It will also return an unpacked flight array “inbetween_dep” (or “inbetween_ret”), where plugging the key “(<airport 1>, <airport 2>)” for any of the possible segments (e.g., “(“LHR”, “RUH”)”) will return a flight array of all the flights going from the first to the second airport. Essentially, it gives all the possible ways to get from the origin to the destination and all the possible bookings corresponding to each of the segments along the way.

**get_dicts_of_top_n_sorted_all_types_flights**: This finally sorts all the possible bookings by a given metric, identified by the argument “sort_key”. For example, “sort_key=‘total_amount’” would be the most common one. It is actually just a slightly more comprehensive version of “get_dicts_of_top_n_sorted_synthetic_flights”, because “get_dicts_of_top_n_sorted_synthetic_flights” will return *strictly* synthetic routing flights and not whole bookings for two-way trips. That function works as follows: for each possible synthetic routing itinerary from “find_possible_routings_from_master_list”, it tries combinations of flights that cover segments of the itinerary until it finds the cheapest one. It repeats this process until it has found the desired number of bookings (or runs out of combinations, but this will be extremely rare, because the number of combinations scales very quickly). It uses the functions “get_top_n_flight_combos“ and “get_top_n_dep_ret_combos“ to sort the flights, and an examination of their code will reveal the sorting procedure. The current method is relatively fast, but is not guaranteed to always produce the “n” cheapest (or otherwise best) options. Rove may want to swap those functions for slower ones that invariably find the best options, but for almost all cases the current functions work well.

**get_useful_info_of_top_n_sorted_flights**: This is the most important function in the file, and it is what “Final_UI.py” calls when searching for flights. It calls “get_dicts_of_top_n_sorted_all_types_flights”, which outputs all the top combinations of flights which can work, and it reformulates the data into something easy to display in the UI.

### Other Important Notes

It is important to emphasize that “get_useful_info_of_top_n_sorted_flights”, the most important function of “Streamlit_Deployment/Synthetic_and_VPM_Logic.py”, will only search the “Synthetic_and_VPM_Logic.py” database, *not* actually call Duffel. If “get_useful_info_of_top_n_sorted_flights” is used without the applicable flights already being in the database, then it will not return any flights. When the database does not contain the right flights already, “get_dict_for_all_possible_routings” should always be run and added to the database with “add_flights_to_master_flight_list” first.
