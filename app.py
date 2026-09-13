import streamlit as st
import pandas as pd
import json
from pathlib import Path

st.set_page_config(
    page_title="Lead Follow-Up Agent",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 Lead Follow-Up Agent")
st.caption("AI-powered lead qualification and personalized follow-up")

# --------------------------------------------------
# Load leads
# --------------------------------------------------

try:
    leads = pd.read_csv("leads.csv")
except FileNotFoundError:
    st.error("leads.csv not found.")
    st.stop()


# --------------------------------------------------
# Load AI reviews
# --------------------------------------------------

reviews = {}

reviews_file = Path("lead_reviews.json")

if reviews_file.exists():
    try:
        with open(reviews_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict):
            if "reviews" in data:
                data = data["reviews"]

            if isinstance(data, list):
                reviews = {
                    str(item.get("lead_id")): item
                    for item in data
                    if item.get("lead_id")
                }
            else:
                reviews = data

        elif isinstance(data, list):
            reviews = {
                str(item.get("lead_id")): item
                for item in data
                if item.get("lead_id")
            }

    except Exception as e:
        st.warning(f"Could not read lead_reviews.json: {e}")


# --------------------------------------------------
# Add AI information
# --------------------------------------------------

leads["score"] = leads["lead_id"].map(
    lambda x: reviews.get(str(x), {}).get("lead_score")
)

leads["priority"] = leads["lead_id"].map(
    lambda x: reviews.get(str(x), {}).get("priority")
)


# --------------------------------------------------
# Dashboard metrics
# --------------------------------------------------

total_leads = len(leads)

high_count = (leads["priority"] == "HIGH").sum()
medium_count = (leads["priority"] == "MEDIUM").sum()
low_count = (leads["priority"] == "LOW").sum()

col1, col2, col3, col4 = st.columns(4)

col1.metric("Total Leads", total_leads)
col2.metric("🔥 High Priority", high_count)
col3.metric("🟡 Medium Priority", medium_count)
col4.metric("🟢 Low Priority", low_count)

st.divider()


# --------------------------------------------------
# Lead List
# --------------------------------------------------

st.subheader("📋 Lead List")

display_columns = [
    "lead_id",
    "name",
    "company",
    "score",
    "priority",
    "email"
]

st.dataframe(
    leads[display_columns],
    use_container_width=True,
    hide_index=True
)


# --------------------------------------------------
# Lead Selection
# --------------------------------------------------

st.divider()

st.subheader("🔍 Lead Details")

selected_id = st.selectbox(
    "Select a lead",
    leads["lead_id"].tolist()
)

selected_lead = leads[
    leads["lead_id"] == selected_id
].iloc[0]

review = reviews.get(str(selected_id), {})


# --------------------------------------------------
# Lead Information
# --------------------------------------------------

col1, col2, col3 = st.columns(3)

with col1:
    st.write("**Name**")
    st.write(selected_lead["name"])

with col2:
    st.write("**Company**")
    st.write(selected_lead["company"])

with col3:
    st.write("**Email**")
    st.write(selected_lead["email"])


st.write("**Original Lead Message**")
st.info(selected_lead["message"])


# --------------------------------------------------
# AI Analysis
# --------------------------------------------------

st.subheader("🧠 AI Analysis")

col1, col2 = st.columns(2)

with col1:
    st.write("**Lead Score**")
    st.metric("Score", review.get("lead_score", "N/A"))

    st.write("**Priority**")
    st.write(review.get("priority", "N/A"))

    st.write("**Customer Problem**")
    st.write(review.get("customer_problem", "N/A"))

    st.write("**Likely Requirement**")
    st.write(review.get("likely_requirement", "N/A"))

with col2:
    st.write("**Relevant Service**")
    st.write(review.get("relevant_service", "N/A"))

    st.write("**Explicit Information**")
    st.write(review.get("explicit_information", "N/A"))

    st.write("**Missing Information**")
    st.write(review.get("missing_information", "N/A"))

    st.write("**Recommended Action**")
    st.write(review.get("recommended_action", "N/A"))


# --------------------------------------------------
# Risk Flags
# --------------------------------------------------

st.subheader("⚠️ Risk Flags")

risk_flags = review.get("risk_flags", [])

if isinstance(risk_flags, list) and risk_flags:
    for risk in risk_flags:
        st.warning(risk)
else:
    st.success("No significant risk flags identified.")


# --------------------------------------------------
# Generated Email
# --------------------------------------------------

st.subheader("✉️ AI-Generated Follow-Up")

st.write("**Subject:**")
st.code(
    review.get("email_subject", "No email generated"),
    language=None
)

st.write("**Email Body:**")

email_body = review.get(
    "email_body",
    "No email generated."
)

st.text_area(
    "Draft Preview",
    email_body,
    height=300,
    disabled=True
)