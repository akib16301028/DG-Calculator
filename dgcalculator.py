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
    mains_fail_data['Start Time'] = pd.to_datetime(mains_fail_data['Start Time'], errors='coerce')

    # Drop rows with invalid or missing Start Time
    dg_data = dg_data.dropna(subset=['Start Time'])
    mains_fail_data = mains_fail_data.dropna(subset=['Start Time'])

    # Extract the date part
    dg_data['Date'] = dg_data['Start Time'].dt.date
    mains_fail_data['Date'] = mains_fail_data['Start Time'].dt.date

    # Step 4: Match Data by Site Alias
    st.header("Matched Data")
    matched_data = []

    for site_alias, dg_group in dg_data.groupby('Site Alias'):
        mains_group = mains_fail_data[mains_fail_data['Site Alias'] == site_alias]

        if not mains_group.empty:
            # Sort by Start Time
            dg_group = dg_group.sort_values('Start Time')
            mains_group = mains_group.sort_values('Start Time')

            # Match sequentially
            for _, dg_row in dg_group.iterrows():
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
                            'Difference (Minutes)': abs(int(time_difference))
                        })

                        # Remove matched Mains Fail entry to ensure one-to-one mapping
                        mains_group = mains_group[mains_group['Start Time'] != mains_start_time]

    # Step 5: Process Matched Data
    if matched_data:
        matched_df = pd.DataFrame(matched_data)

        # Aggregate duplicates
        latest_df = matched_df.sort_values('Start Time_DG', ascending=False).drop_duplicates(subset=['Site Alias'], keep='first')
        aggregated_df = matched_df.groupby('Site Alias').agg(
            Occurrence_Count=('Site Alias', 'size'),
            Total_Time=('Difference (Minutes)', 'sum')
        ).reset_index()

        # Merge latest with aggregated data
        final_df = pd.merge(latest_df, aggregated_df, on='Site Alias', how='left')

        # Keep only required columns
        final_df = final_df[[
            'Site Alias', 'Zone', 'Cluster', 'Start Time_DG', 'Start Time_MainsFail',
            'Occurrence_Count', 'Total_Time'
        ]]

        # Display final table
        st.dataframe(final_df)

        # Step 6: Provide Download Option
        with pd.ExcelWriter("filtered_data.xlsx") as writer:
            final_df.to_excel(writer, sheet_name="Matched Data", index=False)

        with open("filtered_data.xlsx", "rb") as file:
            st.download_button(
                label="Download Filtered Data",
                data=file,
                file_name="filtered_data.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    else:
        st.info("No Site Alias found with the specified time difference condition.")
