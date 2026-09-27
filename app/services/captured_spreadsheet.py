import os
import csv
import threading
from datetime import datetime
from typing import List, Dict, Any
import pandas as pd

STORAGE_DIR = os.path.join(os.getcwd(), "storage")
CSV_PATH = os.path.join(STORAGE_DIR, "captured_students.csv")
EXCEL_PATH = os.path.join(STORAGE_DIR, "captured_students.xlsx")

CSV_HEADERS = [
    "Timestamp",
    "Registration_Number",
    "Full_Name",
    "Department",
    "Pose",
    "Quality_Score_Percent",
    "Photo_Filename",
    "Photo_Path",
    "Status"
]

_file_lock = threading.Lock()


def ensure_storage_ready() -> None:
    """Ensure storage directory and header files exist."""
    os.makedirs(STORAGE_DIR, exist_ok=True)
    with _file_lock:
        if not os.path.exists(CSV_PATH):
            with open(CSV_PATH, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(CSV_HEADERS)
        
        if not os.path.exists(EXCEL_PATH):
            df = pd.DataFrame(columns=CSV_HEADERS)
            df.to_excel(EXCEL_PATH, index=False, engine="openpyxl")


def record_captured_photo(
    reg_number: str,
    full_name: str,
    department: str = "General",
    pose: str = "frontal",
    quality_score: float = 100.0,
    photo_filename: str = "",
    photo_path: str = "",
    status: str = "STORED"
) -> Dict[str, Any]:
    """
    Appends a new captured photo record to both CSV and Excel files.
    Thread-safe to prevent concurrent file access issues.
    """
    ensure_storage_ready()
    
    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    q_str = f"{round(quality_score, 1)}%" if quality_score <= 100 else f"{quality_score}%"

    row_data = {
        "Timestamp": timestamp_str,
        "Registration_Number": reg_number.strip().upper(),
        "Full_Name": full_name.strip(),
        "Department": department.strip() if department else "General",
        "Pose": pose.strip().lower(),
        "Quality_Score_Percent": q_str,
        "Photo_Filename": photo_filename,
        "Photo_Path": photo_path,
        "Status": status
    }

    with _file_lock:
        # 1. Append to CSV
        file_exists = os.path.exists(CSV_PATH)
        with open(CSV_PATH, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
            if not file_exists:
                writer.writeheader()
            writer.writerow(row_data)

        # 2. Update Excel (.xlsx)
        try:
            if os.path.exists(CSV_PATH):
                df = pd.read_csv(CSV_PATH)
                df.to_excel(EXCEL_PATH, index=False, engine="openpyxl")
        except Exception as e:
            print(f"[CapturedSpreadsheet] Warning updating Excel: {e}")

    return row_data


def get_all_captured_records() -> List[Dict[str, Any]]:
    """Reads all captured student records from CSV."""
    ensure_storage_ready()
    records = []
    with _file_lock:
        if os.path.exists(CSV_PATH):
            try:
                with open(CSV_PATH, mode="r", newline="", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        records.append(dict(row))
            except Exception as e:
                print(f"[CapturedSpreadsheet] Read error: {e}")
    return records


def get_csv_file_path() -> str:
    """Returns absolute path to CSV file."""
    ensure_storage_ready()
    return CSV_PATH


def get_excel_file_path() -> str:
    """Returns absolute path to Excel file."""
    ensure_storage_ready()
    return EXCEL_PATH
