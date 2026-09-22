"""
Plotly figures for backtest results.

Kept out of dashboard.py so the same charts can be used from a notebook or
script, and so they can be rendered and eyeballed without Streamlit.
"""

from typing import Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from backtester import BacktestResult

# Chart colors, validated against the plotly_dark surface
C_EQUITY = '#3987e5'      # strategy equity / SMA 20
C_BENCH = '#d95926'       # buy & hold reference / SMA 50
C_PRICE = '#ffffff'       # price line
C_ENTRY = '#0ca30c'       # entry marks (always paired with a label, never color alone)
C_EXIT = '#d03b3b'        # exit marks / drawdown
C_SURFACE = '#111111'     # plotly_dark surface, used for marker rings
C_MUTED = '#898781'       # axis / reference ink

# Diverging scale for signed metrics (return %, Sharpe): cool = negative, warm =
# positive, neutral gray at the true zero (set via zmid, not the data's min/max)
DIVERGING_SCALE = [
    [0.00, '#0d366b'],
    [0.25, '#3987e5'],
    [0.50, '#f0efec'],
    [0.75, '#ef8584'],
    [1.00, '#e34948'],
]


def equity_figure(result: BacktestResult) -> go.Figure:
    """
    Equity curve against buy & hold, with the drawdown underneath.

    Two panels rather than two y-axes: dollars and percent never share a scale.
    """
    equity = result.equity_curve
    buy_hold = result.data['close'] / float(result.data['close'].iloc[0]) * result.initial_capital
    drawdown = result.drawdown_curve()

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.1,
        row_heights=[0.68, 0.32],
        subplot_titles=("Equity Curve", "Drawdown from Peak (%)")
    )

    fig.add_trace(
        go.Scatter(x=equity.index, y=equity, name="Strategy",
                   line=dict(color=C_EQUITY, width=2),
                   hovertemplate="Strategy: $%{y:,.0f}<extra></extra>"),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(x=buy_hold.index, y=buy_hold, name="Buy & Hold",
                   line=dict(color=C_BENCH, width=2, dash='dot'),
                   hovertemplate="Buy & Hold: $%{y:,.0f}<extra></extra>"),
        row=1, col=1
    )
    # Break-even reference
    fig.add_hline(y=result.initial_capital, line_dash="dash", line_color=C_MUTED,
                  line_width=1, row=1, col=1)

    fig.add_trace(
        go.Scatter(x=drawdown.index, y=drawdown, name="Drawdown",
                   line=dict(color=C_EXIT, width=1.5),
                   fill='tozeroy', fillcolor='rgba(208,59,59,0.2)', showlegend=False,
                   hovertemplate="Drawdown: %{y:.2f}%<extra></extra>"),
        row=2, col=1
    )

    fig.update_layout(height=560, hovermode='x unified', template='plotly_dark',
                      margin=dict(t=70, b=40, l=60, r=30),
                      legend=dict(orientation='h', yanchor='bottom', y=1.04, x=0))
    fig.update_yaxes(title_text="Equity ($)", row=1, col=1)
    fig.update_yaxes(title_text="Drawdown (%)", row=2, col=1)
    fig.update_xaxes(title_text="Date", row=2, col=1)
    return fig


def trades_figure(result: BacktestResult) -> go.Figure:
    """Price with the strategy's moving averages and every entry / exit marked"""
    data = result.data
    trades = result.trades_frame()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=data.index, y=data['close'], name="Close",
        line=dict(color=C_PRICE, width=2),
        hovertemplate="Close: $%{y:.2f}<extra></extra>"
    ))
    fig.add_trace(go.Scatter(
        x=data.index, y=data['sma_20'], name="SMA 20",
        line=dict(color=C_EQUITY, width=1.5),
        hovertemplate="SMA 20: $%{y:.2f}<extra></extra>"
    ))
    fig.add_trace(go.Scatter(
        x=data.index, y=data['sma_50'], name="SMA 50",
        line=dict(color=C_BENCH, width=1.5),
        hovertemplate="SMA 50: $%{y:.2f}<extra></extra>"
    ))

    if not trades.empty:
        fig.add_trace(go.Scatter(
            x=trades['entry_date'], y=trades['entry_price'],
            name="Entry", mode='markers',
            marker=dict(symbol='triangle-up', size=13, color=C_ENTRY,
                        line=dict(color=C_SURFACE, width=2)),
            customdata=trades['shares'],
            hovertemplate="<b>Entry</b> $%{y:.2f}<br>%{customdata:.0f} shares<extra></extra>"
        ))

        closed = trades[trades['status'] == 'closed']
        if not closed.empty:
            fig.add_trace(go.Scatter(
                x=closed['exit_date'], y=closed['exit_price'],
                name="Exit", mode='markers',
                marker=dict(symbol='triangle-down', size=13, color=C_EXIT,
                            line=dict(color=C_SURFACE, width=2)),
                customdata=closed[['return_pct', 'exit_reason']],
                hovertemplate=("<b>Exit</b> $%{y:.2f}<br>Return: %{customdata[0]:.2f}%"
                               "<br>Reason: %{customdata[1]}<extra></extra>")
            ))

        # Shade each holding period so entries and exits read as pairs
        for t in result.closed_trades:
            fig.add_vrect(x0=t.entry_date, x1=t.exit_date, line_width=0,
                          fillcolor=C_ENTRY if t.is_winner else C_EXIT, opacity=0.07)
        for t in result.open_trades:
            fig.add_vrect(x0=t.entry_date, x1=data.index[-1], line_width=0,
                          fillcolor=C_MUTED, opacity=0.07)

    fig.update_layout(height=520, hovermode='x unified', template='plotly_dark',
                      title="Trades on Price", yaxis_title="Price ($)", xaxis_title="Date",
                      margin=dict(t=90, b=40, l=60, r=30),
                      legend=dict(orientation='h', yanchor='bottom', y=1.02, x=0))
    return fig


