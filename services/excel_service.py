import os
import io
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from models import Worker, Badge, ExposureRecord
from config import Config

class ExcelService:
    """
    Industrial Excel Export & Persistence Service for H2SENSE.
    Generates professionally formatted, audit-ready .xlsx workbooks
    containing worker directories, active badge lifecycles, and exposure histories.
    """

    # Palette
    HEADER_FILL = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
    SUBHEADER_FILL = PatternFill(start_color="334155", end_color="334155", fill_type="solid")
    ALT_ROW_FILL = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    
    # Status Fills
    STATUS_FILLS = {
        "SAFE": PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid"),
        "CAUTION": PatternFill(start_color="FEF9C3", end_color="FEF9C3", fill_type="solid"),
        "HIGH": PatternFill(start_color="FFEDD5", end_color="FFEDD5", fill_type="solid"),
        "CRITICAL": PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid"),
        "VALID": PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid"),
        "NEAR EXPIRY": PatternFill(start_color="FEF9C3", end_color="FEF9C3", fill_type="solid"),
        "EXPIRED": PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid"),
        "REVOKED": PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid"),
        "ACTIVE": PatternFill(start_color="E0F2FE", end_color="E0F2FE", fill_type="solid"),
        "INACTIVE": PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
    }

    STATUS_FONTS = {
        "SAFE": Font(name="Calibri", size=10, bold=True, color="166534"),
        "CAUTION": Font(name="Calibri", size=10, bold=True, color="854D0E"),
        "HIGH": Font(name="Calibri", size=10, bold=True, color="9A3412"),
        "CRITICAL": Font(name="Calibri", size=10, bold=True, color="991B1B"),
        "VALID": Font(name="Calibri", size=10, bold=True, color="166534"),
        "NEAR EXPIRY": Font(name="Calibri", size=10, bold=True, color="854D0E"),
        "EXPIRED": Font(name="Calibri", size=10, bold=True, color="991B1B"),
        "REVOKED": Font(name="Calibri", size=10, bold=True, color="64748B"),
        "ACTIVE": Font(name="Calibri", size=10, bold=True, color="0369A1"),
        "INACTIVE": Font(name="Calibri", size=10, bold=True, color="64748B")
    }

    THIN_BORDER = Border(
        left=Side(style='thin', color="E2E8F0"),
        right=Side(style='thin', color="E2E8F0"),
        top=Side(style='thin', color="E2E8F0"),
        bottom=Side(style='thin', color="E2E8F0")
    )

    @classmethod
    def generate_workers_excel(cls, workers=None) -> io.BytesIO:
        """
        Creates a multi-sheet, fully formatted Excel workbook
        containing the complete worker roster and exposure telemetry history.
        Returns:
            io.BytesIO: Buffer containing the binary .xlsx workbook.
        """
        if workers is None:
            workers = Worker.query.order_by(Worker.worker_code.asc()).all()

        wb = Workbook()

        # ===============================================================
        # SHEET 1: WORKER DIRECTORY & ROSTER
        # ===============================================================
        ws1 = wb.active
        ws1.title = "Worker Directory"
        ws1.views.sheetView[0].showGridLines = True

        # Document Header Banner
        ws1.merge_cells("A1:O1")
        title_cell = ws1["A1"]
        title_cell.value = "H₂SENSE INDUSTRIAL SAFETY SYSTEM — WORKFORCE EXPOSURE ROSTER"
        title_cell.font = Font(name="Calibri", size=14, bold=True, color="FFFFFF")
        title_cell.fill = cls.HEADER_FILL
        title_cell.alignment = Alignment(horizontal="center", vertical="center")
        ws1.row_dimensions[1].height = 36

        # Subtitle metadata
        ws1.merge_cells("A2:O2")
        meta_cell = ws1["A2"]
        meta_cell.value = (
            f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}  |  "
            f"Total Operators: {len(workers)}  |  "
            f"Facility: Refinery Processing Unit  |  "
            f"Safety Protocol: Prototype Colorimetric H₂S Monitoring"
        )
        meta_cell.font = Font(name="Calibri", size=9, italic=True, color="E2E8F0")
        meta_cell.fill = cls.SUBHEADER_FILL
        meta_cell.alignment = Alignment(horizontal="center", vertical="center")
        ws1.row_dimensions[2].height = 20

        # Column Headers
        headers1 = [
            "Worker Code",
            "Full Name",
            "Department",
            "Role / Designation",
            "Phone / Contact",
            "Status",
            "Active Badge Code",
            "Badge Expiry Date",
            "Days Remaining",
            "Badge Validity",
            "Latest Reading (ppm)",
            "Risk Classification",
            "Cumulative Exposure (ppm)",
            "Total Scans",
            "Registration Date"
        ]

        ws1.row_dimensions[3].height = 26
        for col_num, header in enumerate(headers1, 1):
            cell = ws1.cell(row=3, column=col_num)
            cell.value = header
            cell.font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
            cell.fill = cls.HEADER_FILL
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = cls.THIN_BORDER

        # Data Rows
        row_idx = 4
        for w in workers:
            active_badge = w.get_active_badge()
            latest_rec = w.get_latest_record()
            cum_exp = w.get_cumulative_exposure()
            scans_count = w.exposure_records.count()

            badge_code = active_badge.badge_code if active_badge else "UNASSIGNED"
            badge_expiry = active_badge.expiry_date.strftime('%Y-%m-%d') if active_badge and active_badge.expiry_date else "N/A"
            badge_days = active_badge.days_remaining if active_badge else 0
            badge_validity = active_badge.validity_status if active_badge else "NONE"

            latest_val = round(latest_rec.corrected_exposure, 1) if latest_rec else 0.0
            latest_status = latest_rec.status if latest_rec else "SAFE"
            reg_date = w.created_at.strftime('%Y-%m-%d %H:%M') if w.created_at else "N/A"

            row_data = [
                w.worker_code,
                w.name,
                w.department,
                w.role,
                w.phone or "N/A",
                w.status,
                badge_code,
                badge_expiry,
                badge_days,
                badge_validity,
                latest_val,
                latest_status,
                cum_exp,
                scans_count,
                reg_date
            ]

            ws1.row_dimensions[row_idx].height = 22
            is_alt = (row_idx % 2 == 0)

            for col_idx, val in enumerate(row_data, 1):
                c = ws1.cell(row=row_idx, column=col_idx, value=val)
                c.font = Font(name="Calibri", size=10)
                c.border = cls.THIN_BORDER
                c.alignment = Alignment(vertical="center")

                # Alternating row background
                if is_alt:
                    c.fill = cls.ALT_ROW_FILL

                # Specific Column Alignments & Formats
                if col_idx in [1, 7, 8]:  # Worker Code, Badge, Expiry
                    c.alignment = Alignment(horizontal="center", vertical="center")
                elif col_idx in [9, 11, 13, 14]:  # Numeric columns
                    c.alignment = Alignment(horizontal="right", vertical="center")
                    if col_idx in [11, 13]:
                        c.number_format = '0.0'
                    elif col_idx in [9, 14]:
                        c.number_format = '#,##0'

                # Status Highlight: Worker Status (Col 6)
                if col_idx == 6 and val in cls.STATUS_FILLS:
                    c.fill = cls.STATUS_FILLS[val]
                    c.font = cls.STATUS_FONTS.get(val, c.font)
                    c.alignment = Alignment(horizontal="center", vertical="center")

                # Status Highlight: Badge Validity (Col 10)
                if col_idx == 10 and val in cls.STATUS_FILLS:
                    c.fill = cls.STATUS_FILLS[val]
                    c.font = cls.STATUS_FONTS.get(val, c.font)
                    c.alignment = Alignment(horizontal="center", vertical="center")

                # Status Highlight: Risk Classification (Col 12)
                if col_idx == 12 and val in cls.STATUS_FILLS:
                    c.fill = cls.STATUS_FILLS[val]
                    c.font = cls.STATUS_FONTS.get(val, c.font)
                    c.alignment = Alignment(horizontal="center", vertical="center")

            row_idx += 1

        # Adjust Column Widths for Sheet 1
        for col in ws1.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                if cell.row in [1, 2]:
                    continue  # Skip banner rows
                val_str = str(cell.value or '')
                if len(val_str) > max_len:
                    max_len = len(val_str)
            ws1.column_dimensions[col_letter].width = max(max_len + 4, 12)

        # ===============================================================
        # SHEET 2: EXPOSURE AUDIT & COLORIMETRIC LOGS
        # ===============================================================
        ws2 = wb.create_sheet(title="Exposure History Logs")
        ws2.views.sheetView[0].showGridLines = True

        ws2.merge_cells("A1:S1")
        title_cell2 = ws2["A1"]
        title_cell2.value = "H₂SENSE HISTORICAL SENSOR SCANS & COLORIMETRIC CALIBRATION AUDIT"
        title_cell2.font = Font(name="Calibri", size=14, bold=True, color="FFFFFF")
        title_cell2.fill = cls.HEADER_FILL
        title_cell2.alignment = Alignment(horizontal="center", vertical="center")
        ws2.row_dimensions[1].height = 36

        headers2 = [
            "Scan ID",
            "Timestamp (UTC)",
            "Worker Code",
            "Worker Name",
            "Department",
            "Badge Code",
            "Scan Type",
            "Measured RGB",
            "Hex Code",
            "CIELAB (L*, a*, b*)",
            "Temp (°C)",
            "Humidity (%RH)",
            "Raw Exposure",
            "Env Correction",
            "Corrected Total",
            "Shift Delta",
            "Cumulative Total",
            "Risk Status",
            "Confidence"
        ]

        ws2.row_dimensions[2].height = 26
        for col_num, header in enumerate(headers2, 1):
            cell = ws2.cell(row=2, column=col_num)
            cell.value = header
            cell.font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
            cell.fill = cls.HEADER_FILL
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = cls.THIN_BORDER

        all_records = ExposureRecord.query.order_by(ExposureRecord.timestamp.desc()).all()
        row_idx2 = 3
        for rec in all_records:
            w_code = rec.worker.worker_code if rec.worker else "N/A"
            w_name = rec.worker.name if rec.worker else "N/A"
            w_dept = rec.worker.department if rec.worker else "N/A"
            b_code = rec.badge.badge_code if rec.badge else "N/A"

            rgb_str = f"RGB({rec.r}, {rec.g}, {rec.b})"
            hex_str = f"#{rec.r:02x}{rec.g:02x}{rec.b:02x}"
            lab_str = f"L* {round(rec.lab_l, 1)}  a* {round(rec.lab_a, 1)}  b* {round(rec.lab_b, 1)}"
            env_sign = "+" if (rec.corrected_exposure - rec.raw_exposure) >= 0 else ""
            env_corr = f"{env_sign}{round(rec.corrected_exposure - rec.raw_exposure, 1)}"
            conf_str = f"{round(rec.confidence * 100, 1)}%"

            row_data2 = [
                rec.id,
                rec.timestamp.strftime('%Y-%m-%d %H:%M:%S') if rec.timestamp else '',
                w_code,
                w_name,
                w_dept,
                b_code,
                rec.scan_type,
                rgb_str,
                hex_str,
                lab_str,
                round(rec.temperature, 1),
                round(rec.humidity, 1),
                round(rec.raw_exposure, 1),
                env_corr,
                round(rec.corrected_exposure, 1),
                round(rec.shift_exposure, 1),
                round(rec.cumulative_exposure, 1),
                rec.status,
                conf_str
            ]

            ws2.row_dimensions[row_idx2].height = 20
            is_alt2 = (row_idx2 % 2 == 0)

            for col_idx2, val in enumerate(row_data2, 1):
                c = ws2.cell(row=row_idx2, column=col_idx2, value=val)
                c.font = Font(name="Calibri", size=9)
                c.border = cls.THIN_BORDER
                c.alignment = Alignment(vertical="center")

                if is_alt2:
                    c.fill = cls.ALT_ROW_FILL

                if col_idx2 in [1, 2, 3, 6, 7, 9]:
                    c.alignment = Alignment(horizontal="center", vertical="center")
                elif col_idx2 in [11, 12, 13, 14, 15, 16, 17, 19]:
                    c.alignment = Alignment(horizontal="right", vertical="center")

                # Highlight Risk Status
                if col_idx2 == 18 and val in cls.STATUS_FILLS:
                    c.fill = cls.STATUS_FILLS[val]
                    c.font = cls.STATUS_FONTS.get(val, c.font)
                    c.alignment = Alignment(horizontal="center", vertical="center")

                # Highlight Scan Type (Col 7)
                if col_idx2 == 7:
                    if val == 'ENTRY':
                        c.fill = PatternFill(start_color="F0FDF4", end_color="F0FDF4", fill_type="solid")
                        c.font = Font(name="Calibri", size=9, bold=True, color="166534")
                    else:
                        c.fill = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")
                        c.font = Font(name="Calibri", size=9, bold=True, color="92400E")

            row_idx2 += 1

        # Adjust Column Widths for Sheet 2
        for col in ws2.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                if cell.row == 1:
                    continue
                val_str = str(cell.value or '')
                if len(val_str) > max_len:
                    max_len = len(val_str)
            ws2.column_dimensions[col_letter].width = max(max_len + 3, 11)

        # Output to memory buffer
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return output

    @classmethod
    def save_workers_excel_to_file(cls, filepath=None, workers=None) -> str:
        """
        Generates and saves the Excel sheet directly to the filesystem.
        Default location: Config.EXPORTS_FOLDER / 'workers_master_data.xlsx'.
        Returns:
            str: Absolute file path where the workbook was saved.
        """
        if not filepath:
            os.makedirs(Config.EXPORTS_FOLDER, exist_ok=True)
            filepath = os.path.join(Config.EXPORTS_FOLDER, "workers_master_data.xlsx")

        buf = cls.generate_workers_excel(workers=workers)
        with open(filepath, "wb") as f:
            f.write(buf.getbuffer())
        return filepath
