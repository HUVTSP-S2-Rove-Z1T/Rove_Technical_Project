import streamlit as st
from datetime import date
import Synthetic_and_VPM_Logic as synth
import sqlite3 as sql
import bcrypt as bc

# Constants and session state setup (reuse your constants)
AIRLINES_WITH_VPM_DATA_CODES = list(synth.AIRLINE_CODE_TO_NAME.keys())
AIRLINES_WITH_VPM_DATA_NAMES = []
for code in AIRLINES_WITH_VPM_DATA_CODES:
    AIRLINES_WITH_VPM_DATA_NAMES.append(synth.airline_code_to_name(code))

SEARCH_FILTERS = ['Maximize Overall Value', 'Only Show Flights Payable With Miles', 'Sort by VPM']
SEARCHES_SHOWN = 10
FLIGHTS_SHOWN = 25

CABIN_CLASS_FANCY_TO_BASIC = {
    'Economy' : 'economy',
    'Premium Economy' : 'premium_economy',
    'Business' : 'business',
    'First Class' : 'first'
}

# Graphics for later
def css_style_by_index(index):
    name = "container_background" + str(index)

    dark_or_light = st.context.theme.type

    if index % 2 == 0:
        if dark_or_light == 'light':
            color = "#EEEEEE"
        else:
            color = "#222222"
    else:
        if dark_or_light == 'light':
            color = "#DDDDDD"
        else:
            color = "#333333"
    
    style_str = "<style> .st-key-" + name + " {background-color: " + color + ";} </style>"
    return style_str

    

if 'is_logged_in' not in st.session_state:
    st.session_state.is_logged_in = False

if 'username' not in st.session_state:
    st.session_state.username = None
if 'search_page' not in st.session_state:
    st.session_state.search_page = 1

