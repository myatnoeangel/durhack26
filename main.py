from dash import Dash, html, dcc, Input, Output
import pandas as pd
from pathlib import Path
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import random
from database.connection import get_connection
from strategies import (
    prepare_weather,
    weather_rule_curve,
    random_forest_curve
)
from stockdata import get_sp500_strategy

app = Dash(__name__)

import warnings

warnings.filterwarnings(
    "ignore",
    message="pandas only supports SQLAlchemy connectable"
)

# -----------------------------
# LOAD DATA FROM TIGERDATA
# -----------------------------

def load_weather_data(city):

    with get_connection() as conn:
        df = pd.read_sql_query(
            """
            SELECT
                time AS date,
                temperature AS temperature_2m,
                humidity AS relative_humidity_2m,
                precipitation,
                cloud_cover
            FROM weather_observations
            WHERE city = %s
            ORDER BY time
            """,
            conn,
            params=(city,)
        )

    df["date"] = pd.to_datetime(
        df["date"], utc=True
    ).dt.tz_convert(None)

    return df


def load_stock_data(symbol):

    with get_connection() as conn:
        df = pd.read_sql_query(
            """
            SELECT
                time,
                open,
                high,
                low,
                close,
                volume
            FROM stock_prices
            WHERE symbol = %s
            ORDER BY time
            """,
            conn,
            params=(symbol,)
        )

    df["time"] = pd.to_datetime(
        df["time"], utc=True
    ).dt.tz_convert(None)
    df = df.set_index("time")

    return df

# Load weather from TigerData
london_data = load_weather_data("London")
tokyo_data = load_weather_data("Tokyo")
sydney_data = load_weather_data("Sydney")
newyork_data = load_weather_data("New York")
shanghai_data = load_weather_data("Shanghai")

# -----------------------------
# PREPARE WEATHER STRATEGY DATA
# -----------------------------

weather_dict = {
    "London": london_data,
    "Tokyo": tokyo_data,
    "Sydney": sydney_data,
    "New York": newyork_data,
    "Shanghai": shanghai_data
}

CITIES = list(weather_dict.keys())

weather_features = prepare_weather(weather_dict)

sp500_model, sp500_buy_hold = get_sp500_strategy()

# -----------------------------
# LOAD STOCKS FROM TIGERDATA
# -----------------------------

STOCK_NAMES = {
    "AAPL": "Apple",
    "MSFT": "Microsoft",
    "TSLA": "Tesla"
}

stock_cache = {
    ticker: load_stock_data(ticker)
    for ticker in STOCK_NAMES
}

apple_data = stock_cache["AAPL"]
tesla_data = stock_cache["TSLA"]
microsoft_data = stock_cache["MSFT"]

# -----------------------------
# S&P 500 BENCHMARK
# -----------------------------

sp500_model, sp500_buy_hold = get_sp500_strategy()

# -----------------------------
# STOCK DATA HELPERS
# -----------------------------

def get_close(data):
    return data["close"]

# -----------------------------
# AVAILABLE WEATHER DATES
# -----------------------------

available_dates = sorted(
    pd.to_datetime(london_data["date"]).dt.date.unique().tolist()
)

if not available_dates:
    raise ValueError("No historical weather dates were downloaded.")

default_date = available_dates[-1]


# -----------------------------
# BUILD THE GRAPH
# -----------------------------

PALETTE = ["#8B5CF6", "#F28C68", "#269C91", "#3A86FF", "#D1495B", "#6A994E", "#B5838D"]
FRAME_MS = 500
POINTS_PER_FRAME = 1