def _metric_label(metric: str) -> str:
    """'total_return_pct' -> 'Total Return (%)'; used for axis/legend text"""
    is_pct = metric.endswith('_pct')
    base = metric[:-4] if is_pct else metric
    label = base.replace('_', ' ').title()
    return f"{label} (%)" if is_pct else label


def ranking_bar_chart(table: pd.DataFrame, metric: str = 'total_return_pct',
                       label_col: str = 'strategy', title: Optional[str] = None) -> go.Figure:
    """
    Horizontal bar ranking of strategies by one metric, colored good/bad
    (never by rank — the same strategy keeps its color if the list is refiltered).
    """
    df = table[[label_col, metric]].dropna().sort_values(metric, ascending=True)
    colors = [C_ENTRY if v >= 0 else C_EXIT for v in df[metric]]
    # Outside labels need headroom on both ends, or the largest bar's label
    # clips against the plot edge — pad the range instead of clipping it off
    span = max(df[metric].max(), 0) - min(df[metric].min(), 0)
    pad = span * 0.18 or 1.0

    fig = go.Figure(go.Bar(
        x=df[metric], y=df[label_col], orientation='h',
        marker=dict(color=colors), cliponaxis=False,
        text=[f"{v:+.1f}" for v in df[metric]], textposition='outside',
        hovertemplate="%{y}: %{x:.2f}<extra></extra>",
    ))
    fig.add_vline(x=0, line_color=C_MUTED, line_width=1)
    fig.update_layout(
        title=title or _metric_label(metric),
        template='plotly_dark', height=90 + 46 * len(df),
        margin=dict(t=60, b=40, l=180, r=60), showlegend=False,
    )
    fig.update_xaxes(title_text=_metric_label(metric),
                     range=[df[metric].min() - pad, df[metric].max() + pad])
    return fig


def heatmap_figure(pivot: pd.DataFrame, metric_label: str = "Total Return (%)",
                    title: str = "Strategy × Asset Performance") -> go.Figure:
    """
    Diverging heatmap of a signed metric across strategies (rows) and assets
    (columns). The number is printed on every cell — color is a secondary
    channel, readable at a glance but never the only way to get the value.
    """
    z = pivot.to_numpy(dtype=float)
    # Text color: near the neutral midpoint the tile is pale, so use dark ink;
    # toward either extreme the tile is saturated, so use light ink
    vmax = np.nanmax(np.abs(z)) if np.isfinite(z).any() and np.nanmax(np.abs(z)) > 0 else 1.0
    text_colors = np.where(np.abs(z) / vmax > 0.45, '#ffffff', '#0b0b0b')

    fig = go.Figure(go.Heatmap(
        z=z, x=list(pivot.columns), y=list(pivot.index),
        colorscale=DIVERGING_SCALE, zmid=0,
        hovertemplate="%{y} on %{x}<br>" + metric_label + ": %{z:.2f}<extra></extra>",
        colorbar=dict(title=metric_label),
        xgap=3, ygap=3,
    ))
    annotations = []
    for yi, row_label in enumerate(pivot.index):
        for xi, col_label in enumerate(pivot.columns):
            val = z[yi, xi]
            if not np.isnan(val):
                annotations.append(dict(
                    x=col_label, y=row_label, text=f"{val:.1f}", showarrow=False,
                    font=dict(color=text_colors[yi, xi], size=12),
                ))
    fig.update_layout(
        title=title, height=120 + 54 * len(pivot.index),
        template='plotly_white', margin=dict(t=60, b=40, l=160, r=40),
        annotations=annotations,
    )
    return fig
