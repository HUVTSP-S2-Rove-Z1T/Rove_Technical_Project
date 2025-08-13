import streamlit as st
from datetime import date
import Synthetic_and_VPM_logic as synth
import sqlite3 as sql
import bcrypt as bc

# Constants and session state setup (reuse your constants)
AIRLINES_WITH_VPM_DATA = ['United', 'Delta', 'Emirates']
SEARCH_FILTERS = ['Maximize Value', 'Free Wifi', 'Direct Flights Only']
<<<<<<< HEAD
USER_DB = "user_auth.db"
REDEMPTIONS_FILE = "redemptions.json"
=======
>>>>>>> ef92ce9 (Add Synthetic_and_VPM_logic.py, Final_UI.py, and Week_4_UI files)
SEARCHES_SHOWN = 10

if 'is_logged_in' not in st.session_state:
    st.session_state.is_logged_in = False

if 'username' not in st.session_state:
    st.session_state.username = None
if 'search_page' not in st.session_state:
    st.session_state.search_page = 1

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

<<<<<<< HEAD
def get_user_savings(username):
    if not username:
        return 0
    with sql.connect(USER_DB) as conn:
        cur = conn.cursor()
        result = cur.execute('SELECT total_savings FROM users WHERE username = ?', (username,)).fetchone()
        if result:
            return result[0]
        return 0
    
=======
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
>>>>>>> ef92ce9 (Add Synthetic_and_VPM_logic.py, Final_UI.py, and Week_4_UI files)

def change_mode_creator(new_mode):
    def change_mode():
        st.session_state.mode = new_mode
    return change_mode

<<<<<<< HEAD
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

    # We turn the weirder data types into strings
    if roundtrip:
        roundtrip = "True"
        return_date = return_date.strftime("%Y-%m-%d")
    else:
        roundtrip = "False"
        return_date = ""
    departure_date = departure_date.strftime("%Y-%m-%d")
    
    # Now we set up the table
    table_columns = ["roundtrip", "origin", "destination", "departure_date", "return_date", "passengers", "cabin_class"]
    table_columns_types = ["TEXT", "TEXT", "TEXT", "TEXT", "TEXT", "INTEGER", "TEXT"]
    table_name = f"search_history_{username}"

    history_dict = db_table_to_dict(db_filename, table_name, table_columns, table_columns_types)

    data_append = [roundtrip, origin, destination, departure_date, return_date, passengers, cabin_class]
    for i in range(len(table_columns)):
        key = table_columns[i]
        history_dict[key].append(data_append[i])
    
    dict_to_db_table(db_filename, table_name, history_dict)

def reset_savings(username):
    with sql.connect(USER_DB) as conn:
        cur = conn.cursor()
        cur.execute('UPDATE users SET total_savings = 0 WHERE username = ?', (username,))
        conn.commit()
    st.session_state['message'] = "Your savings have been reset to $0.00."

def display_message():
    st.toast(st.session_state['message'])
    del st.session_state['message']

def reset_password(old_password, new_password):
    if not old_password or not new_password:
        st.error('Please enter both old and new passwords.')
        return
    if len(new_password) < 8:
        st.error('New password must be at least 8 characters long.')
        return
    with sql.connect(USER_DB) as conn:
        cur = conn.cursor()
        user = cur.execute('SELECT * FROM users WHERE username = ?', (st.session_state.username,)).fetchone()
        if not bc.checkpw(old_password.encode('utf8'), user[1]):
            st.error('Old password is incorrect.')
        elif bc.checkpw(new_password.encode('utf8'), user[1]):
            st.error('New password cannot be the same as the old password.')
        else:
            hashed = bc.hashpw(new_password.encode('utf8'), bc.gensalt())
            cur.execute('UPDATE users SET password = ? WHERE username = ?', (hashed, st.session_state.username))
            st.success('Password changed successfully.')
        conn.commit()

# Sidebar navigation
=======
# Sidebar
>>>>>>> ef92ce9 (Add Synthetic_and_VPM_logic.py, Final_UI.py, and Week_4_UI files)
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
    st.session_state.saved_miles_dict = {airline: 0 for airline in AIRLINES_WITH_VPM_DATA}