def build_figure(tickers, strategies):
    fig = go.Figure()
    tickers = tickers or []
    strategies = strategies or []

    for n, ticker in enumerate(tickers):
        close = get_close(stock_cache[ticker]).dropna()
        if close.empty:
            continue
        color = PALETTE[n % len(PALETTE)]

        if "Buy & Hold" in strategies:
            fig.add_scatter(
                x=close.index,
                y=close / close.iloc[0] * 100,
                mode="lines",
                name=f"{ticker} Buy & Hold",
                line=dict(color=color, width=3)
            )

        if "Weather Rule" in strategies:
            curve = weather_rule_curve(close, weather_features, CITIES)
            if not curve.empty:
                fig.add_scatter(
                    x=curve.index,
                    y=curve.values,
                    mode="lines",
                    name=f"{ticker} Weather Rule",
                    line=dict(color=color, width=3, dash="dot")
                )

        if "Random Forest (test period)" in strategies:
            curve = random_forest_curve(close, weather_features, CITIES)
            if not curve.empty:
                fig.add_scatter(
                    x=curve.index,
                    y=curve.values,
                    mode="lines",
                    name=f"{ticker} Random Forest",
                    line=dict(color=color, width=3, dash="dash")
                )

    if "S&P 500" in strategies:
        fig.add_scatter(
            x=sp500_model.index,
            y=sp500_model.values,
            mode="lines",
            name="S&P 500 Model",
            line=dict(color="#E09F3E", width=3)
        )
        fig.add_scatter(
            x=sp500_buy_hold.index,
            y=sp500_buy_hold.values,
            mode="lines",
            name="S&P 500 Buy & Hold",
            line=dict(color="#493D50", width=3, dash="dash")
        )

    # ---- styling ----
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="#E0D4E7",
        plot_bgcolor="#F8F3FA",
        font=dict(family="Arial", color="#493D50"),
        title=dict(
            text="Stock Performance - Last Year",
            x=0.03,
            font=dict(size=22)
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        xaxis=dict(title="Date", showgrid=False, linecolor="#C9B8D1"),
        yaxis=dict(
            title="Performance (starting at 100)",
            gridcolor="#E6DCEB",
            zeroline=False
        ),
        margin=dict(l=45, r=25, t=85, b=45),
        hovermode="x unified"
    )

    fig.update_traces(hovertemplate="%{y:.2f}<extra>%{fullData.name}</extra>")

    if len(fig.data) == 0:
        fig.update_layout(title=dict(text="Pick a stock and a strategy"))
        return fig

    # ---- animation ----
    max_len = max(len(trace.x) for trace in fig.data)

    all_x = [x for trace in fig.data for x in trace.x]
    all_y = np.concatenate(
        [np.asarray(trace.y, dtype=float) for trace in fig.data]
    )
    y_min = np.nanmin(all_y)
    y_max = np.nanmax(all_y)
    y_pad = (y_max - y_min) * 0.05

    fig.update_xaxes(range=[min(all_x), max(all_x)])
    fig.update_yaxes(range=[y_min - y_pad, y_max + y_pad])

    steps = list(range(1, max_len + 1, 3))
    if steps[-1] != max_len:
        steps.append(max_len)

    fig.frames = [
        go.Frame(
            data=[
                go.Scatter(x=trace.x[:i], y=trace.y[:i])
                for trace in fig.data
            ],
            name=str(i)
        )
        for i in steps
    ]

    fig.update_layout(
        updatemenus=[
            dict(
                type="buttons",
                showactive=False,
                buttons=[
                    dict(
                        label="▶ Play",
                        method="animate",
                        args=[
                            None,
                            {
                                "frame": {"duration": 40, "redraw": True},
                                "fromcurrent": True
                            }
                        ]
                    ),
                    dict(
                        label="⏸ Pause",
                        method="animate",
                        args=[
                            [None],
                            {
                                "frame": {"duration": 0, "redraw": False},
                                "mode": "immediate"
                            }
                        ]
                    )
                ]
            )
        ]
    )

    return fig


# -----------------------------
# CARD STYLES
# -----------------------------

