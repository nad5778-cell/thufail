"""Render anomaly detection results as a styled Excel dashboard (in-memory)."""

import io

import pandas as pd


def build_dashboard_xlsx(result: pd.DataFrame, pic_code: str) -> bytes:
    total = len(result)
    anomaly_count = int(result["is_anomaly"].sum())
    normal_count = total - anomaly_count
    anomaly_rate = (anomaly_count / total * 100) if total else 0.0

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        workbook = writer.book

        title_fmt = workbook.add_format({"bold": True, "font_size": 18, "font_color": "#1F4E78"})
        subtitle_fmt = workbook.add_format({"font_size": 10, "italic": True, "font_color": "#7F7F7F"})
        kpi_label_fmt = workbook.add_format({"bold": True, "font_size": 11, "font_color": "#FFFFFF",
                                              "bg_color": "#1F4E78", "align": "center", "valign": "vcenter",
                                              "border": 1})
        kpi_value_fmt = workbook.add_format({"bold": True, "font_size": 22, "font_color": "#1F4E78",
                                              "align": "center", "valign": "vcenter", "border": 1,
                                              "bg_color": "#EAF1F8"})
        kpi_alert_fmt = workbook.add_format({"bold": True, "font_size": 22, "font_color": "#C00000",
                                              "align": "center", "valign": "vcenter", "border": 1,
                                              "bg_color": "#FDEBEB"})
        header_fmt = workbook.add_format({"bold": True, "font_color": "#FFFFFF", "bg_color": "#1F4E78",
                                           "align": "center", "valign": "vcenter", "border": 1})

        summary = workbook.add_worksheet("Dashboard")
        writer.sheets["Dashboard"] = summary
        summary.hide_gridlines(2)
        summary.set_column("A:A", 3)
        summary.set_column("B:H", 16)

        summary.merge_range("B2:H2", "Anomaly Detection Dashboard", title_fmt)
        summary.merge_range("B3:H3", f"NATIONAL_IDENTITY anomalies | PIC = {pic_code}", subtitle_fmt)

        kpis = [
            ("Total Records", total, kpi_value_fmt),
            ("Normal Records", normal_count, kpi_value_fmt),
            ("Anomalies Found", anomaly_count, kpi_alert_fmt),
            ("Anomaly Rate", f"{anomaly_rate:.1f}%", kpi_alert_fmt),
        ]
        col = 1
        for label, value, value_fmt in kpis:
            summary.merge_range(4, col, 4, col + 1, label, kpi_label_fmt)
            summary.merge_range(5, col, 6, col + 1, value, value_fmt)
            col += 2

        summary.write_row("B9", ["Category", "Count"])
        summary.write_row("B10", ["Normal", normal_count])
        summary.write_row("B11", ["Anomaly", anomaly_count])

        chart = workbook.add_chart({"type": "doughnut"})
        chart.add_series({
            "name": "Anomaly Breakdown",
            "categories": ["Dashboard", 9, 1, 10, 1],
            "values": ["Dashboard", 9, 2, 10, 2],
            "points": [{"fill": {"color": "#2E75B6"}}, {"fill": {"color": "#C00000"}}],
            "data_labels": {"percentage": True, "font": {"bold": True}},
        })
        chart.set_title({"name": "Normal vs Anomaly"})
        chart.set_size({"width": 380, "height": 260})
        summary.insert_chart("B13", chart)

        result_sorted = result.sort_values("anomaly_score", ascending=False).reset_index(drop=True)
        result_sorted.to_excel(writer, sheet_name="Details", index=False, startrow=1, header=False)
        detail = writer.sheets["Details"]

        for col_idx, col_name in enumerate(result_sorted.columns):
            detail.write(0, col_idx, col_name, header_fmt)
            width = max(14, len(col_name) + 2)
            detail.set_column(col_idx, col_idx, width)

        n_rows = len(result_sorted)
        if n_rows:
            score_col = result_sorted.columns.get_loc("anomaly_score")
            flag_col = result_sorted.columns.get_loc("is_anomaly")
            last_col = len(result_sorted.columns) - 1

            red_fmt = workbook.add_format({"bg_color": "#FDEBEB", "font_color": "#C00000"})

            detail.conditional_format(1, 0, n_rows, last_col, {
                "type": "formula",
                "criteria": f"=${chr(65 + flag_col)}2=TRUE",
                "format": red_fmt,
            })
            detail.conditional_format(1, score_col, n_rows, score_col, {
                "type": "3_color_scale",
                "min_color": "#63BE7B", "mid_color": "#FFEB84", "max_color": "#F8696B",
            })

        detail.autofilter(0, 0, n_rows, len(result_sorted.columns) - 1)
        detail.freeze_panes(1, 0)

        anomalies = result_sorted[result_sorted["is_anomaly"]].reset_index(drop=True)
        anomalies.to_excel(writer, sheet_name="Anomalies", index=False, startrow=1, header=False)
        anomaly_sheet = writer.sheets["Anomalies"]

        anomaly_header_fmt = workbook.add_format({"bold": True, "font_color": "#FFFFFF", "bg_color": "#C00000",
                                                    "align": "center", "valign": "vcenter", "border": 1})
        for col_idx, col_name in enumerate(anomalies.columns):
            anomaly_sheet.write(0, col_idx, col_name, anomaly_header_fmt)
            width = max(14, len(col_name) + 2)
            anomaly_sheet.set_column(col_idx, col_idx, width)

        n_anomaly_rows = len(anomalies)
        if n_anomaly_rows:
            row_fmt = workbook.add_format({"bg_color": "#FDEBEB", "font_color": "#C00000"})
            anomaly_sheet.conditional_format(1, 0, n_anomaly_rows, len(anomalies.columns) - 1, {
                "type": "no_errors",
                "format": row_fmt,
            })
            anomaly_sheet.autofilter(0, 0, n_anomaly_rows, len(anomalies.columns) - 1)
            anomaly_sheet.freeze_panes(1, 0)

    return buffer.getvalue()