<<<<<<< HEAD
if 'message' in st.session_state:
    display_message()

if mode == 'Welcome':
=======
# Current mode
current_mode = st.session_state.get('mode', 'Welcome')

if current_mode == 'Welcome':
>>>>>>> ef92ce9 (Add Synthetic_and_VPM_logic.py, Final_UI.py, and Week_4_UI files)
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
        selected_airlines = st.multiselect("Airlines You Have Rewards With", AIRLINES_WITH_VPM_DATA)
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

<<<<<<< HEAD


        def show_synthetic_card(option, idx):
            with st.container():
                cols = st.columns([5, 2])
                with cols[0]:
                    st.markdown(f"### ✈️ {option['route']}")
                    st.markdown(f"**Value-per-mile**: {option['vpm']}¢")
                    st.markdown(f"**Fees**: {option['total_fees']}")
                    st.markdown(f"**Total Cash Value**: {option['total_cash']}")
                    st.markdown(f"**Cabin Mix**: {option['cabin_mix']}")
                    if option.get('highlight'):
                        st.markdown(f"**💡 Highlights:** {' | '.join(option['highlight'])}")
                    st.markdown(f"**Airlines:** {', '.join(option['airlines'])}")
                with cols[1]: 
                    if st.button("Select", key=f"select_{idx}", on_click=lambda: select_redemption(synthetic_results[idx], idx)):
                        pass
                st.markdown("---")

                
        def select_redemption(option, i):
            with sql.connect(USER_DB) as conn:
                cur = conn.cursor()
                current = get_user_savings(st.session_state.username)
                new_total = current + float(option['total_cash'][1:])
                cur.execute('UPDATE users SET total_savings = ? WHERE username = ?', (new_total, st.session_state.username))
                conn.commit()
            st.session_state['message'] = f"You selected option {option['route']}! Your profile has been updated with your savings."


        if search_clicked:
            # We quickly save the flight to the search history
            add_search_to_history(st.session_state.username, roundtrip, origin, destination, departure_date, return_date, passengers, cabin_class)

            if not origin or not destination:
                st.error("Please enter both origin and destination airport codes.")
            else:
=======
            with st.spinner("Fetching flights and calculating redemptions..."):
>>>>>>> ef92ce9 (Add Synthetic_and_VPM_logic.py, Final_UI.py, and Week_4_UI files)
                try:
                    # Step 1: Get all possible routings (direct + multi-leg) from backend
                    whole_flights = synth.get_dict_for_all_possible_routings(
                        origin, destination, passengers, cabin_class.lower(), 
                        departure_date.strftime("%Y-%m-%d"),
                        return_date.strftime("%Y-%m-%d") if return_date else None
                    )

<<<<<<< HEAD


