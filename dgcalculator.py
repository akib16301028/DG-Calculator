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
    except Exception as e:
        st.error(f"Error reading sheets: {e}")
        st.stop()

    # Ensure required columns are present
    required_columns = [
        "Rms Station", "Site", "Site Alias", "Zone", "Cluster", "Node",
        "Start Time", "End Time", "Elapsed Time", "Acknowledgement",
        "AcknowledgedTime", "AcknowledgedBy"
    ]

    if not all(col in dg_data.columns for col in required_columns):
        st.error("The DG sheet does not have the required columns.")
        st.stop()

    if not all(col in mains_fail_data.columns for col in required_columns):
        st.error("The Mains Fail sheet does not have the required columns.")
        st.stop()

    # Step 3: Convert Start Time and End Time to datetime and handle errors
    dg_data['Start Time'] = pd.to_datetime(dg_data['Start Time'], errors='coerce')
    dg_data['End Time'] = pd.to_datetime(dg_data['End Time'], errors='coerce')
    mains_fail_data['Start Time'] = pd.to_datetime(mains_fail_data['Start Time'], errors='coerce')
    mains_fail_data['End Time'] = pd.to_datetime(mains_fail_data['End Time'], errors='coerce')

    # Drop rows with invalid or missing Start Time or End Time
    dg_data = dg_data.dropna(subset=['Start Time', 'End Time'])
    mains_fail_data = mains_fail_data.dropna(subset=['Start Time', 'End Time'])

    # Extract the date part
    dg_data['Date'] = dg_data['Start Time'].dt.date
    mains_fail_data['Date'] = mains_fail_data['Start Time'].dt.date

    # Find unique dates
    unique_dates = sorted(set(dg_data['Date']).union(mains_fail_data['Date']))

    # Step 4: Match Data by Date and Analyze Results
    st.header("Matched Data by Date")
    results = []

    for date in unique_dates:
        dg_filtered = dg_data[dg_data['Date'] == date]
        mains_fail_filtered = mains_fail_data[mains_fail_data['Date'] == date]

        if not dg_filtered.empty and not mains_fail_filtered.empty:
            # Find common Site Alias and corresponding Zone, Cluster, and Start Time
            common_sites = pd.merge(
                dg_filtered, mains_fail_filtered,
                on=['Site Alias', 'Zone', 'Cluster'],
                suffixes=('_DG', '_MainsFail')
            )

            if not common_sites.empty:
                # Calculate the time difference
                common_sites['Difference'] = (common_sites['Start Time_DG'] - common_sites['Start Time_MainsFail']).dt.total_seconds() / 60.0

                # Filter for rows where Start Time_DG is 30 or more minutes before Start Time_MainsFail
                common_sites = common_sites.sort_values(by=['Site Alias', 'Start Time_DG'])

                # Group by Site Alias to find the latest occurrence
                latest_occurrences = common_sites.groupby('Site Alias').last().reset_index()

                # Add a column for the number of occurrences
                occurrences = common_sites.groupby('Site Alias').size().reset_index(name='Occurrences')
                latest_occurrences = latest_occurrences.merge(occurrences, on='Site Alias')

                # Add a column for the total time difference of all occurrences
                total_diff = common_sites[common_sites['Difference'] <= -30].groupby('Site Alias')['Difference'].sum().reset_index(name='Total Difference (Minutes)')
                latest_occurrences = latest_occurrences.merge(total_diff, on='Site Alias', how='left')
                latest_occurrences['Total Difference (Minutes)'] = latest_occurrences['Total Difference (Minutes)'].fillna(0).apply(lambda x: f"{int(abs(x))} minutes")

                # Filter the latest occurrences for the 30-minute condition
                filtered_sites = latest_occurrences[latest_occurrences['Difference'] <= -30]

                if not filtered_sites.empty:
                    st.subheader(f"Filtered Data for Date: {date}")
                    filtered_sites['Difference (Minutes)'] = filtered_sites['Difference'].apply(lambda x: f"{int(abs(x))} minutes")
                    st.dataframe(filtered_sites[[
                        'Site Alias', 'Zone', 'Cluster',
                        'Start Time_DG', 'Start Time_MainsFail', 'Difference (Minutes)',
                        'Occurrences', 'Total Difference (Minutes)'
                    ]])

                    # Store results for download
                    results.append((date, filtered_sites))

    # Step 5: Provide Download Option
    if results:
        with pd.ExcelWriter("filtered_data.xlsx") as writer:
            for date, result in results:
                result.to_excel(writer, sheet_name=str(date), index=False)

        with open("filtered_data.xlsx", "rb") as file:
            st.download_button(
                label="Download Filtered Data",
                data=file,
                file_name="filtered_data.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    else:
        st.info("No Site Alias found with the specified time difference condition.")
