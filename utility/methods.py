import streamlit as st

def error(message, header='Error'):
    st.error(header, icon=':material/error:')
    st.markdown(f'```\n{message}\n```')

def convert_to_int(value):
    formatted_value = value.replace(',', '').strip()
    try:
        return int(formatted_value)
    except ValueError as e:
        error(f'Incorrect match id: {value}')
        return ''

def safe_division(dividend, divisor):
    return dividend / divisor if divisor != 0 else dividend

# General pandas dataframe operations

def nunique(df, column):
    if not column:
        raise Exception(f'Provide a valid column name')
    
    return df[column].nunique()

def unique(df, column, ascending_sort=True):
    if not column:
        raise Exception(f'Provide a valid column name')
    
    return df[column].drop_duplicates().sort_values(ascending=ascending_sort)

def filter_dataframe(df, key, value):
    result = df
    if not key:
        raise Exception(f'Key should be specified to filter data')
    elif not value:
        raise Exception(f'Provide value to filter data')
    elif isinstance(value, list):
        result = result[result[key].isin(value)]
    else:
        result = result[result[key] == value]

    return result