file = "user_auth.db"
with sql.connect(file) as conn:
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT, password TEXT)''')
    conn.commit()

def sign_up(username, password):
    if not username or not password:
        st.error('Please enter both username and password.')
        return False
    with sql.connect(file) as conn:
        cur = conn.cursor()
        if cur.execute('SELECT username FROM users WHERE username = ?', (username,)).fetchone():
            st.error('Username already exists. Please choose a different username.')
            return False
    if len(password) < 8:
        st.error('Password must be at least 8 characters long.')
        return False
    if len(username) < 3:
        st.error('Username must be at least 3 characters long.')
        return False
    password_hash = bc.hashpw(password.encode('utf8'), bc.gensalt())
    with sql.connect(file) as conn:
        cur = conn.cursor()
        cur.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password_hash))
        conn.commit()
    st.session_state.is_logged_in = True
    st.session_state.username = username
    return True

def log_in(username, password):
    if not username or not password:
        st.error('Please enter both username and password.')
        return False
    with sql.connect(file) as conn:
        cur = conn.cursor()
        user = cur.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        if user and bc.checkpw(password.encode('utf8'), user[1]):
            st.session_state.is_logged_in = True
            st.session_state.username = username
            return True
        else:
            st.error('Invalid username or password.')
            return False

def db_table_to_dict(db_filename, table_name, table_columns, table_columns_types):
    columns_no_types = ''
    columns_with_types = ''
    for i in range(len(table_columns)):
        columns_no_types += table_columns[i]
        columns_with_types += table_columns[i] + ' ' + table_columns_types[i]
        if i != len(table_columns) - 1:
            columns_with_types += ', '
            columns_no_types += ', '
    
    conn = sql.connect(db_filename)
    c = conn.cursor()
    c.execute(f'CREATE TABLE IF NOT EXISTS {table_name} (id INTEGER PRIMARY KEY AUTOINCREMENT, {columns_with_types})')
    conn.commit()

    # Now we actually get the data
    c.execute(f'SELECT {columns_no_types} FROM {table_name}')
    rows = c.fetchall()

    conn.close()

    data_dict = {col: [] for col in table_columns}
    for row in rows:
        for i, col in enumerate(table_columns):
            data_dict[col].append(row[i])
    
    return data_dict


def dict_to_db_table(db_filename, table_name, data_dict):
    # First we figure out the shape of the table
    table_columns = list(data_dict.keys())
    table_columns_types = []
    for i in range(len(table_columns)):
        key = table_columns[i]
        if type(key) == int:
            table_columns_types.append("INTEGER")
        elif type(key) == float:
            table_columns_types.append("FLOAT")
        else:
            table_columns[i] = str(key)
            table_columns_types.append("TEXT")

    columns_no_types = ''
    columns_with_types = ''
    for i in range(len(table_columns)):
        columns_no_types += table_columns[i]
        columns_with_types += table_columns[i] + ' ' + table_columns_types[i]
        if i != len(table_columns) - 1:
            columns_with_types += ', '
            columns_no_types += ', '
    
    conn = sql.connect(db_filename)
    c = conn.cursor()
    # Note that it overwrites the previous one
    c.execute(f'DROP TABLE IF EXISTS {table_name}')
    c.execute(f'CREATE TABLE {table_name} (id INTEGER PRIMARY KEY AUTOINCREMENT, {columns_with_types})')
    conn.commit()

    unknown_string = ''
    for i in range(len(table_columns)):
        unknown_string += '?'
        if i != len(table_columns) - 1:
            unknown_string += ', '

    for i in range(len(data_dict[table_columns[0]])):  # For each row of the table
        data_append = []
        for key in table_columns:
            if type(data_dict[key][i]) == list:
                data_append.append(str(data_dict[key][i]))
            else:
                data_append.append(data_dict[key][i])

        c.execute(f'''
                INSERT INTO {table_name} ({columns_no_types})
                VALUES ({unknown_string})
            ''', data_append)
        conn.commit()

    conn.close()




def add_search_to_history(username, roundtrip=True, origin="LHR", destination="DXB", departure_date=date.today(), return_date=date.today(), passengers=1, cabin_class="Economy"):
    db_filename = "user_auth.db"
    if roundtrip:
        roundtrip_str = "True"
        return_date_str = return_date.strftime("%Y-%m-%d")
    else:
        roundtrip_str = "False"
        return_date_str = ""
    departure_date_str = departure_date.strftime("%Y-%m-%d")

    table_columns = ["roundtrip", "origin", "destination", "departure_date", "return_date", "passengers", "cabin_class"]
    table_columns_types = ["TEXT", "TEXT", "TEXT", "TEXT", "TEXT", "INTEGER", "TEXT"]
    table_name = f"search_history_{username}"

    # Fetch existing history or create new dict
    try:
        history_dict = db_table_to_dict(db_filename, table_name, table_columns, table_columns_types)
    except:
        history_dict = {col: [] for col in table_columns}

    data_append = [roundtrip_str, origin, destination, departure_date_str, return_date_str, passengers, cabin_class]
    for i, key in enumerate(table_columns):
        history_dict[key].append(data_append[i])

    dict_to_db_table(db_filename, table_name, history_dict)


def delete_search_history(username):
    db_filename = "user_auth.db"

    table_columns = ["roundtrip", "origin", "destination", "departure_date", "return_date", "passengers", "cabin_class"]
    table_name = f"search_history_{username}"

    # Fetch existing history or create new dict
    history_dict = {col: [] for col in table_columns}

    dict_to_db_table(db_filename, table_name, history_dict)


def change_mode_creator(new_mode):
    def change_mode():
        st.session_state.mode = new_mode
    return change_mode

# Sidebar
st.sidebar.header('ROVE :small[:blue[Redemptions]]')
st.sidebar.button('Welcome', on_click=change_mode_creator('Welcome'))
st.sidebar.button('Find Flights', on_click=change_mode_creator('Find Flights'))
if st.session_state.is_logged_in:
    st.sidebar.button('Profile', on_click=change_mode_creator('Profile'))
    st.sidebar.button('Log Out', on_click=change_mode_creator('Log Out'))
else:
    st.sidebar.button('Log In', on_click=change_mode_creator('Log In'))

# Initialize saved miles dict in session state
if 'saved_miles_dict' not in st.session_state:
    st.session_state.saved_miles_dict = {airline: 0 for airline in AIRLINES_WITH_VPM_DATA_CODES}

# Current mode
current_mode = st.session_state.get('mode', 'Welcome')

if current_mode == 'Welcome':
    col1, col2 = st.columns([1,3])
    with col1:
        st.image("https://cdn-icons-png.flaticon.com/512/854/854878.png", width=100)
    with col2:
        st.title("✈️ Welcome to Rove :blue[Redemptions]")
        st.markdown("##### Your smart flight rewards assistant for finding the best **miles-based** flights — fast.")
    st.markdown("---")
    st.markdown("""
    🔍 **Search with filters.**  
    🎯 **Maximize your value per mile.**  
    🧳 **Track your miles across airlines.**

    ---  
    """)
    st.markdown("#### 👉 Get started by logging in and selecting **Find Flights** from the sidebar.")

elif current_mode == 'Find Flights':
    if not st.session_state.is_logged_in:
        st.warning("Please log in to find flights.")
    else:
        st.title("Find Flights Now")
        st.header("Booking info:")

        roundtrip = st.checkbox("Roundtrip?", value=True)

        cols = st.columns([1,1,1.5,1.5,1,2])
        origin = cols[0].text_input("From (IATA)", max_chars=4, value="LHR").upper()
        destination = cols[1].text_input("To (IATA)", max_chars=4, value="DXB").upper()
        departure_date = cols[2].date_input("Departure date", min_value=date.today())
        if roundtrip:
            return_date = cols[3].date_input("Return date", min_value=departure_date)
        else:
            cols[3].markdown(":small[Return date]")
            cols[3].markdown(":x:")
            return_date = None
        passengers = cols[4].number_input("Passengers", min_value=1, max_value=10, value=1)
        cabin_class = cols[5].selectbox("Cabin Class", ['Economy', 'Premium Economy', 'Business', 'First Class'])

        st.subheader("Use Miles")
        selected_airlines = st.multiselect("Airlines You Have Rewards With", AIRLINES_WITH_VPM_DATA_NAMES)
        mile_inputs = {}
        if selected_airlines:
            mile_cols = st.columns(len(selected_airlines))
            for i, airline in enumerate(selected_airlines):
                miles = mile_cols[i].number_input(f"{airline} miles", min_value=0, value=st.session_state.saved_miles_dict.get(airline, 0))
                mile_inputs[airline] = miles
                st.session_state.saved_miles_dict[airline] = miles
        else:
            st.info("Select airlines to enter miles.")

        st.subheader("Filters")
        filters = st.multiselect("Search filters", options=SEARCH_FILTERS)

        if st.button("Search!"):
            # Save search
            add_search_to_history(st.session_state.username, roundtrip, origin, destination, departure_date, return_date, passengers, cabin_class)

            with st.spinner("Fetching flights and calculating redemptions from the Duffel API, please wait. This should not take more than a couple of minutes."):
                try:
                    search_mode = "cheapest"
                    if 'Maximize Overall Value' in filters:
                        search_mode = "overall_value"
                    
                    only_miles = 'Only Show Flights Payable With Miles' in filters
                    
                    selected_airlines_codes = []
                    for name in selected_airlines:
                        selected_airlines_codes.append(synth.airline_name_to_code(name))
                    
                    real_cabin_class = CABIN_CLASS_FANCY_TO_BASIC[cabin_class]

                    if roundtrip:
                        return_date_str=return_date.strftime("%Y-%m-%d")
                    else:
                        return_date_str = None

                    all_routings = synth.get_dict_for_all_possible_routings(origin, destination,
                                                                            passengers, real_cabin_class, departure_date.strftime("%Y-%m-%d"),
                                                                            return_date_str=return_date_str)
                    
                    synth.add_flights_to_master_flight_list(all_routings)
                    
                    useful_dict = synth.get_useful_info_of_top_n_sorted_flights(FLIGHTS_SHOWN, search_mode, origin, destination,
                                                                                passengers, real_cabin_class, departure_date.strftime("%Y-%m-%d"),
                                                                                return_date_str=return_date_str,
                                                                                only_flights_with_award_airlines=only_miles,
                                                                                airlines_with_miles=selected_airlines_codes)

                    
                    flights_returned = len(useful_dict["is_synthetic"])

                    # Display results
                    st.subheader("🔎 Suggested Redemptions")

                    def render_tag(tag):
                        tag_colors = {
                            "Best Value": "green",
                            # "Popular Choice": "blue",
                            # "Flexible": "orange",
                            "Premium Value": "pink",
                            "Luxury": "orange",
                            "Best VPM": "teal"
                            # "Synthetic": "teal"
                        }
                        color = tag_colors.get(tag, "gray")
                        return f"<span style='color:{color}; font-weight:bold'>{tag}</span>"


                    # We attach the tags to the right options
                    tags_to_ids = {
                            "Best Value" : [],
                            # "Popular Choice": ,
                            # "Flexible": "orange",
                            "Premium Value" : [],
                            "Luxury" : [],
                            "Best VPM" : []
                            # "Synthetic": "teal"
                    }

                    useful_dict = synth.sort_dict_by_lists_sequentially(useful_dict, ["overall_value", "cash_price"], reverse_list=[False, False])
                    tags_to_ids["Best Value"].append(useful_dict["unique_id"][0])

                    useful_dict = synth.sort_dict_by_lists_sequentially(useful_dict, ["average_perceived_value", "cash_price"], reverse_list=[True, False])
                    tags_to_ids["Luxury"].append(useful_dict["unique_id"][0])
                    tags_to_ids["Premium Value"].append(useful_dict["unique_id"][1])

                    useful_dict = synth.sort_dict_by_lists_sequentially(useful_dict, ["vpm", "cash_price"], reverse_list=[True, False])
                    if useful_dict["vpm"][0] > 0:
                        tags_to_ids["Best VPM"].append(useful_dict["unique_id"][0])

                    
                    # And re-sort
                    if 'Sort by VPM' in filters:
                        useful_dict = synth.sort_dict_by_lists_sequentially(useful_dict, ["vpm", "cash_price"], reverse_list=[True, False])
                    elif search_mode == "cheapest":
                        useful_dict = synth.sort_dict_by_lists_sequentially(useful_dict, ["cash_price", "overall_value"], reverse_list=[False, False])
                    elif search_mode == "overall_value":
                        useful_dict = synth.sort_dict_by_lists_sequentially(useful_dict, ["overall_value", "cash_price"], reverse_list=[False, False])


                    def show_redemption_card(single_dict, index):
                        graphics_key = "container_background" + str(index)

                        style_str = css_style_by_index(index)
                        st.markdown(style_str, unsafe_allow_html=True)

                        with st.container(key=graphics_key):
                            if single_dict["is_synthetic"]:
                                st.header("Synthetic Routing")
                                cols = st.columns([5,2])

                                departure_bookings = len(single_dict["dep_airline_names"])
                                

                                with cols[0]:
                                    for i in range(departure_bookings):  # For each booking of the departure
                                        airline_name = single_dict["dep_airline_names"][i]
                                        dep_segments = single_dict["dep_segments_str"][i]
                                        st.markdown(f"### ✈️ {airline_name}")
                                        st.markdown(f"Departure Booking {i + 1}: {dep_segments}")
                                    
                                    if single_dict["ret_segments_str"]:
                                        return_bookings = len(single_dict["ret_airline_names"])
                                        for i in range(return_bookings):  # For each booking of the departure
                                            airline_name = single_dict["ret_airline_names"][i]
                                            ret_segments = single_dict["ret_segments_str"][i]
                                            st.markdown(f"### ✈️ {airline_name}")
                                            st.markdown(f"Return Booking {i + 1}: {ret_segments}")

                                    # st.markdown(f"**Value-per-mile**: {redemption['vpm']}¢")
                                    # st.markdown(f"**Fees**: {redemption['fees']}")
                                    # st.markdown(f"**Total Cost**: {redemption['total_cost']}")
                                    unique_id = single_dict["unique_id"]
                                    for key in tags_to_ids:
                                        if unique_id in tags_to_ids[key]:
                                            st.markdown(f"**💡 Tag**: {render_tag(key)}", unsafe_allow_html=True)
                            else:
                                st.header("Single Booking")
                                cols = st.columns([5,2])

                                airline_name = single_dict["dep_airline_names"][0]
                                dep_segments = single_dict["dep_segments_str"][0]
                                if single_dict["ret_segments_str"]:
                                    ret_segments = single_dict["ret_segments_str"][0]
                                else:
                                    ret_segments = None

                                with cols[0]:
                                    st.markdown(f"### ✈️ {airline_name}")
                                    if ret_segments:
                                        st.markdown(f"Departure: {dep_segments}")
                                        st.markdown(f"Return: {ret_segments}")
                                    else:
                                        st.markdown(f"Intinerary: {dep_segments}")

                                    # st.markdown(f"**Value-per-mile**: {redemption['vpm']}¢")
                                    # st.markdown(f"**Fees**: {redemption['fees']}")
                                    # st.markdown(f"**Total Cost**: {redemption['total_cost']}")
                                    unique_id = single_dict["unique_id"]
                                    for key in tags_to_ids:
                                        if unique_id in tags_to_ids[key]:
                                            st.markdown(f"**💡 Tag**: {render_tag(key)}", unsafe_allow_html=True)
                            
                            with cols[1]:
                                    total_cash = round(single_dict['cash_price'], 2)
                                    if len(single_dict["miles_price_by_airline_or_cash"]) > 1 or "cash" not in list(single_dict["miles_price_by_airline_or_cash"].keys()):
                                        st.markdown(f"**Paying With Miles**")

                                        miles_sum = 0

                                        for code in selected_airlines_codes:
                                            if code in list(single_dict["miles_price_by_airline_or_cash"].keys()):
                                                code_miles = round(single_dict['miles_price_by_airline_or_cash'][code])
                                                st.markdown(f"{synth.airline_code_to_name(code)} miles: {code_miles}")
                                                miles_sum += code_miles

                                        if 'cash' in list(single_dict["miles_price_by_airline_or_cash"].keys()):
                                            cash_remainder = single_dict['miles_price_by_airline_or_cash']['cash']
                                            st.markdown(f"Remainder in Cash: {cash_remainder} USD")
                                            value = total_cash - cash_remainder
                                        else:
                                            value = total_cash
                                        
                                        vpm = round(single_dict["vpm"], 2)
                                        st.markdown(f"Value Per Mile (VPM): {vpm} ¢")

                                        st.markdown("---")
                                    
                                    st.markdown(f"**Paying with Cash**")
                                    st.markdown(f"{total_cash} USD")


                                # try:
                                #     savings_value = int(redemption["savings"].replace("$",""))
                                # except:
                                #     savings_value = 0
                                # st.metric(label="You Save", value=redemption["savings"])
                                # st.progress(min(savings_value, 200)/200)
                                # st.button("Select", key=f"select_{index}")
                            # st.markdown("---")

                    for i in range(flights_returned):
                        single_dict = {}
                        for key in list(useful_dict.keys()):
                            single_dict[key] = useful_dict[key][i]

                        show_redemption_card(single_dict, i)

                except Exception as e:
                    st.error(f"An error occurred during flight search: {e}")

elif current_mode == 'Profile':
    st.title(f"{st.session_state.username}'s Profile")
    st.header("Flight Search History")

    db_filename = "user_auth.db"
    table_columns = ["roundtrip", "origin", "destination", "departure_date", "return_date", "passengers", "cabin_class"]
    pretty_columns = ["Roundtrip?", "Origin", "Destination", "Departure date", "Return date", "Passengers", "Cabin Class"]
    table_columns_types = ["TEXT", "TEXT", "TEXT", "TEXT", "TEXT", "INTEGER", "TEXT"]
    table_name = f"search_history_{st.session_state.username}"

    try:
        history_dict = db_table_to_dict(db_filename, table_name, table_columns, table_columns_types)
    except:
        history_dict = {col: [] for col in table_columns}

    entries = len(history_dict[table_columns[0]])
    total_pages = (entries + SEARCHES_SHOWN - 1) // SEARCHES_SHOWN

    if total_pages == 0:
        st.subheader("No searches found. Go to the 'Find Flights' page to make your first search!")
    else:
        for key in table_columns:
            history_dict[key].reverse()

        column_widths = [1,1,1.5,1.5,1,2]
        name_cols = st.columns(column_widths)
        for i in range(len(pretty_columns)-1):
            true_idx = i+1
            name_cols[i].markdown(f":small[{pretty_columns[true_idx]}]")

        st.divider()

        search_cols = st.columns(column_widths)
        start_idx = SEARCHES_SHOWN * (st.session_state.search_page -1)
        cur_idx = start_idx
        while cur_idx < entries and cur_idx - start_idx < SEARCHES_SHOWN:
            for i in range(len(table_columns)-1):
                true_idx = i+1
                key = table_columns[true_idx]
                if key == "return_date" and history_dict["roundtrip"][cur_idx] == "False":
                    search_cols[i].markdown(":x:")
                else:
                    search_cols[i].text(history_dict[key][cur_idx])
            cur_idx += 1

        if cur_idx == start_idx:
            st.subheader("No searches found. Go to the 'Find Flights' page to make your first search!")

        st.divider()

        page_cols = st.columns([1,2,1,2,1])
        first_page = (st.session_state.search_page == 1)
        last_page = (st.session_state.search_page == total_pages)

        if not first_page:
            if page_cols[0].button("Previous Page"):
                st.session_state.search_page -= 1
                st.rerun()

        if not last_page:
            if page_cols[4].button("Next Page"):
                st.session_state.search_page += 1
                st.rerun()

        page_cols[2].text(f"Page {st.session_state.search_page} of {total_pages}")
    
    if entries > 0:
        delete_button = st.button("Delete Search History")
        if delete_button:
            delete_search_history(st.session_state.username)
            st.rerun()

elif current_mode == 'Log In':
    st.title("Log In")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    st.button("Don't have an account?", on_click=change_mode_creator('Sign Up'))
    if st.button("Log In"):
        if log_in(username, password):
            st.session_state.user_type = 'account'
            st.session_state.mode = 'Profile'
            st.rerun()

elif current_mode == 'Log Out':
    st.session_state.is_logged_in = False
    st.session_state.username = None
    st.session_state.search_page = 1
    st.success("You have logged out.")
    st.session_state.mode = 'Welcome'
    st.rerun()

elif current_mode == 'Sign Up':
    st.title("Sign Up")
    username = st.text_input("Choose a username")
    password = st.text_input("Choose a password", type="password")
    password_confirm = st.text_input("Confirm password", type="password")
    st.button("Already have an account? Log In", on_click=change_mode_creator('Log In'))
    if st.button("Sign Up"):
        if password != password_confirm:
            st.error("Passwords do not match.")
        else:
            if sign_up(username, password):
                st.success("Account created. You are now logged in.")
                st.session_state.mode = 'Welcome'
                st.rerun()

# Utility functions for DB <-> dict (reused from your backend)

def dict_to_db_table(db_filename, table_name, dict_data):
    with sql.connect(db_filename) as conn:
        cur = conn.cursor()
        # Create table if not exists
        columns = ', '.join([f"{k} TEXT" for k in dict_data.keys()])
        cur.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({columns})")
        # Clear table
        cur.execute(f"DELETE FROM {table_name}")
        # Insert data rows
        n = len(next(iter(dict_data.values())))
        for i in range(n):
            values = tuple(dict_data[k][i] for k in dict_data.keys())
            placeholders = ','.join(['?']*len(values))
            cur.execute(f"INSERT INTO {table_name} VALUES ({placeholders})", values)
        conn.commit()

def db_table_to_dict(db_filename, table_name, columns, columns_types):
    dict_data = {col: [] for col in columns}
    with sql.connect(db_filename) as conn:
        cur = conn.cursor()
        try:
            cur.execute(f"SELECT * FROM {table_name}")
            rows = cur.fetchall()
            for row in rows:
                for i, col in enumerate(columns):
                    dict_data[col].append(row[i])
        except sql.OperationalError:
            pass
    return dict_data
