import streamlit as st

from utility.methods import filter_dataframe, unique

def filters_block(df, options, multiselect=True, on_change=None):
    size = len(options)
    columns = st.columns(size)
    col_index = 0

    if not size:
        return options
    
    for key, representation in options.items():
        column = columns[col_index]

        with column:
            values = unique(df, key)
            placeholder = representation if representation else key
            if multiselect:
                selected_values = st.multiselect('Select value', values, placeholder=placeholder, label_visibility='hidden', on_change=on_change)
            else:
                selected_values = st.selectbox('Select value', values, index=None, placeholder=placeholder, label_visibility='hidden', on_change=on_change)

            if selected_values:
                df = filter_dataframe(df, key, selected_values)
                options[key] = selected_values
            else:
                options[key] = None

        col_index += 1

    return df, options

def metrics_block(metrics, columns = None):
    if not metrics:
        return
    
    if columns == None:
        columns = len(metrics)

    collection = st.columns(columns)
    index = 0
    for key, value in metrics.items():
        column = collection[index]
        visibility = 'hidden' if not key else 'visible'
        label = key or 'layout_spacer'

        if isinstance(value, tuple):
            column.metric(label, value[0], value[1], label_visibility=visibility)
        else:
            column.metric(label, value, label_visibility=visibility)

        index += 1
        if index >= columns:
            index = 0

def charts_block(charts, columns = None):
    if not charts:
        return
    
    if columns == None:
        columns = len(charts)

    collection = st.columns(columns)
    index = 0
    for chart in charts:
        column = collection[index]
        column.altair_chart(chart, width='stretch')

        index += 1
        if index >= columns:
            index = 0
