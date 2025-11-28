#!/bin/bash
# Run Streamlit app

cd "$(dirname "$0")"
streamlit run src/streamlit_app/app.py

