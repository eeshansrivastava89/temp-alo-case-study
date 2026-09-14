import streamlit as st

st.set_page_config(page_title="AI Business Analyst", page_icon="📊", layout="wide")

navigation = st.navigation(
    [
        st.Page("pages/1_AI_Business_Analyst.py", title="AI Business Analyst", icon="💬", default=True),
        st.Page("pages/2_Executive_Dashboard.py", title="Executive Dashboard", icon="📈"),
    ]
)
navigation.run()