card_style = {
    "padding": "5px 12px",
    # "borderRadius": "8px",
    "textAlign": "left",
    "minHeight": "35px",
    "display": "flex",
    "flexDirection": "row",
    "alignItems": "center",
    "justifyContent": "space-between",
    "gap": "8px"
}

grid_style = {
    "display": "flex",
    "flexDirection": "column",
    "gap": "6px"
}


def make_card(title, value="", subtitle="", background="#FFF1E5"):
    return html.Div(
        [
            html.Span(
                title,
                style={
                    "fontWeight": "bold",
                    "color": "#493D50",
                    "flex": "1"
                }
            ),
            html.Span(
                value,
                style={
                    "fontWeight": "bold",
                    "color": "#493D50"
                }
            ),
            html.Span(
                subtitle,
                style={
                    "fontSize": "12px",
                    "color": "#817489",
                    "textAlign": "right"
                }
            )
        ],
        style={
            **card_style,
            "backgroundColor": background
        }
    )


# -----------------------------
# WEATHER AND STOCK CARD DATA
# -----------------------------

weather_locations = [
    ("London", london_data),
    ("Tokyo", tokyo_data),
    ("Sydney", sydney_data),
    ("New York", newyork_data),
    ("Shanghai", shanghai_data)
]

stock_locations = [
    (name, stock_cache[ticker])
    for ticker, name in STOCK_NAMES.items()
]


def condition_label(rain_mm, cloud_pct):
    # Same thresholds as the weather rule in strategies.py
    if rain_mm > 1:
        return "🌧 Rainy"
    if cloud_pct < 30:
        return "☀️ Sunny"
    if cloud_pct < 70:
        return "⛅ Partly cloudy"
    return "☁️ Cloudy"


def make_detail_card(title, value, details, background,
                     subtitle="", value_color="#493D50"):
    """A card with a headline row, an optional subtitle and small detail chips."""

    children = [
        html.Div(
            [
                html.Span(
                    title,
                    style={
                        "fontWeight": "bold",
                        "color": "#493D50",
                        "flex": "1"
                    }
                ),
                html.Span(
                    value,
                    style={
                        "fontWeight": "bold",
                        "color": value_color
                    }
                )
            ],
            style={
                "display": "flex",
                "alignItems": "center",
                "gap": "8px"
            }
        )
    ]

    if subtitle:
        children.append(
            html.Div(
                subtitle,
                style={"fontSize": "12px", "color": "#817489"}
            )
        )

    children.append(
        html.Div(
            [
                html.Span(
                    [
                        html.Span(f"{label} ", style={"color": "#817489"}),
                        html.Span(
                            val,
                            style={"color": "#493D50", "fontWeight": "bold"}
                        )
                    ]
                )
                for label, val in details
            ],
            style={
                "display": "flex",
                "flexWrap": "wrap",
                "gap": "2px 14px",
                "fontSize": "12px",
                "marginTop": "4px"
            }
        )
    )

    return html.Div(
        children,
        style={
            "padding": "6px 12px",
            "backgroundColor": background,
            "display": "flex",
            "flexDirection": "column"
        }
    )


def build_weather_cards(selected_date):

    selected_day = pd.to_datetime(selected_date).date()

    cards = []

    for name, data in weather_locations:

        dates = pd.to_datetime(data["date"]).dt.date
        day_data = data.loc[dates == selected_day]

        if day_data.empty:
            cards.append(make_card(name, "No data", "", "#FFF1E5"))
            continue

        rain = day_data["precipitation"].sum()
        cloud = day_data["cloud_cover"].mean()

        cards.append(
            make_detail_card(
                name,
                f"{day_data['temperature_2m'].mean():.1f}°C",
                [
                    ("High", f"{day_data['temperature_2m'].max():.1f}°C"),
                    ("Low", f"{day_data['temperature_2m'].min():.1f}°C"),
                    ("Humidity", f"{day_data['relative_humidity_2m'].mean():.0f}%"),
                    ("Rain", f"{rain:.1f} mm"),
                    ("Cloud", f"{cloud:.0f}%")
                ],
                "#FFF1E5",
                subtitle=condition_label(rain, cloud)
            )
        )

    return cards


