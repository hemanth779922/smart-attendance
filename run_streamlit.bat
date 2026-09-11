@echo off
echo ======================================================================
echo Starting Smart Attendance System 2.0 - Streamlit Web Application...
echo ======================================================================
streamlit run streamlit_app.py --server.headless true --browser.gatherUsageStats false
pause