elif mode == 'Profile':
    if not st.session_state.is_logged_in:
        st.title("Please log in to view your profile.")
    else:
        st.title('Profile')
        st.markdown(f"### Welcome, **{st.session_state.username}**!")
        total_saved = get_user_savings(st.session_state.username)
        st.markdown(f"💰 **Total savings from using Rove:** ${total_saved:.2f}")
        st.button('Reset Savings', on_click=lambda: reset_savings(st.session_state.username))
        st.header("Flight Search History")

        # Now we set up the table
        db_filename = "user_auth.db"
        table_columns = ["roundtrip", "origin", "destination", "departure_date", "return_date", "passengers", "cabin_class"]
        pretty_columns = ["Roundtrip?", "Origin", "Destination", "Departure date", "Return date", "Passengers", "Cabin Class"]
        table_columns_types = ["TEXT", "TEXT", "TEXT", "TEXT", "TEXT", "INTEGER", "TEXT"]
        table_name = f"search_history_{st.session_state.username}"

        history_dict = db_table_to_dict(db_filename, table_name, table_columns, table_columns_types)
        entries = len(history_dict[table_columns[0]])
        total_pages = (entries + SEARCHES_SHOWN - 1) // SEARCHES_SHOWN

        if total_pages == 0:
            st.subheader("No searches found. Go to the \"Find Flights\" page to make your first search!")
        else:
            # Remember to sort from most recent to least recent
            for key in table_columns:
                history_dict[key].reverse()

            column_widths = [1, 1, 1.5, 1.5, 1, 2]

            name_columns = st.columns(column_widths)
            for i in range(len(pretty_columns) - 1):
                true_index = i + 1  # We skip the roundtrip one
                name_columns[i].markdown(f":small[{pretty_columns[true_index]}]")
            
            st.divider()

            search_columns = st.columns(column_widths)
            start_index = SEARCHES_SHOWN * (st.session_state.search_page - 1)
            current_index = start_index
            while current_index < entries and current_index - start_index < SEARCHES_SHOWN:
                for i in range(len(table_columns) - 1):
                    true_index = i + 1
                    key = table_columns[true_index]
                    if key == "return_date" and history_dict["roundtrip"][current_index] == "False":
                        search_columns[i].markdown(':x:')
                    else:
                        search_columns[i].text(history_dict[key][current_index])

                current_index += 1
            
            if current_index == start_index:
                st.subheader("No searches found. Go to the \"Find Flights\" page to make your first search!")
            
            st.divider()

            page_columns = st.columns([1, 2, 1, 2, 1])

            first_page = False
            last_page = False
            if st.session_state.search_page == 1:
                first_page = True
            if st.session_state.search_page == total_pages:
                last_page = True
            
            if not first_page:
                prev_button = page_columns[0].button("Previous Page")
                if prev_button:
                    st.session_state.search_page -= 1
                    st.rerun()

            if not last_page:
                next_button = page_columns[4].button("Next Page")
                if next_button:
                    st.session_state.search_page += 1
                    st.rerun()
            
            page_columns[2].text(f"Page {st.session_state.search_page} of {total_pages}")
        st.header("Change Password")
        old_password = st.text_input('Old Password', type='password', key='old_pass')
        new_password = st.text_input('New Password', type='password', key='new_pass')
        if st.button('Change Password', key='change_pass_btn'):
            reset_password(old_password, new_password)

elif mode == 'Log In':
    st.title('Log In')
    username = st.text_input('Username', key='login_user')
    password = st.text_input('Password', type='password', key='login_pass')
    if st.button("Don't have an account?", key='goto_signup'):
        st.session_state.mode = 'Sign Up'
        st.rerun()
    if st.button('Log In', key='login_btn'):
        if log_in(username, password):
            st.session_state.mode = 'Welcome'
            st.rerun()
