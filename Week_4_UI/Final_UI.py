import streamlit as st
from datetime import date
import sqlite3 as sql
import bcrypt as bc
from synthetic_redemption import load_redemptions, find_synthetic_routes

# Constants
AIRLINES_WITH_VPM_DATA = ['United', 'Delta', 'Emirates']
SEARCH_FILTERS = ['Maximize Value', 'Free Wifi', 'Direct Flights Only']
USER_DB = "user_auth.db"
REDEMPTIONS_FILE = "Week_4_UI/redemptions.json"
SEARCHES_SHOWN = 10

# Initialize session state flags
if 'is_logged_in' not in st.session_state:
    st.session_state.is_logged_in = False
if 'mode' not in st.session_state:
    st.session_state.mode = 'Welcome'
if 'user_type' not in st.session_state:
    st.session_state.user_type = 'guest'
if 'saved_miles_dict' not in st.session_state:
    st.session_state.saved_miles_dict = {airline: 0 for airline in AIRLINES_WITH_VPM_DATA}
if 'username' not in st.session_state:
    st.session_state.username = None
if 'search_page' not in st.session_state:
    st.session_state.search_page = 1

# Create user table if not exists, and add total_savings column if missing
with sql.connect(USER_DB) as conn:
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS users (
                    username TEXT UNIQUE, 
                    password TEXT
                )''')
    conn.commit()

    cur.execute("PRAGMA table_info(users)")
    columns = [info[1] for info in cur.fetchall()]
    if 'total_savings' not in columns:
        cur.execute("ALTER TABLE users ADD COLUMN total_savings REAL DEFAULT 0")
        conn.commit()

# Auth functions
def sign_up(username, password):
    if not username or not password:
        st.error('Please enter both username and password.')
        return False
    if len(password) < 8:
        st.error('Password must be at least 8 characters long.')
        return False
    if len(username) < 3:
        st.error('Username must be at least 3 characters long.')
        return False
    with sql.connect(USER_DB) as conn:
        cur = conn.cursor()
        if cur.execute('SELECT username FROM users WHERE username = ?', (username,)).fetchone():
            st.error('Username already exists.')
            return False
        hashed = bc.hashpw(password.encode('utf8'), bc.gensalt())
        cur.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed))
        conn.commit()
    st.session_state.is_logged_in = True
    st.session_state.user_type = 'account'
    st.session_state.username = username
    return True

def log_in(username, password):
    if not username or not password:
        st.error('Please enter both username and password.')
        return False
    with sql.connect(USER_DB) as conn:
        cur = conn.cursor()
        user = cur.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        if user and bc.checkpw(password.encode('utf8'), user[1]):
            st.session_state.is_logged_in = True
            st.session_state.user_type = 'account'
            st.session_state.username = username
            return True
        else:
            st.error('Invalid username or password.')
            return False

def get_user_savings(username):
    if not username:
        return 0
    with sql.connect(USER_DB) as conn:
        cur = conn.cursor()
        result = cur.execute('SELECT total_savings FROM users WHERE username = ?', (username,)).fetchone()
        if result:
            return result[0]
        return 0

def update_user_savings(username, added_savings):
    if not username:
        return
    with sql.connect(USER_DB) as conn:
        cur = conn.cursor()
        current = get_user_savings(username)
        new_total = current + added_savings
        cur.execute('UPDATE users SET total_savings = ? WHERE username = ?', (new_total, username))
        conn.commit()

def change_mode_creator(new_mode):
    def change_mode():
        st.session_state.mode = new_mode
    return change_mode

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


# Sidebar navigation
st.sidebar.header('ROVE :small[:blue[Redemptions]]')
st.sidebar.button('Welcome', on_click=change_mode_creator('Welcome'))
st.sidebar.button('Find Flights', on_click=change_mode_creator('Find Flights'))
st.sidebar.button('Profile', on_click=change_mode_creator('Profile'))
if st.session_state.user_type == 'guest':
    st.sidebar.button('Log In', on_click=change_mode_creator('Log In'))
else:
    st.sidebar.button('Log Out', on_click=change_mode_creator('Log Out'))

mode = st.session_state.mode

if mode == 'Welcome':
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
    st.markdown("#### 👉 Get started by creating an account by selecting ***Log In*** and finding your redemptions by selecting ***Find Flights*** in the sidebar.")

elif mode == 'Find Flights':
    if not st.session_state.is_logged_in:
        st.title("Please log in to find flights.")
    else:
        st.title('Find Flights Now')
        st.header('Booking info:')

        roundtrip = st.checkbox('Roundtrip?', value=True)
        booking_cols = st.columns([1,1,1.5,1.5,1,2])
        origin = booking_cols[0].text_input('From', max_chars=4)
        destination = booking_cols[1].text_input('To', max_chars=4)
        departure_date = booking_cols[2].date_input('Departure date', min_value=date.today())
        if roundtrip:
            return_date = booking_cols[3].date_input('Return date', min_value=date.today())
        else:
            booking_cols[3].markdown(':small[Return date]')
            booking_cols[3].markdown(':x:')
        passengers = booking_cols[4].number_input('Passengers', min_value=1, max_value=100)
        cabin_class = booking_cols[5].selectbox('Cabin Class', ['Economy', 'Premium Economy', 'Business', 'First Class'])

        st.subheader('Use Miles')
        all_airlines = st.multiselect('Airlines You Have Rewards With', AIRLINES_WITH_VPM_DATA)
        if all_airlines:
            mile_cols = st.columns(len(all_airlines))
            for i, airline in enumerate(all_airlines):
                miles = mile_cols[i].number_input(f'{airline} miles', min_value=0)
                st.session_state.saved_miles_dict[airline] = miles

        st.subheader('Filters')
        st.multiselect('Search filters', options=SEARCH_FILTERS)

        search_clicked = st.button('Search!')

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
                    if st.button("Select", key=f"select_{idx}"):
                        # Update savings when user selects this option
                        savings_val = float(option.get('total_cash', '0').replace('$',''))  # assuming total_cash is string like '$123'
                        update_user_savings(st.session_state.username, savings_val)
                        st.success(f"Selected route saved! You saved ${savings_val:.2f} on this redemption.")
                st.markdown("---")

        if search_clicked:
            # We quickly save the flight to the search history
            add_search_to_history(st.session_state.username, roundtrip, origin, destination, departure_date, return_date, passengers, cabin_class)

            if not origin or not destination:
                st.error("Please enter both origin and destination airport codes.")
            else:
                try:
                    redemptions_data = load_redemptions(REDEMPTIONS_FILE)
                    synthetic_results = find_synthetic_routes(origin.upper(), destination.upper(), redemptions_data)
                    if synthetic_results:
                        st.subheader("🔎 Synthetic Redemption Options (1-stop routes):")
                        for i, option in enumerate(synthetic_results):
                            show_synthetic_card(option, i)
                    else:
                        st.info("No synthetic routes found for your search.")
                except FileNotFoundError:
                    st.error(f"Redemptions data file '{REDEMPTIONS_FILE}' not found.")

elif mode == 'Profile':
    if not st.session_state.is_logged_in:
        st.title("Please log in to view your profile.")
    else:
        st.title('Profile')
        st.markdown(f"### Welcome, **{st.session_state.username}**!")
        total_saved = get_user_savings(st.session_state.username)
        st.markdown(f"💰 **Total savings from using Rove:** ${total_saved:.2f}")

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

elif mode == 'Log Out':
    st.session_state.is_logged_in = False
    st.session_state.user_type = 'guest'
    st.session_state.username = None
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
