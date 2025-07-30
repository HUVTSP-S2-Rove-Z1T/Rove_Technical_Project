import streamlit as st
import pandas as pd

df = pd.read_csv("VPM_Research.csv")

# -----------------------------
# Streamlit App UI
# -----------------------------
st.set_page_config(page_title="Redemption Optimizer", layout="centered")
st.title(" Rove Redemption Optimizer")
st.markdown("**Compare flights, hotels, and gift cards to find the best use of your airline miles.**")

user_airline = st.selectbox("Select an airline", df["airline"].unique())
user_miles = st.number_input("How many miles do you have?", min_value=0, value=60000)

# -----------------------------
# Filter to selected airline
# -----------------------------
filtered = df[df["airline"] == user_airline].copy()

# Calculate net value and value per mile
filtered["net_value"] = filtered["cash_value"] - filtered["taxes_fees"]
filtered["adjusted_value"] = filtered["net_value"] - filtered["miles_fee"]
filtered["vpm"] = filtered["net_value"] / filtered["miles_required"]  # in dollars
filtered["vpm_cents"] = filtered["vpm"] * 100  # in cents

filtered = filtered.sort_values(by="vpm", ascending=False, ignore_index=True)

# Rating thresholds by redemption type
def rate_redemption(row):
    if row["type"] == "Flight":
        if row["vpm"] > 0.013:
            return "Excellent"
        elif row["vpm"] > 0.011:
            return "Good"
        else:
            return "Poor"
    elif row["type"] == "Hotel":
        return "Good" if row["vpm"] >= 0.010 else "Poor"
    elif row["type"] == "Gift Card":
        return "Fair" if row["vpm"] >= 0.010 else "Poor"

filtered["rating"] = filtered.apply(rate_redemption, axis=1)
filtered["can_afford"] = filtered["miles_required"] <= user_miles

# -----------------------------
# Show table of results
# -----------------------------
st.subheader(f"Redemption Options with {user_airline} Miles")
st.dataframe(
    filtered[["type", "name", "miles_required", "miles_fee", "cash_value", "taxes_fees", "vpm_cents", "rating", "can_afford"]]
    .rename(columns={"vpm_cents": "Value per Mile (¢)"})
    .style.format({"miles_fee": "${:.2f}", "cash_value": "${:.2f}", "taxes_fees": "${:.2f}", "Value per Mile (¢)": "{:.2f}"})
)

# -----------------------------
# Best recommendation
# -----------------------------
affordable = filtered[filtered["can_afford"] == True]

if affordable.empty:
    st.warning("You don't have enough miles for any available redemption options.")
else:
    best = affordable.sort_values(by="vpm", ascending=False).iloc[0]
    st.success(f"✅ **Best Use:** {best['type']} — {best['vpm_cents']:.2f}¢ per mile ({best['rating']})")

# -----------------------------
# Notes
# -----------------------------
with st.expander("ℹ️ How this works"):
    st.markdown("""
    - **Value per Mile (VPM)** is calculated as:  
      `(Cash Price - Taxes & Fees) / Miles Required`
    - This reflects how much real dollar value you're getting per point.
    - We compare flights, hotels, and gift cards to recommend the best use.
    - Thresholds differ by category (flights usually give better value).
    """)
