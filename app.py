# HACK: Completely prevent chromadb import by removing it from sys.modules
import sys
import types

# Create a mock chromadb package with all the required components
mock_chromadb = types.ModuleType("chromadb")

# Create a mock class for Chroma components
class MockDocuments:
    def __init__(self, *args, **kwargs):
        pass

class MockClientAPI:
    def __init__(self, *args, **kwargs):
        pass

class MockSettings:
    def __init__(self, *args, **kwargs):
        pass

# Create mock classes for other Chroma components
mock_chromadb.Documents = MockDocuments  # Mock Documents class
mock_chromadb.EmbeddingFunction = lambda *args, **kwargs: None  # Mock EmbeddingFunction as simple lambda
mock_chromadb.Embeddings = lambda *args, **kwargs: None  # Mock Embeddings as simple lambda
mock_chromadb.Collection = lambda *args, **kwargs: None  # Mock Collection

# Mock chromadb.errors (which is also being imported)
mock_chromadb.errors = types.ModuleType("chromadb.errors")
mock_chromadb.errors.ChromaError = lambda *args, **kwargs: None  # Mock ChromaError

# Mock chromadb.config (the source of the current error)
mock_chromadb.config = types.ModuleType("chromadb.config")
mock_chromadb.config.Settings = MockSettings  # Use MockSettings instead of None

# Mock the ClientAPI and other parts of the code that might use `| None`
mock_chromadb.api = types.ModuleType("chromadb.api")
mock_chromadb.api.ClientAPI = MockClientAPI  # Replace with MockClientAPI class
mock_chromadb.api.types = types.ModuleType("chromadb.api.types")
mock_chromadb.api.types.OneOrMany = lambda *args, **kwargs: None  # Mock OneOrMany
mock_chromadb.api.types.validate_embedding_function = lambda *args, **kwargs: None  # Mock validate_embedding_function

# Add the mock module to sys.modules to ensure CrewAI uses this mock instead of the real Chroma
sys.modules["chromadb"] = mock_chromadb
sys.modules["chromadb.api"] = mock_chromadb.api
sys.modules["chromadb.api.types"] = mock_chromadb.api.types
sys.modules["chromadb.errors"] = mock_chromadb.errors
sys.modules["chromadb.config"] = mock_chromadb.config

# Now import CrewAI after stubbing chromadb
import crewai


import streamlit as st
import pysqlite3 as sqlite3
from collector import CountryLegalDataCollector
from aggregator import LegalDataAggregator
from evaluator import DynamicRiskEvaluationAgent
from reporter import ReportGenerator
from crewai import Task, Crew, Process
import json

# Apply background and ensure text stays visible on top

import base64
import streamlit as st
from collector import CountryLegalDataCollector
# … rest of your imports …


def add_bg_and_content_container_style(image_file: str):
    with open(image_file, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    st.markdown(
        f"""
        <style>
        /* full‑page prison bars background */
        .stApp {{
            background-image: url("data:image/png;base64,{b64}");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}

        /* white, semi‑opaque panel behind all content */
        .stApp .block-container {{
            background-color: rgba(255, 255, 255, 0.85);
            padding: 2rem;
            border-radius: 0.75rem;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

# call before any other Streamlit UI code
add_bg_and_content_container_style("background.png")

#st.set_page_config(page_title="Tweet Legal Risk Analyzer", layout="centered")
st.title("Will You Go to Jail for This Tweet?")
st.markdown("🛡️ Enter your tweet and select a country to get a legal risk score.")

# User inputs
country = st.text_input("Country (e.g., US, UK, Germany):", value="US")
tweet = st.text_area("Enter your tweet here:")

if st.button("Analyze Tweet"):
    if not tweet.strip():
        st.error("Please enter a tweet to analyze.")
    else:
        with st.spinner("Analyzing legal risk..."):
            # Task 1: Collect legal data
            collect_task = Task(
                name="collect_legal_data",
                agent=CountryLegalDataCollector(),
                description="Retrieve raw legal guidelines for the chosen country",
                params={"country": country},
                expected_output="dict mapping category names to {'text':…, 'url':…}"
            )

            # Task 2: Aggregate and structure legal data
            aggregate_task = Task(
                name="aggregate_legal_data",
                agent=LegalDataAggregator(),
                description="Structure and attach citations to the raw legal data",
                params={"legal_data": "{collect_legal_data}"},
                expected_output="dict mapping category names to {'text':…, 'citation':…}"
            )

            # Task 3: Evaluate the tweet content against legal data
            evaluate_task = Task(
                name="evaluate_tweet",
                agent=DynamicRiskEvaluationAgent(),
                description="Compute per-category and overall risk scores for the tweet",
                params={
                    "tweet": tweet,
                    "legal_data": "{aggregate_legal_data}"
                },
                expected_output="dict with 'per_category':{…}, 'overall_risk': float"
            )

            # Task 4: Generate the final report
            report_task = Task(
                name="generate_report",
                agent=ReportGenerator(),
                description="Format the evaluation into a human‑readable summary and details",
                params={"evaluation": "{evaluate_tweet}"},
                expected_output="dict with 'summary', 'details', and 'full_report' strings"
            )

            # Orchestrate the crew sequentially
            crew = Crew(
                name="TweetLegalRiskCrew",
                tasks=[collect_task, aggregate_task, evaluate_task, report_task],
                process=Process.sequential,
                verbose=False
            )

            # Run the crew
            result = crew.kickoff()

            # === Display ===

            # After kickoff():
            raw = result.raw
            try:
                output = json.loads(raw)
            except json.JSONDecodeError:
                st.error("Failed to parse crew output as JSON:")
                st.code(raw)
                st.stop()

            # Now output is a dict
            st.subheader("Overall Risk")
            st.markdown(output.get("summary", "N/A"))

            st.subheader("Category Breakdown")
            details = output.get("details", {})
            for category, info in details.items():
                with st.expander(category):
                    st.markdown(f"**Risk Score:** {info.get('risk_score', 'N/A')}%")
                    st.markdown(f"**Citation:** {info.get('citation', 'N/A')}")
                    st.write(info.get("text", ""))

            # etc…

