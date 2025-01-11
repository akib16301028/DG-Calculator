import streamlit as st
import pandas as pd

# Streamlit app
def main():
    st.title("Process Site Alias Data")

    # File upload
    uploaded_file = st.file_uploader("Upload your file", type=["csv", "xlsx"])

    if uploaded_file:
        # Check if the uploaded file is an Excel file with multiple sheets
        if uploaded_file.name.endswith(".xlsx"):
            # Read all sheets into a dictionary of DataFrames
            sheet_data = pd.read_excel(uploaded_file, sheet_name=None)
            processed_sheets = {}

            for sheet_name, df in sheet_data.items():
                st.write(f"### Original Data from Sheet: {sheet_name}")
                st.write(df)

                # Ensure required columns exist
                required_columns = [
                    "Site Alias",
                    "Zone",
                    "Cluster",
                    "Start Time_DG",
                    "Start Time_MainsFail",
                    "Difference (Minutes)",
                    "Occurrence Count",
                    "Total Time (Minutes)",
                ]

                if not all(col in df.columns for col in required_columns):
                    st.error(f"The sheet '{sheet_name}' does not contain the required columns.")
                    continue

                # Convert datetime columns to proper datetime format
                df["Start Time_DG"] = pd.to_datetime(df["Start Time_DG"], errors='coerce')
                df["Start Time_MainsFail"] = pd.to_datetime(df["Start Time_MainsFail"], errors='coerce')

                # Sort by latest 'Start Time_DG' and 'Start Time_MainsFail'
                df = df.sort_values(by=["Site Alias", "Start Time_DG", "Start Time_MainsFail"], ascending=[True, False, False])

                # Drop duplicates, keeping the first (latest) occurrence
                df_unique = df.drop_duplicates(subset=["Site Alias"], keep="first")

                st.write(f"### Processed Data from Sheet: {sheet_name}")
                st.write(df_unique)

                # Save processed data for this sheet
                processed_sheets[sheet_name] = df_unique

            # Combine all processed sheets into a single DataFrame
            combined_data = pd.concat(processed_sheets.values(), ignore_index=True)

            # Save processed sheets and combined data into a single Excel file
            if processed_sheets:
                output_file = pd.ExcelWriter("processed_data.xlsx", engine='xlsxwriter')
                for sheet_name, df_unique in processed_sheets.items():
                    df_unique.to_excel(output_file, sheet_name=sheet_name, index=False)
                combined_data.to_excel(output_file, sheet_name="Combined Data", index=False)
                output_file.close()  # Use close() to save and finalize the file

                with open("processed_data.xlsx", "rb") as f:
                    st.download_button(
                        label="Download Processed Data as Excel",
                        data=f,
                        file_name="processed_data.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )

        else:
            # Handle single-sheet files (CSV or single-sheet Excel)
            if uploaded_file.name.endswith(".csv"):
                df = pd.read_csv(uploaded_file)
            elif uploaded_file.name.endswith(".xlsx"):
                df = pd.read_excel(uploaded_file)

            st.write("### Original Data:")
            st.write(df)

            # Ensure required columns exist
            required_columns = [
                "Site Alias",
                "Zone",
                "Cluster",
                "Start Time_DG",
                "Start Time_MainsFail",
                "Difference (Minutes)",
                "Occurrence Count",
                "Total Time (Minutes)",
            ]

            if not all(col in df.columns for col in required_columns):
                st.error("The uploaded file does not contain the required columns.")
                return

            # Convert datetime columns to proper datetime format
            df["Start Time_DG"] = pd.to_datetime(df["Start Time_DG"], errors='coerce')
            df["Start Time_MainsFail"] = pd.to_datetime(df["Start Time_MainsFail"], errors='coerce')

            # Sort by latest 'Start Time_DG' and 'Start Time_MainsFail'
            df = df.sort_values(by=["Site Alias", "Start Time_DG", "Start Time_MainsFail"], ascending=[True, False, False])

            # Drop duplicates, keeping the first (latest) occurrence
            df_unique = df.drop_duplicates(subset=["Site Alias"], keep="first")

            st.write("### Processed Data (Unique Site Alias):")
            st.write(df_unique)

            # Option to download processed data
            csv = df_unique.to_csv(index=False)
            st.download_button(
                label="Download Processed Data as CSV",
                data=csv,
                file_name="processed_data.csv",
                mime="text/csv",
            )

if __name__ == "__main__":
    main()
