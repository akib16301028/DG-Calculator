import pandas as pd
import streamlit as st

# Streamlit app
st.title("Excel File Processor")

# File upload
uploaded_file = st.file_uploader("Upload your Excel file", type=["xlsx"])

if uploaded_file:
    # Load the Excel file
    excel_data = pd.ExcelFile(uploaded_file)
    st.write(f"### Sheets found: {excel_data.sheet_names}")

    processed_sheets = {}
    combined_data = []

    for sheet_name in excel_data.sheet_names:
        # Read each sheet into a DataFrame
        df = excel_data.parse(sheet_name)
        
        # Ensure required columns exist
        required_columns = ["Site Alias", "Zone", "Cluster", "Start Time_DG", "Start Time_MainsFail", "Time Difference (minutes)", "Before/After"]
        if not all(col in df.columns for col in required_columns):
            st.error(f"Sheet '{sheet_name}' does not contain the required columns.")
            continue

        # Remove duplicates, keeping the row with the lowest Time Difference (minutes)
        df_processed = df.sort_values(by="Time Difference (minutes)").drop_duplicates(subset="Site Alias", keep="first")

        # Store the processed DataFrame
        processed_sheets[sheet_name] = df_processed

        # Add processed data to combined list
        combined_data.append(df_processed)

        # Display the processed DataFrame for the sheet
        st.write(f"### Processed Data for Sheet: {sheet_name}")
        st.dataframe(df_processed)

    # Create a combined sheet with all data
    if combined_data:
        combined_df = pd.concat(combined_data, ignore_index=True)
        st.write("### Combined Data Across All Sheets")
        st.dataframe(combined_df)

        # Add the combined sheet to the processed Excel file
        output_file = pd.ExcelWriter("processed_data.xlsx", engine='openpyxl')
        for sheet_name, processed_df in processed_sheets.items():
            processed_df.to_excel(output_file, index=False, sheet_name=sheet_name)
        combined_df.to_excel(output_file, index=False, sheet_name="Combined Data")
        output_file.close()

        with open("processed_data.xlsx", "rb") as f:
            st.download_button(
                label="Download Processed Excel File",
                data=f,
                file_name="processed_data.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
