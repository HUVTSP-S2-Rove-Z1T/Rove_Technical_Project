import streamlit as st
from datetime import date, timedelta
import sqlite3 as sql
import bcrypt as bc

# These lists will get bigger
AIRLINES_WITH_VPM_DATA = ['United', 'Delta', 'Emirates']
SEARCH_FILTERS = ['Maximize Value', 'Free Wifi', 'Direct Flights Only']
SEARCHES_SHOWN = 10
if 'is_logged_in' not in st.session_state:
    st.session_state.is_logged_in = False

if 'username' not in st.session_state:
    st.session_state.username = None

if 'search_page' not in st.session_state:
    st.session_state.search_page = 1

file = "user_auth.db"
with sql.connect(file) as conn:
    cur = conn.cursor()
    # This creates the table, if we want to store additional info like prev flights and redemptions, we can add more columns
    cur.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT, password TEXT)''')
    # We'll also have a table for each user in the same db for the flight search history. The name will be f"search_history_{username}"
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
    password = bc.hashpw(password.encode('utf8'), bc.gensalt())
    with sql.connect(file) as conn:
        cur = conn.cursor()
        cur.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
        conn.commit()
    st.session_state.is_logged_in = True
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
    




# We set up data that we want saved between refreshes with "st.session_state"
if 'mode' not in st.session_state:
    st.session_state.mode = 'Welcome'

if 'user_type' not in st.session_state:
    st.session_state.user_type = 'guest'

def change_mode_creator(new_mode):
    def change_mode():
        st.session_state.mode = new_mode
    return change_mode

# Setting up the sidebar
st.sidebar.header('ROVE :small[:blue[Redemptions]]')
st.sidebar.button('Welcome', on_click=change_mode_creator('Welcome'))
st.sidebar.button('Find Flights', on_click=change_mode_creator('Find Flights'))
if st.session_state.user_type == 'guest':
    st.sidebar.button('Log In', on_click=change_mode_creator('Log In'))
else:
    st.sidebar.button('Profile', on_click=change_mode_creator('Profile'))
    st.sidebar.button('Log Out', on_click=change_mode_creator('Log Out'))

# These are some variables used for the "Find Flights" mode
if 'saved_miles_dict' not in st.session_state:
    st.session_state.saved_miles_dict = {}
    for airline in AIRLINES_WITH_VPM_DATA:
        st.session_state.saved_miles_dict[airline] = 0


# This is where the real work starts, each of the if statements below should contain the corresponding page.
current_mode = st.session_state.mode
if current_mode == 'Welcome':
    col1, col2 = st.columns([1, 3])

    with col1:
        st.image("https://cdn-icons-png.flaticon.com/512/854/854878.png", width=100)  # Example image URL

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
    
    st.markdown("#### 👉 Get started by creating account by selecting ***Log In*** and finding your redemptions by selecting ***Find Flights*** in the sidebar.")
elif current_mode == 'Find Flights':
    if st.session_state.is_logged_in:
        # Chase and Abdullah, the output part can go below, where the next comment is
        st.title('Find Flights Now')
        st.header('Booking info:')
        roundtrip = st.checkbox('Roundtrip?', value=True)

        # The column order is: origin, destination, departure date, return date, number of passengers, cabin class
        booking_columns = st.columns([1, 1, 1.5, 1.5, 1, 2])

        origin = booking_columns[0].text_input('From', max_chars=4)
        destination = booking_columns[1].text_input('To', max_chars=4)
        departure_date = booking_columns[2].date_input('Departure date', min_value=date.today())
        if roundtrip:
            return_date = booking_columns[3].date_input('Return date', min_value=departure_date)
        else:
            booking_columns[3].markdown(':small[Return date]')
            booking_columns[3].markdown(':x:')
            return_date = None
            # Other options: :red_circle:, :no_entry:, :no_entry_sign:
        passengers = booking_columns[4].number_input('Passengers', min_value=1, max_value=100)
        cabin_class = booking_columns[5].selectbox('Cabin Class', ['Economy', 'Premium Economy', 'Business', 'First Class'])

        st.subheader('Use Miles')

        all_airlines = st.multiselect('Airlines You Have Rewards With', AIRLINES_WITH_VPM_DATA)
        if len(all_airlines) > 0:
            mile_columns = st.columns(len(all_airlines))
            for i in range(len(all_airlines)):
                this_mile_input = mile_columns[i].number_input(all_airlines[i] + ' miles', min_value=0)
                st.session_state.saved_miles_dict[all_airlines[i]] = this_mile_input
        
        st.subheader('Filters')
        st.multiselect('Search filters', options=SEARCH_FILTERS)

        search_button = st.button('Search!')
        

        if search_button:
            # We quickly save the flight to the search history
            add_search_to_history(st.session_state.username, roundtrip, origin, destination, departure_date, return_date, passengers, cabin_class)

            # Sample redemption data (replace with real backend data later)
            redemptions = [
                {
                    "option_name": "United Saver Award – Economy",
                    "vpm": 2.1,
                    "fees": "$5.60",
                    "total_cost": "25,000 miles + $5.60",
                    "tag": "Best Value",
                    "savings": "$115"
                },
                {
                    "option_name": "Delta SkyMiles – Main Cabin",
                    "vpm": 1.8,
                    "fees": "$11.20",
                    "total_cost": "30,000 miles + $11.20",
                    "tag": "Popular Choice",
                    "savings": "$100"
                },
                {
                    "option_name": "Emirates Flex Plus – Economy",
                    "vpm": 1.5,
                    "fees": "$55.00",
                    "total_cost": "42,500 miles + $55.00",
                    "tag": "Flexible",
                    "savings": "$95"
                },
                {
                    "option_name": "United Standard Award – Business",
                    "vpm": 2.4,
                    "fees": "$10.10",
                    "total_cost": "60,000 miles + $10.10",
                    "tag": "Premium Value",
                    "savings": "$160"
                },
                {
                    "option_name": "Delta One – Business Class",
                    "vpm": 1.9,
                    "fees": "$28.80",
                    "total_cost": "70,000 miles + $28.80",
                    "tag": "Luxury",
                    "savings": "$140"
                }
            ]

            # Sort redemptions by highest value-per-mile
            redemptions.sort(key=lambda x: x["vpm"], reverse=True)

            # Visual tag coloring logic
            def render_tag(tag):
                tag_colors = {
                    "Best Value": "green",
                    "Popular Choice": "blue",
                    "Flexible": "orange",
                    "Premium Value": "purple",
                    "Luxury": "darkred"
                }
                color = tag_colors.get(tag, "gray")
                return f"<span style='color:{color}; font-weight:bold'>{tag}</span>"

            # Function to show one redemption card
            def show_redemption_card(redemption, index):
                with st.container():
                    cols = st.columns([5, 2])
                    with cols[0]:
                        st.markdown(f"### ✈️ {redemption['option_name']}")
                        st.markdown(f"**Value-per-mile**: {redemption['vpm']}¢")
                        st.markdown(f"**Fees**: {redemption['fees']}")
                        st.markdown(f"**Total Cost**: {redemption['total_cost']}")
                        st.markdown(f"**💡 Tag**: {render_tag(redemption['tag'])}", unsafe_allow_html=True)
                    with cols[1]:
                        # Convert savings string to int
                        try:
                            savings_value = int(redemption["savings"].replace("$", ""))
                        except:
                            savings_value = 0
                        st.metric(label="You Save", value=redemption["savings"])
                        st.progress(min(savings_value, 200) / 200)  # Assuming $200 is max savings
                        st.button("Select", key=f"select_{index}")
                    st.markdown("---")

            # Display section
            st.subheader("🔎 Suggested Redemptions")
            st.markdown("Results ranked by estimated value-per-mile (VPM).")

            # Show each redemption card
            for i, redemption in enumerate(redemptions):
                show_redemption_card(redemption, i)

                
        else:
            st.title("Please log in to find flights.")

            #Feedback Form
            with st.form(key='feedback_form'):
                st.subheader("How was your experience with this service?")
                faces = st.feedback("faces")
                improvement = st.text_input("What feature(s) would improve this product?")
                additional_comments = st.text_input("Any additional comments?:")
                submit_feedback = st.form_submit_button("Submit")

elif current_mode == 'Profile':
    st.title(f'{st.session_state.username}\'s Profile')

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

        







elif current_mode == 'Log In':
    st.title('Log In')
    username = st.text_input('Username')
    password = st.text_input('Password', type='password')
    switch = st.button("Don't have an account?", on_click=change_mode_creator('Sign Up'))
    if st.button('Log In'):
        if log_in(username, password):
            st.session_state.user_type = 'account'
            st.session_state.mode = 'Welcome'
            st.rerun()

elif current_mode == 'Log Out':
    st.session_state.user_type = 'guest'
    st.session_state.mode = 'Welcome'
    st.session_state.is_logged_in = False
    st.rerun()

elif current_mode == 'Sign Up':
    st.title('Sign Up')
    username = st.text_input('Username')
    password = st.text_input('Password', type='password')
    switch = st.button("Already have an account?", on_click=change_mode_creator('Log In'))
    if st.button('Sign Up'):
        if sign_up(username, password):
            st.session_state.user_type = 'account'
            st.session_state.mode = 'Welcome'
            st.rerun()