def safe_value(data, column, index):
    """Returns data[column] at index, or None if it isn't available."""
    try:
        return float(get_col(data, column).loc[index])
    except Exception:
        return None


def format_volume(volume):
    if volume is None or pd.isna(volume):
        return "n/a"
    if volume >= 1e9:
        return f"{volume / 1e9:.2f}B"
    if volume >= 1e6:
        return f"{volume / 1e6:.1f}M"
    return f"{volume:,.0f}"


def build_stock_cards(selected_date):

    selected_day = pd.to_datetime(selected_date).date()

    cards = []

    for name, data in stock_locations:

        close = get_close(data).dropna()

        # Find the latest closing price on or before selected date
        dates = pd.to_datetime(close.index).date
        available_prices = close.loc[dates <= selected_day]

        if available_prices.empty:
            cards.append(
                make_card(name, "No data", "No earlier trading day", "#E0F5F1")
            )
            continue

        last_index = available_prices.index[-1]
        price = available_prices.iloc[-1]
        price_date = last_index.strftime("%d/%m/%Y")

        # Change compared with the previous trading day
        if len(available_prices) > 1:
            change = price / available_prices.iloc[-2] - 1
            change_text = f"{change * 100:+.2f}%"
            change_color = "#2E7D32" if change >= 0 else "#C62828"
        else:
            change_text = "n/a"
            change_color = "#493D50"

        high = safe_value(data, "High", last_index)
        low = safe_value(data, "Low", last_index)
        open_price = safe_value(data, "Open", last_index)
        volume = safe_value(data, "Volume", last_index)

        details = [
            ("Change", change_text),
            ("Open", f"${open_price:.2f}" if open_price is not None else "n/a"),
            ("High", f"${high:.2f}" if high is not None else "n/a"),
            ("Low", f"${low:.2f}" if low is not None else "n/a"),
            ("Volume", format_volume(volume))
        ]

        cards.append(
            make_detail_card(
                name,
                f"${price:.2f}",
                details,
                "#E0F5F1",
                subtitle=f"Closing price: {price_date}",
                value_color=change_color
            )
        )

    return cards


# -----------------------------
# MAIN APP LAYOUT
# -----------------------------

