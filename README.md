# MaxMiles, By Rove

## Overview

### Product Description

The MaxMiles program is meant to be deployed as a Streamlit website, which is available to anyone with the link. In the site, users can search for flights and see the itineraries with the cheapest prices, including both individual bookings and synthetic routings. Beyond this basic functionality, by entering the airlines where they have rewards, users will be able to see estimated prices in miles for each flight and the value per mile (VPM) they would receive from paying with miles. Filters also allow users to only see flights they can pay for with miles, sort by VPM, or sort by overall value (a combination of low price and high quality of the airline).

This core use case is supported by a login system, where a user's data is stored according to their unique username and only accessible given their password, and a user profile, where users can see their past flight searches.

### Data Sources

All flight data except VPM and perceived airline value is gathered from a free "Pay as you go" Duffel API account.

**Duffel API**: For this application, the only Duffel endpoint used is "Offer Requests." Calling this endpoint returns a wealth of information for all the flights that have openings for a particular number of passengers given: the origin airport, the destination airport, the departure day, the return day (if not one way), and the cabin class. The most crucial information returned for MaxMiles is the price in USD of the booking, the "segments" of the flight (all the connecting flights along the way, which allows the program to find synthetic routing alternatives), and the departure and arrival times of each segment. This one endpoint drives the whole program.

**Value Per Mile**: Despite Duffel's utility, it cannot provide a flight's price in award miles. The only API our team found which can do so is seats.aero (see https://developers.seats.aero/reference/getting-started-p), which requires a paid account to access that endpoint. Additionally, so many airlines use dynamic pricing these days that trying to process award charts and apply those to flights would have been highly inaccurate. Instead, our team used the average VPM for miles across a list of major airlines, with data collected from NerdWallet (source: https://www.nerdwallet.com/article/travel/airline-miles-and-hotel-points-valuations).

**Perceived Airline Value**: Due to the subjectivity of "perceived airline value," our team created a list of values for major airlines based on our own experience and research.

With Rove's resources, each of these data sources can be improved tremendously. See the "Limitations" section for more details.

### Limitations

As the product of only a five week timeline and without access to Enterprise resources, there are plenty of areas in which Rove can improve on MaxMiles.

**API Call Time and Breadth**: Duffel provides a lot of information, but the free version of their services is rate limited, so the MaxMiles website is constrained by the time it takes to for Duffel to return flight information. Additionally, Duffel only has access to 142 airlines, and includes notable gaps like Delta Airlines. Rove will likely want to invest in a Duffel Enterprise account, or leave Duffel entirely in favor of a more business-oriented API with connections to more airlines.

**VPM and Perceived Value Data**: Either through Rove's existing partnerships with airlines or through paid API accounts with services like the aforementioned seats.aero, Rove will be able to find specific miles prices for each flight and calculate the real VPM instead of an estimation across all the services of an airline. This will greatly increase the accuracy and therefore the utility of MaxMiles. Additionally, basing the perceived value calculations on real world data (for example, annual ratings of airline quality) will increase the credibility of the site.

**Security**: There is currently very little security behind the user authentication process. Rove should integrate professional cybersecurity measures to ensure that the site is not vulnerable to bad actors.

**Database Updating**: Currently, once a type of flight is called (determined by origin, destination, departure date, return date, number of passengers, and cabin class), it will stay in the database indefinitely. This means that when other users call the same flight, they will immediately see results instead of waiting for Duffel to find the information again. However, this means that they may see some expired offers or not see new openings. Once Rove replaces the free version of Duffel, they will likely want to delete entries in the database after a certain amount of time (e.g., one hour) to call new data regularly and stay up to date. Depending on the speed of the new API, Rove may also want to continuously call it for common flights so that users of the website receive instant results from a comprehensive database rather than waiting for the API each time.

### Instructions for Updating Datasets

The MaxMiles program automatically updates its dataset as users search for flights. For more details, see "Database Updating" under "Limitations."

## Technical Description

