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

    # Step 4: Match Data by Date and Display Results
    st.header("Matched Data by Date")
    unique_dates = sorted(set(dg_data['Date']).union(mains_fail_data['Date']))
    results = []

    for date in unique_dates:
        dg_filtered = dg_data[dg_data['Date'] == date]
        mains_fail_filtered = mains_fail_data[mains_fail_data['Date'] == date]

        if not dg_filtered.empty and not mains_fail_filtered.empty:
            # Initialize the matched data list
            matched_data = []

            # Group by Site Alias
            for site_alias, dg_group in dg_filtered.groupby('Site Alias'):
                mains_group = mains_fail_filtered[mains_fail_filtered['Site Alias'] == site_alias]

                if not mains_group.empty:
                    # Sort both DG and Mains Fail data by Start Time
                    dg_group = dg_group.sort_values('Start Time')
                    mains_group = mains_group.sort_values('Start Time')

                    # Sequentially match DG and Mains Fail events
                    for _, dg_row in dg_group.iterrows():
                        # Find the first Mains Fail Start Time after the current DG Start Time
                        matched_mains_row = mains_group[mains_group['Start Time'] > dg_row['Start Time']].iloc[0:1]

                        if not matched_mains_row.empty:
                            mains_start_time = matched_mains_row['Start Time'].values[0]
                            time_difference = (dg_row['Start Time'] - mains_start_time).total_seconds() / 60.0

                            # Keep only if time difference is 30 minutes or more
                            if time_difference <= -30:
                                matched_data.append({
                                    'Site Alias': site_alias,
                                    'Zone': dg_row['Zone'],
                                    'Cluster': dg_row['Cluster'],
                                    'Start Time_DG': dg_row['Start Time'],
                                    'Start Time_MainsFail': mains_start_time,
                                    'Difference (Minutes)': int(abs(time_difference))
                                })

                                # Remove matched Mains Fail entry to ensure one-to-one mapping
                                mains_group = mains_group[mains_group['Start Time'] != mains_start_time]

            if matched_data:
                matched_df = pd.DataFrame(matched_data)
                matched_df['Occurrence Count'] = matched_df.groupby('Site Alias')['Site Alias'].transform('size')
                matched_df['Total Time (Minutes)'] = matched_df.groupby('Site Alias')['Difference (Minutes)'].transform('sum')

                st.subheader(f"Matched Data for Date: {date}")
                st.dataframe(matched_df)

                # Store results for download
                results.append((date, matched_df))

   # Step 5: Provide Download Option
if results:
    # Combine all results into a single DataFrame
    combined_data = pd.concat([result for _, result in results], ignore_index=True)

    with pd.ExcelWriter("filtered_data.xlsx") as writer:
        # Write the combined data to a single sheet
        combined_data.to_excel(writer, sheet_name="All Dates", index=False)
        
        # Write each date's data to separate sheets
        for date, result in results:
            result.to_excel(writer, sheet_name=str(date), index=False)

    # Allow the user to download the file
    with open("filtered_data.xlsx", "rb") as file:
        st.download_button(
            label="Download Filtered Data",
            data=file,
            file_name="filtered_data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
else:
    st.info("No Site Alias found with the specified time difference condition.")