app.layout = html.Div(
    [
        # HEADER
        html.H1(
            "Weather you lose or win, isn't our problem",
            style={
                "textAlign": "center",
                "color": "#493D50",
                "margin": "5px 0 15px 0",
                "fontSize": "28px"
            }
        ),

        # DATE PICKER AND RANDOM BUTTON
        html.Div(
            [
                dcc.DatePickerSingle(
                    id="date-picker",
                    date=default_date.isoformat(),
                    min_date_allowed=available_dates[0].isoformat(),
                    max_date_allowed=available_dates[-1].isoformat(),
                    display_format="DD/MM/YYYY"
                ),

                html.Button(
                    "Random date",
                    id="random-date",
                    n_clicks=0,
                    style={
                        "padding": "8px 15px",
                        # "borderRadius": "8px",
                        "border": "none",
                        "backgroundColor": "#A9E4DE",
                        "cursor": "pointer",
                        "color": "#493D50"
                    }
                )
            ],
            style={
                "display": "flex",
                "alignItems": "center",
                "gap": "12px",
                "justifyContent": "center",
                "marginBottom": "10px"
            }
        ),

        # GRAPH CONTROLS
        html.Div(
            [
                dcc.Dropdown(
                    id="ticker-select",
                    options=[
                        {"label": f"{name} ({ticker})", "value": ticker}
                        for ticker, name in STOCK_NAMES.items()
                    ],
                    value=["AAPL", "TSLA", "MSFT"],
                    multi=True,
                    style={"minWidth": "280px"}
                ),
                dcc.Checklist(
                    id="strategy-select",
                    options=[
                        "Buy & Hold",
                        "Weather Rule",
                        "Random Forest (test period)",
                        "S&P 500"
                    ],
                    value=["Buy & Hold", "Weather Rule", "S&P 500"],
                    inline=True,
                    style={"color": "#493D50"}
                )
            ],
            style={
                "display": "flex",
                "alignItems": "center",
                "gap": "20px",
                "justifyContent": "center",
                "marginBottom": "10px"
            }
        ),

        # MAIN CONTENT
        html.Div(
            [
                # LEFT: STOCK GRAPH
                html.Div(
                    [
                        dcc.Graph(
                            id="stock-graph",
                            style={"height": "100%"},
                            config={"responsive": True}
                        )
                    ],
                    style={
                        "backgroundColor": "#E0D4E7",
                        "padding": "12px",
                        "margin": "5px",
                        "flex": "1.6",
                        "minWidth": "0",
                        "minHeight": "0"
                    }
                ),

                # RIGHT SIDE
                html.Div(
                    [
                        # TOP RIGHT: WEATHER
                        html.Div(
                            [
                                html.H3(
                                    "Historical Weather",
                                    style={"color": "#493D50"}
                                ),

                                html.Div(
                                    build_weather_cards(default_date),
                                    id="weather-cards",
                                    style=grid_style
                                )
                            ],
                            style={
                                "backgroundColor": "#FEC89A",
                                "padding": "12px",
                                "margin": "5px",
                                "flex": "1",
                                "overflowY": "auto"
                            }
                        ),

                        # BOTTOM RIGHT: STOCKS
                        html.Div(
                            [
                                html.H3(
                                    "Stock Prices",
                                    style={"color": "#493D50"}
                                ),

                                html.Div(
                                    build_stock_cards(default_date),
                                    id="stock-cards",
                                    style=grid_style
                                )
                            ],
                            style={
                                "backgroundColor": "#A9E4DE",
                                "padding": "12px",
                                "margin": "5px",
                                "flex": "1",
                                "overflowY": "auto"
                            }
                        )
                    ],
                    style={
                        "display": "flex",
                        "flexDirection": "column",
                        "flex": "1",
                        "minWidth": "0",
                        "minHeight": "0"
                    }
                )
            ],
            style={
                "display": "flex",
                "flexDirection": "row",
                "flex": "1",
                "minHeight": "0"
            }
        )
    ],
    style={
        "display": "flex",
        "flexDirection": "column",
        "height": "100vh",
        "padding": "8px",
        "boxSizing": "border-box"
    }
)


# -----------------------------
# RANDOM DATE CALLBACK
# -----------------------------

@app.callback(
    Output("date-picker", "date"),
    Input("random-date", "n_clicks"),
    prevent_initial_call=True
)
def choose_random_date(n_clicks):
    return random.choice(available_dates).isoformat()


# -----------------------------
# UPDATE CARDS WHEN DATE CHANGES
# -----------------------------

@app.callback(
    Output("weather-cards", "children"),
    Output("stock-cards", "children"),
    Input("date-picker", "date")
)
def update_cards(selected_date):

    if not selected_date:
        return [], []

    weather_cards = build_weather_cards(selected_date)
    stock_cards = build_stock_cards(selected_date)

    return weather_cards, stock_cards


# -----------------------------
# UPDATE GRAPH WHEN CONTROLS CHANGE
# -----------------------------

@app.callback(
    Output("stock-graph", "figure"),
    Input("ticker-select", "value"),
    Input("strategy-select", "value")
)
def update_graph(tickers, strategies):
    return build_figure(tickers, strategies)


# -----------------------------
# RUN APP
# -----------------------------

if __name__ == "__main__":
    app.run(debug=True)