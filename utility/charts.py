import altair as alt

from utility.globals import get_labels_angle

LABELS_ANGLE = get_labels_angle()

# SETTINGS

def update_settings():
    global LABELS_ANGLE
    LABELS_ANGLE = get_labels_angle()

# BAR CHARTS

def bar_chart(df, title, x_axis, y_axis, style='main'):
    update_settings()
    if style == 'alternate':
        return bar_chart_alternate(df, title, x_axis, y_axis)
    elif style == 'team2':
        return bar_chart_team2(df, title, x_axis, y_axis)
    else:
        return bar_chart_main(df, title, x_axis, y_axis)

def bar_chart_main(df, title, x_axis, y_axis):
    return alt.Chart(df, title=title).mark_bar().encode(
        x=alt.X(f'{x_axis}:O', sort=None, axis=alt.Axis(labelAngle=LABELS_ANGLE), title=None),
        y=alt.Y(y_axis, title=None))

def bar_chart_alternate(df, title, x_axis, y_axis):
    return alt.Chart(df, title=title).mark_bar().encode(
        x=alt.X(x_axis, sort=None, axis=alt.Axis(labelAngle=LABELS_ANGLE), title=None),
        y=alt.Y(y_axis, title=None)
    ).configure_bar(
        color='yellowgreen',
        opacity=0.8
    )

def bar_chart_team2(df, title, x_axis, y_axis):
    return alt.Chart(df, title=title).mark_bar().encode(
        x=alt.X(x_axis, sort=None, axis=alt.Axis(labelAngle=LABELS_ANGLE), title=None),
        y=alt.Y(y_axis, title=None)
    ).configure_bar(
        color='orangered',
        opacity=0.8
    )

def horizontal_bar_chart_match_duration(df):
    update_settings()
    return alt.Chart(df, title='Average match duration (min)').mark_bar().encode(
        x=alt.X('Duration:Q', title=None),
        y=alt.Y('Team:N', title=None, sort=None),
        tooltip=['Team', alt.Tooltip('Duration:Q', format='.2f')]
    )

# STACKED BAR CHARTS

def stacked_bar_chart(df, title, x_axis, y_axis, color):
    update_settings()
    return alt.Chart(df, title=title).mark_bar().encode(
        x=alt.X(f'{x_axis}:N', sort=alt.EncodingSortField(field=y_axis, op='sum', order='descending'), axis=alt.Axis(labelAngle=LABELS_ANGLE), title=None),
        y=alt.Y(f'{y_axis}:Q', title=None),
        color=alt.Color(f'{color}:N', legend=alt.Legend(title=color), scale=alt.Scale(domain=['1', '2'], range=['lightskyblue', 'orangered'])),
        tooltip=[
            alt.Tooltip(f'{color}:N', title=color),
            alt.Tooltip(f'{y_axis}:Q', title=y_axis)
        ]
    )

def stacked_ordered_bar_chart(df, title, x_axis, y_axis, color, order, scheme=None):
    if not scheme:
        scheme = 'category20c'
    
    chart = alt.Chart(df, title=title).transform_calculate(
        order=f"-indexof({order}, datum.Origin)"
    ).mark_bar().encode(
        x=alt.X(f'{x_axis}:O', axis=alt.Axis(title=x_axis), sort=None),
        y=alt.Y(f'{y_axis}:Q', axis=alt.Axis(title=y_axis), sort=None),
        color=alt.Color(f'{color}:N', legend=alt.Legend(title=color), sort=order, scale=alt.Scale(scheme=scheme)),
        order='order:Q',
        tooltip=[
            alt.Tooltip(f'{color}:N', title=color),
            alt.Tooltip(f'{y_axis}:Q', title=y_axis)
        ]
    )

    return chart

def negative_stacked_bar_chart_mech_usage(df):
    update_settings()

    base = alt.Chart(df, title='Mech usage by tonnage').mark_bar().encode(
        x=alt.X('Tonnage:N', title=None, sort=None, axis=alt.Axis(labelAngle=LABELS_ANGLE)),
        y=alt.Y('Positive:Q', title=None, stack='zero'),
        y2=alt.Y2('Negative:Q'),
        tooltip=[
            alt.Tooltip('Result:N', title="Result"),
            alt.Tooltip('count:Q', title="Uses")
        ]
    )
    bars = base.mark_bar().encode(
        color=alt.Color('Result', scale=alt.Scale(domain=['WIN', 'LOSS']))
    )
    return bars

def negative_horizontal_stacked_bar_chart_map_stats(df, title):
    update_settings()

    upper_bound = df['Positive'].max()
    lower_bound = df['Negative'].min()
    ticks = int(upper_bound - lower_bound)

    base = alt.Chart(df, title=title).mark_bar().encode(
        x=alt.X('Positive:Q', title=None, stack='zero', sort=None).axis(tickCount=ticks),
        y=alt.Y('Map:N', title=None, sort=None),
        x2=alt.X2('Negative:Q'),
        tooltip=[
            alt.Tooltip('Result:N', title="Result"),
            alt.Tooltip('count:Q', title="Count")
        ]
    )
    bars = base.mark_bar().encode(
        color=alt.Color('Result', scale=alt.Scale(domain=['WIN', 'LOSS']))
    )
    return bars

# LINE CHARTS

def line_chart_submitted_games(df):
    update_settings()
    return alt.Chart(df).mark_line(color='firebrick').encode(
        alt.X('yearmonth(CompleteTime):T', title='Month'),
        alt.Y('distinct(MatchID)', type='nominal', title='Submitted Games')
    )