=======
                    # Step 2: Add these flights to master list
                    synth.add_flights_to_master_flight_list(whole_flights)

                    # Step 3: Find synthetic routings from master list
                    dep_dict, dep_leg_orders, ret_dict, ret_leg_orders = synth.find_possible_routings_from_master_list(
                        origin, destination, passengers, cabin_class.lower(),
                        departure_date.strftime("%Y-%m-%d"),
                        return_date.strftime("%Y-%m-%d") if return_date else None
                    )

                    # Step 4: Combine and prepare redemption options list
                    # For demo, we'll prepare a simple flat list of redemption options from dep_dict flights,
                    # with synthesized VPM based on sample calculation or placeholders.
                    # You should replace this with your actual value-per-mile logic from backend.

                    def prepare_redemption_options(dep_flights_dict, leg_orders, ret_flights_dict=None):
                        options = []
                        for idx, leg_order in enumerate(leg_orders):
                            # Combine legs into a single itinerary string
                            legs = ' -> '.join([f"{leg[0]}-{leg[1]}" for leg in leg_order])
                            # Example: calculate total miles and cost placeholders
                            total_miles = 0
                            total_fees = 0.0
                            # Simplify: sum miles and fees of legs (you can pull from your dict keys like 'miles', 'fees' if present)
                            for leg in leg_order:
                                key = leg
                                # Try to find matching flight(s) in dep_flights_dict for this leg
                                # This is example logic, adjust based on your actual data structure
                                if key in dep_flights_dict:
                                    # Just pick the first flight for demo
                                    miles = dep_flights_dict[key][0].get('miles', 1000) if isinstance(dep_flights_dict[key][0], dict) else 1000
                                    fees = dep_flights_dict[key][0].get('fees', 50) if isinstance(dep_flights_dict[key][0], dict) else 50
                                else:
                                    miles = 1000
                                    fees = 50
                                total_miles += miles
                                total_fees += fees

                            vpm = round(1500 / total_miles * 100, 2)  # Dummy VPM calculation
                            total_cost = f"{int(total_miles)} miles + ${total_fees:.2f}"
                            option = {
                                "option_name": f"Synthetic Routing Option #{idx+1}: {legs}",
                                "vpm": vpm,
                                "fees": f"${total_fees:.2f}",
                                "total_cost": total_cost,
                                "tag": "Synthetic",
                                "savings": f"${int(vpm*20)}"
                            }
                            options.append(option)
                        return options

                    redemption_options = prepare_redemption_options(dep_dict, dep_leg_orders, ret_dict)

                    # Sort by VPM desc
                    redemption_options.sort(key=lambda x: x['vpm'], reverse=True)

                    # Display results
                    st.subheader("🔎 Suggested Redemptions")
                    st.markdown("Results ranked by estimated value-per-mile (VPM).")

                    def render_tag(tag):
                        tag_colors = {
                            "Best Value": "green",
                            "Popular Choice": "blue",
                            "Flexible": "orange",
                            "Premium Value": "purple",
                            "Luxury": "darkred",
                            "Synthetic": "teal"
                        }
                        color = tag_colors.get(tag, "gray")
                        return f"<span style='color:{color}; font-weight:bold'>{tag}</span>"

                    def show_redemption_card(redemption, index):
                        with st.container():
                            cols = st.columns([5,2])
                            with cols[0]:
                                st.markdown(f"### ✈️ {redemption['option_name']}")
                                st.markdown(f"**Value-per-mile**: {redemption['vpm']}¢")
                                st.markdown(f"**Fees**: {redemption['fees']}")
                                st.markdown(f"**Total Cost**: {redemption['total_cost']}")
                                st.markdown(f"**💡 Tag**: {render_tag(redemption['tag'])}", unsafe_allow_html=True)
                            with cols[1]:
                                try:
                                    savings_value = int(redemption["savings"].replace("$",""))
                                except:
                                    savings_value = 0
                                st.metric(label="You Save", value=redemption["savings"])
                                st.progress(min(savings_value, 200)/200)
                                st.button("Select", key=f"select_{index}")
                            st.markdown("---")

                    for i, redemption in enumerate(redemption_options):
                        show_redemption_card(redemption, i)

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
                st.experimental_rerun()

        if not last_page:
            if page_cols[4].button("Next Page"):
                st.session_state.search_page += 1
                st.experimental_rerun()

        page_cols[2].text(f"Page {st.session_state.search_page} of {total_pages}")

elif current_mode == 'Log In':
    st.title("Log In")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    st.button("Don't have an account?", on_click=change_mode_creator('Sign Up'))
    if st.button("Log In"):
        if log_in(username, password):
            st.session_state.user_type = 'account'
            st.experimental_rerun()
>>>>>>> ef92ce9 (Add Synthetic_and_VPM_logic.py, Final_UI.py, and Week_4_UI files)

elif current_mode == 'Log Out':
    st.session_state.is_logged_in = False
    st.session_state.username = None
<<<<<<< HEAD
    st.session_state.mode = 'Welcome'
    st.rerun()

elif mode == 'Sign Up':
    st.title('Sign Up')
    username = st.text_input('Username', key='signup_user')
    password = st.text_input('Password', type='password', key='signup_pass')
    if st.button("Already have an account?", key='goto_login'):
        st.session_state.mode = 'Log In'
        st.rerun()
    if st.button('Sign Up', key='signup_btn'):
        if sign_up(username, password):
            st.session_state.mode = 'Welcome'
            st.rerun()
=======
    st.session_state.search_page = 1
    st.success("You have logged out.")
    st.experimental_rerun()

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
                st.experimental_rerun()

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
>>>>>>> ef92ce9 (Add Synthetic_and_VPM_logic.py, Final_UI.py, and Week_4_UI files)
