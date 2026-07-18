"""Reusable chart/table rendering functions for the Experiment page. Each
function no-ops if its data isn't ready yet, so the page can call all of them
unconditionally."""

import plotly.express as px
import polars as pl
import streamlit as st


def render_kpis(metrics_df: pl.DataFrame) -> None:
    if not (isinstance(metrics_df, pl.DataFrame) and metrics_df.height > 0):
        return
    kpi_df = metrics_df.to_pandas()
    st.subheader("KPIs by Variant")
    st.caption("Quick performance summary for each variant.")

    kpi_cols = st.columns([2, 1, 1, 1, 1])
    with kpi_cols[0]:
        st.markdown("**Variant**")
    with kpi_cols[1]:
        st.markdown("**Impressions**")
    with kpi_cols[2]:
        st.markdown("**Clicks**")
    with kpi_cols[3]:
        st.markdown("**CTR**")
    with kpi_cols[4]:
        st.markdown("**Cost**")

    for _, row in kpi_df.iterrows():
        kpi_cols = st.columns([2, 1, 1, 1, 1])
        with kpi_cols[0]:
            st.markdown(f"{row['variant_name']}")
        with kpi_cols[1]:
            st.markdown(f"{row['impressions']}")
        with kpi_cols[2]:
            st.markdown(f"{row['clicks']}")
        with kpi_cols[3]:
            st.markdown(f"{row['ctr'] * 100:.2f}%")
        total_cost = row.get("total_cost", row.get("cost", 0.0))
        with kpi_cols[4]:
            st.markdown(f"${float(total_cost):.2f}")


