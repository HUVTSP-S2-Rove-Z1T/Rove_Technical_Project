import streamlit as st
from datetime import date
import sqlite3 as sql
import bcrypt as bc
from synthetic_redemption import load_redemptions, find_synthetic_routes

# Constants
AIRLINES_WITH_VPM_DATA = ['United', 'Delta', 'Emirates']
SEARCH_FILTERS = ['Maximize Value', 'Free Wifi', 'Direct Flights Only']
USER_DB = "user_auth.db"
REDEMPTIONS_FILE = "redemptions.json"

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

elif mode == 'Log In':
    st.title('Log In')
    username = st.text_input('Username', key='login_user')
    password = st.text_input('Password', type='password', key='login_pass')
    if st.button("Don't have an account?", key='goto_signup'):
        st.session_state.mode = 'Sign Up'
        st.experimental_rerun()
    if st.button('Log In', key='login_btn'):
        if log_in(username, password):
            st.session_state.mode = 'Welcome'
            st.experimental_rerun()

elif mode == 'Log Out':
    st.session_state.is_logged_in = False
    st.session_state.user_type = 'guest'
    st.session_state.username = None
    st.session_state.mode = 'Welcome'
    st.experimental_rerun()

elif mode == 'Sign Up':
    st.title('Sign Up')
    username = st.text_input('Username', key='signup_user')
    password = st.text_input('Password', type='password', key='signup_pass')
    if st.button("Already have an account?", key='goto_login'):
        st.session_state.mode = 'Log In'
        st.experimental_rerun()
    if st.button('Sign Up', key='signup_btn'):
        if sign_up(username, password):
            st.session_state.mode = 'Welcome'
            st.experimental_rerun()
