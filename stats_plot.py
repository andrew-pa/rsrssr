import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import datetime

from sqlalchemy.orm import scoped_session


def plot_update_stats_figure(data: pd.DataFrame) -> go.Figure:
    # Create subplots: 2 rows, 2 columns
    fig = make_subplots(
        rows=2,
        cols=2,
        subplot_titles=(
            "Total Update Time and Feed Count",
            "New Items over Time",
            "Fetched, Updated, and Failed",
            "Per-Feed Update Time",
        ),
        specs=[
            [{"secondary_y": True}, {"secondary_y": False}],
            [{"secondary_y": False}, {"secondary_y": False}],
        ],
        shared_xaxes=False,
        vertical_spacing=0.1,
        horizontal_spacing=0.1,
    )

    # Plot 1: dur_total and num_feeds with secondary Y axis
    fig.add_trace(
        go.Scatter(
            x=data["timestamp"],
            y=data["dur_total"],
            mode="lines",
            name="Total Duration",
        ),
        row=1,
        col=1,
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=data["timestamp"],
            y=data["num_feeds"],
            mode="lines",
            name="Num Feeds",
            yaxis="y2",
        ),
        row=1,
        col=1,
        secondary_y=True,
    )
    fig.update_yaxes(title_text="Total Duration (s)", secondary_y=False, row=1, col=1)
    fig.update_yaxes(title_text="Num Feeds", secondary_y=True, row=1, col=1)

    # Plot 2: num_new_items
    fig.add_trace(
        go.Scatter(
            x=data["timestamp"],
            y=data["num_new_items"],
            mode="lines",
            name="Num New Items",
        ),
        row=1,
        col=2,
    )
    fig.update_yaxes(title_text="Num New Items", row=1, col=2)

    # Plot 3: num_fetched, num_updated, num_failed
    fig.add_trace(
        go.Scatter(
            x=data["timestamp"], y=data["num_fetched"], mode="lines", name="Num Fetched"
        ),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=data["timestamp"], y=data["num_updated"], mode="lines", name="Num Updated"
        ),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=data["timestamp"], y=data["num_failed"], mode="lines", name="Num Failed"
        ),
        row=2,
        col=1,
    )
    fig.update_yaxes(title_text="Num Feeds", row=2, col=1)

    # Plot 4: dur_min_feed, dur_avg_feed, dur_max_feed with error bars for dur_avg_feed
    fig.add_trace(
        go.Scatter(
            x=data["timestamp"],
            y=data["dur_min_feed"],
            mode="lines",
            name="Min Feed Duration",
            text=data["min_feed_url"],
            hovertemplate="%{y}ms; %{text}",
        ),
        row=2,
        col=2,
    )
    fig.add_trace(
        go.Scatter(
            x=data["timestamp"],
            y=data["dur_avg_feed"],
            mode="lines",
            name="Avg Feed Duration",
            error_y=dict(type="data", array=data["dur_std_feed"], visible=True),
        ),
        row=2,
        col=2,
    )
    fig.add_trace(
        go.Scatter(
            x=data["timestamp"],
            y=data["dur_max_feed"],
            mode="lines",
            name="Max Feed Duration",
            text=data["max_feed_url"],
            hovertemplate="%{y}ms; %{text}",
        ),
        row=2,
        col=2,
    )
    fig.update_yaxes(title_text="Duration (ms)", row=2, col=2)

    # Update layout for a clean look
    fig.update_layout(
        title_text="RSS Updates",
        showlegend=True,
        hovermode="x unified",
        plot_bgcolor="black",
        paper_bgcolor="black",
        font={"color": "white"},
    )

    return fig
