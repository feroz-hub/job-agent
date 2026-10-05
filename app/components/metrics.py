"""Dashboard and processing counters."""
import streamlit as st


def render_metrics(values: dict[str, int]) -> None:
    for column, (label, count) in zip(st.columns(len(values)), values.items()):
        column.metric(label, count)