def render_allocation_evolution(decision_log_df: pl.DataFrame, total_events: int) -> None:
    if not (isinstance(decision_log_df, pl.DataFrame) and decision_log_df.height > 0):
        return
    df_log = decision_log_df.to_pandas()
    n_bins = 10
    bin_size = max(1, total_events // n_bins)
    if "time_step" not in df_log.columns:
        df_log = df_log.copy()
        df_log["time_step"] = range(1, len(df_log) + 1)
    df_log["time_bin"] = (df_log["time_step"] // bin_size) * bin_size

    df_alloc_evol = df_log.groupby(["time_bin", "variant_name"]).size().reset_index(name="allocations")

    # Normalize within each bin so it shows proportions
    df_alloc_evol["total"] = df_alloc_evol.groupby("time_bin")["allocations"].transform("sum")
    df_alloc_evol["share"] = df_alloc_evol["allocations"] / df_alloc_evol["total"]

    st.subheader("Allocation by Variant Evolution Over Time")
    st.caption(f"Traffic allocation aggregated in bins of {bin_size} steps.")

    fig_alloc = px.area(
        df_alloc_evol,
        x="time_bin",
        y="share",
        color="variant_name",
        groupnorm=None,  # already normalized manually
    )
    st.plotly_chart(fig_alloc, use_container_width=True)


def render_cumulative_ctr(decision_log_df: pl.DataFrame) -> None:
    if not (isinstance(decision_log_df, pl.DataFrame) and decision_log_df.height > 0):
        return
    df_log = decision_log_df.to_pandas()
    if "time_step" not in df_log.columns:
        df_log["time_step"] = df_log.groupby("variant_name").cumcount() + 1
    # Cumulative CTR = total clicks so far / total impressions so far, per variant.
    # This is impression-weighted (each impression counts once), unlike a plain
    # mean of per-row CTRs, which would let a 5-impression row outweigh a 5000-one.
    grp = df_log.groupby("variant_name")
    df_log["cum_clicks"] = grp["clicks"].cumsum()
    df_log["cum_impressions"] = grp["impressions"].cumsum()
    df_log["cumulative_ctr"] = df_log["cum_clicks"] / df_log["cum_impressions"]
    st.subheader("Cumulative CTR by Variant")
    st.caption("Impression-weighted click-through rate over time for each variant.")
    fig_reward = px.line(df_log, x="time_step", y="cumulative_ctr", color="variant_name")
    fig_reward.update_yaxes(tickformat=".1%", title="Cumulative CTR")
    st.plotly_chart(fig_reward, use_container_width=True)


def render_metrics_table(metrics_df: pl.DataFrame) -> None:
    if not (isinstance(metrics_df, pl.DataFrame) and metrics_df.height > 0):
        return
    st.subheader("Experiment Metrics")
    st.caption("Summary by variant: impressions, clicks, CTR, cost.")
    st.dataframe(metrics_df, use_container_width=True)


def render_allocations_table(allocations_df: pl.DataFrame) -> None:
    if not (isinstance(allocations_df, pl.DataFrame) and allocations_df.height > 0):
        return
    st.subheader("Recommended Allocations")
    st.caption("Budget distribution among variants.")
    st.dataframe(allocations_df, use_container_width=True)


def render_cost_ctr_breakdown(metrics_by_context_df: pl.DataFrame) -> None:
    if not (isinstance(metrics_by_context_df, pl.DataFrame) and metrics_by_context_df.height > 0):
        return
    df_ctx = metrics_by_context_df.to_pandas()
    st.subheader("Cost vs CTR by Variant, Segment, Device")
    fig_ctx = px.scatter(
        df_ctx,
        x="total_cost",
        y="ctr",
        color="variant_name",
        symbol="device",
        size="impressions",
        hover_data=["clicks", "user_segment", "device"],
        facet_col="user_segment",
    )
    st.plotly_chart(fig_ctx, use_container_width=True)

    st.subheader("Average CTR by Segment and Device")
    fig_bar = px.bar(df_ctx, x="user_segment", y="ctr", color="device", barmode="group")
    st.plotly_chart(fig_bar, use_container_width=True)


def render_geo(metrics_by_context_df: pl.DataFrame) -> None:
    if not (isinstance(metrics_by_context_df, pl.DataFrame) and metrics_by_context_df.height > 0):
        return
    df_geo = metrics_by_context_df.to_pandas()
    st.subheader("Geographic Performance")
    st.caption("Performance metrics by geographic location.")
    df_geo_grouped = df_geo.groupby("location").agg({"impressions": "sum", "clicks": "sum"}).reset_index()
    df_geo_grouped["ctr"] = df_geo_grouped["clicks"] / df_geo_grouped["impressions"]
    fig_geo = px.choropleth(
        df_geo_grouped,
        locations="location",
        color="ctr",
        hover_data=["impressions", "clicks"],
        color_continuous_scale=px.colors.sequential.Viridis,
        scope="world",
        projection="natural earth",
    )
    fig_geo.update_geos(
        showcountries=True, showcoastlines=True, showland=True, landcolor="#f7f7f7", countrycolor="#333"
    )
    fig_geo.update_traces(marker_line_width=1, marker_line_color="#333")
    fig_geo.update_layout(margin={"r": 0, "t": 40, "l": 0, "b": 0})
    st.plotly_chart(fig_geo, use_container_width=True)


def render_heatmap(metrics_by_context_df: pl.DataFrame) -> None:
    if not (isinstance(metrics_by_context_df, pl.DataFrame) and metrics_by_context_df.height > 0):
        return
    df_ctx = metrics_by_context_df.to_pandas()
    if not set(["device", "user_segment", "ctr"]).issubset(df_ctx.columns):
        return
    pivot = df_ctx.pivot_table(index="device", columns="user_segment", values="ctr", aggfunc="mean")
    fig_heatmap = px.imshow(
        pivot,
        text_auto=True,
        aspect="auto",
        color_continuous_scale="Viridis",
        labels=dict(x="User Segment", y="Device", color="CTR"),
    )
    st.subheader("CTR Heatmap: Device x Segment")
    st.plotly_chart(fig_heatmap, use_container_width=True)


def render_hourly(decision_log_df: pl.DataFrame) -> None:
    if not (isinstance(decision_log_df, pl.DataFrame) and decision_log_df.height > 0):
        return
    df_log = decision_log_df.to_pandas()
    if not ("context" in df_log.columns and set(["impressions", "clicks"]).issubset(df_log.columns)):
        return
    df_log["hour"] = df_log["context"].apply(lambda x: x.get("hour") if isinstance(x, dict) else None)
    hourly = df_log.groupby("hour")[["impressions", "clicks"]].sum().reset_index()
    fig_hour = px.bar(hourly, x="hour", y=["impressions", "clicks"], barmode="group")
    st.subheader("Impressions & Clicks by Hour of Day")
    st.plotly_chart(fig_hour, use_container_width=True)
