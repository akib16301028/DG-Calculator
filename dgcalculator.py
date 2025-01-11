import streamlit as st
import pandas as pd

# Streamlit app
def main():
    st.title("Process Site Alias Data")

    # File upload
    uploaded_file = st.file_uploader("Upload your file", type=["csv", "xlsx"])

    if uploaded_file:
        # Read file based on extension
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
