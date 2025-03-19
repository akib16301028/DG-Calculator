import streamlit as st
import pandas as pd

# Streamlit App
st.title("DG and Mains Fail Data Matcher")

# Step 1: Upload the Excel File
uploaded_file = st.file_uploader("Upload your Excel file", type=["xlsx"])

if uploaded_file:
    # Step 2: Read the Excel file
    try:
        dg_data = pd.read_excel(uploaded_file, sheet_name='DG')
        mains_fail_data = pd.read_excel(uploaded_file, sheet_name='Mains Fail')

        # Trim spaces and normalize column names
        dg_data.columns = dg_data.columns.str.strip()
        mains_fail_data.columns = mains_fail_data.columns.str.strip()

    except Exception as e:
        st.error(f"Error reading sheets: {e}")
        st.stop()

    # Ensure required columns are present
    required_columns = [
        "Rms Station", "Site", "Site Alias", "Zone", "Cluster", "Node",
        "Start Time", "End Time", "Elapsed Time"
    ]

    # Debugging: Show available columns
    st.write("DG Data Columns:", list(dg_data.columns))
    st.write("Mains Fail Data Columns:", list(mains_fail_data.columns))

    if not all(col in dg_data.columns for col in required_columns):
        st.error("The DG sheet does not have the required columns. Please check column names for spaces or typos.")
        st.stop()

    if not all(col in mains_fail_data.columns for col in required_columns):
        st.error("The Mains Fail sheet does not have the required columns. Please check column names for spaces or typos.")
        st.stop()

    # Step 3: Convert Start Time and End Time to datetime and handle errors
    dg_data['Start Time'] = pd.to_datetime(dg_data['Start Time'], format='%d/%m/%Y %H:%M', errors='coerce')
    dg_data['End Time'] = pd.to_datetime(dg_data['End Time'], format='%d/%m/%Y %H:%M', errors='coerce')
    mains_fail_data['Start Time'] = pd.to_datetime(mains_fail_data['Start Time'], format='%d/%m/%Y %H:%M', errors='coerce')
    mains_fail_data['End Time'] = pd.to_datetime(mains_fail_data['End Time'], format='%d/%m/%Y %H:%M', errors='coerce')

    # Drop rows with invalid or missing Start Time or End Time
    dg_data = dg_data.dropna(subset=['Start Time', 'End Time'])
    mains_fail_data = mains_fail_data.dropna(subset=['Start Time', 'End Time'])

    # Extract the date part
    dg_data['Date'] = dg_data['Start Time'].dt.date
    mains_fail_data['Date'] = mains_fail_data['Start Time'].dt.date

    # Sort data by Start Time
    dg_data = dg_data.sort_values(by=['Date', 'Start Time'])
    mains_fail_data = mains_fail_data.sort_values(by=['Date', 'Start Time'])

    # Find unique dates
    unique_dates = sorted(set(dg_data['Date']).union(mains_fail_data['Date']))

    # Split the page into two columns
    col1, col2 = st.columns(2)

    # Display DG data by date in the first column
    with col1:
        st.header("DG Data by Date")
        for date in unique_dates:
            dg_filtered = dg_data[dg_data['Date'] == date]
            if not dg_filtered.empty:
                st.subheader(f"Date: {date}")
                st.dataframe(dg_filtered)

    # Display Mains Fail data by date in the second column
    with col2:
        st.header("Mains Fail Data by Date")
        for date in unique_dates:
            mains_fail_filtered = mains_fail_data[mains_fail_data['Date'] == date]
            if not mains_fail_filtered.empty:
                st.subheader(f"Date: {date}")
                st.dataframe(mains_fail_filtered)

    # Step 4: Match Data by Date and Nearest Start Time Within 2-Hour Window
    st.header("Matched Data by Date and Nearest Time (±2 Hours)")
    results = []

    for date in unique_dates:
        dg_filtered = dg_data[dg_data['Date'] == date]
        mains_fail_filtered = mains_fail_data[mains_fail_data['Date'] == date]

        if not dg_filtered.empty and not mains_fail_filtered.empty:
            matched_entries = []

            for _, dg_row in dg_filtered.iterrows():
                # Filter Mains Fail data within a 2-hour window of DG Start Time
                time_window = mains_fail_filtered[
                    (mains_fail_filtered['Start Time'] >= dg_row['Start Time'] - pd.Timedelta(hours=2)) &
                    (mains_fail_filtered['Start Time'] <= dg_row['Start Time'] + pd.Timedelta(hours=2))
                ]

                for _, mf_row in time_window.iterrows():
                    if dg_row['Site Alias'] == mf_row['Site Alias']:
                        time_difference = (dg_row['Start Time'] - mf_row['Start Time']).total_seconds() / 60  # Time difference in minutes
                        classification = (
                            "DG after MF" if time_difference >= 30 else
                            "High DG" if time_difference <= -30 else
                            "Within 30 mins"
                        )
                        matched_entries.append({
                            'Site Alias': dg_row['Site Alias'],
                            'Zone': dg_row['Zone'],
                            'Cluster': dg_row['Cluster'],
                            'Start Time_DG': dg_row['Start Time'],
                            'Start Time_MainsFail': mf_row['Start Time'],
                            'Time Difference (minutes)': abs(time_difference),
                            'Before/After': classification
                        })

            if matched_entries:
                matched_df = pd.DataFrame(matched_entries)
                st.subheader(f"Matched Data for Date: {date}")
                st.dataframe(matched_df)

                # Store results for download
                results.append((date, matched_df))

    # Step 5: Provide Download Option
    if results:
        with pd.ExcelWriter("matched_data.xlsx") as writer:
            # Save DG and Mains Fail data
            dg_data.to_excel(writer, sheet_name="DG Data", index=False)
            mains_fail_data.to_excel(writer, sheet_name="Mains Fail Data", index=False)

            # Save matched data
            for date, result in results:
                result.to_excel(writer, sheet_name=str(date), index=False)

        with open("matched_data.xlsx", "rb") as file:
            st.download_button(
                label="Download Matched Data",
                data=file,
                file_name="matched_data.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    else:
        st.info("No matches found for any date.")
