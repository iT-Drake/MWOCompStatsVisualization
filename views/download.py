import streamlit as st

from utility.database import read_comp_data
from utility.blocks import filters_block
from utility.methods import unique

def header():
    st.header('Dowload match data in CSV format')

def filters():
    df = read_comp_data()
    options = {'Tournament': None, 'Division': None, 'TeamName': 'Team', 'Map': None}
    df, options = filters_block(df, options)

    return df

def generate_button(df):
    button_pressed = st.button('Generate file with all data', use_container_width=True)
    if button_pressed:
        download_button(df)

    button_pressed = st.button('Generate file with only match IDs', use_container_width=True)
    if button_pressed:
        df = unique(df, 'MatchID')
        download_button(df)

def download_button(df):
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download data as CSV",
        data=csv,
        file_name="data_dump.csv",
        mime='text/csv',
        type='primary',
        use_container_width=True
    )

header()
df = filters()
generate_button(df)
