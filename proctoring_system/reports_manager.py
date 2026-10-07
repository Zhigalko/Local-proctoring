"""
Reports and Session Management for Proctoring System.
Manages session directory structures under reports/<YYYY-MM-DD_HH-MM>_<Student_Name>/,
creates summary.json, archives incident screenshots, and generates exports (HTML/CSV).
"""

import os
import re
import json
import csv
import shutil
import base64
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

import cv2
import numpy as np

from proctoring_system.config import REPORTS_DIR, INCIDENTS_DIR


INCIDENT_RUSSIAN_NAMES = {
    "PHONE_DETECTED": "Обнаружен смартфон",
    "LOOKING_AWAY": "Отвод головы в сторону (>1.5с)",
    "LOOKING_DOWN": "Взгляд опущен вниз (>1.5с)",
    "GAZE_AWAY": "Отвод взгляда от экрана (>1.5с)",
    "GAZE_DEVIATION": "Отвод взгляда от экрана",
    "NO_FACE": "Студент покинул рабочее место (нет лица)",
    "MULTIPLE_FACES": "Второе лицо в кадре",
    "HOTKEY_BLOCKED": "Попытка запрещенной клавиши / хоткея",
    "FOCUS_LOST": "Потеря фокуса окна (Alt+Tab / переключение)"
}


def sanitize_filename(name: str) -> str:
    """Sanitize string for safe cross-platform filesystem directory naming."""
    cleaned = re.sub(r'[^\w\s\u0400-\u04FF-]', '', name).strip()
    cleaned = re.sub(r'\s+', '_', cleaned)
    return cleaned or "Студент"


def get_status_info(violation_count: int) -> tuple[str, str, str]:
    """Returns (status_key, status_ru, color_hex) based on violation count."""
    if violation_count == 0:
        return "CLEAN", "Чисто", "#22c55e"
    elif violation_count <= 2:
        return "ATTENTION", "Требует внимания", "#f59e0b"
    else:
        return "CHEATING", "Подозрение на списывание", "#ef4444"


class SessionReportManager:
    """Handles creation, reading, and export of student examination sessions."""

    @staticmethod
    def save_session(
        student_name: str,
        start_time: datetime,
        end_time: datetime,
        correct_count: int,
        total_count: int,
        score_pct: int,
        time_spent: str,
        incidents: list
    ) -> Path:
        """
        Creates session directory: reports/<YYYY-MM-DD_HH-MM>_<ФИО_студента>/
        Archives incident screenshots into screenshots/ folder and saves summary.json.
        """
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)

        date_prefix = start_time.strftime("%Y-%m-%d_%H-%M")
        safe_student = sanitize_filename(student_name)
        folder_name = f"{date_prefix}_{safe_student}"
        session_dir = REPORTS_DIR / folder_name

        # Avoid collision
        counter = 1
        while session_dir.exists():
            session_dir = REPORTS_DIR / f"{folder_name}_{counter}"
            counter += 1

        session_dir.mkdir(parents=True, exist_ok=True)
        screenshots_dir = session_dir / "screenshots"
        screenshots_dir.mkdir(parents=True, exist_ok=True)

        status_key, status_ru, status_color = get_status_info(len(incidents))

        processed_incidents = []
        for idx, inc in enumerate(incidents):
            inc_dict = inc.to_dict() if hasattr(inc, "to_dict") else dict(inc)
            inc_type = inc_dict.get("incident_type", "INCIDENT")
            inc_type_ru = INCIDENT_RUSSIAN_NAMES.get(inc_type, inc_type)
            inc_id = f"inc_{idx+1:03d}"

            # Calculate time code relative to session start
            time_code = "00:00"
            duration_sec = 1.5
            timestamp_str = ""
            try:
                inc_time_str = inc_dict.get("timestamp", "")
                if inc_time_str:
                    inc_dt = datetime.fromisoformat(inc_time_str)
                    offset_sec = max(0, int((inc_dt - start_time).total_seconds()))
                    mins = offset_sec // 60
                    secs = offset_sec % 60
                    time_code = f"{mins:02d}:{secs:02d}"
                    timestamp_str = inc_dt.strftime("%H:%M:%S")
                details = inc_dict.get("details", {})
                if isinstance(details, dict) and "duration" in details:
                    duration_sec = float(details["duration"])
            except Exception:
                pass

            if not timestamp_str:
                timestamp_str = datetime.now().strftime("%H:%M:%S")

            # Copy screenshot into session folder
            orig_shot = inc_dict.get("screenshot_path", "")
            target_shot_rel = ""
            if orig_shot and Path(orig_shot).exists():
                shot_filename = f"{idx+1:03d}_{inc_type.lower()}.jpg"
                dest_path = screenshots_dir / shot_filename
                try:
                    shutil.copy2(orig_shot, dest_path)
                    target_shot_rel = f"screenshots/{shot_filename}"
                except Exception as e:
                    print(f"[SessionReportManager] Error copying screenshot: {e}")

            processed_incidents.append({
                "incident_id": inc_id,
                "id": idx + 1,
                "timestamp": timestamp_str,
                "time": inc_dict.get("timestamp", datetime.now().isoformat()),
                "time_code": time_code,
                "type": inc_type,
                "type_ru": inc_type_ru,
                "severity": inc_dict.get("severity", "MEDIUM"),
                "description": inc_dict.get("description", ""),
                "duration_sec": duration_sec,
                "details": inc_dict.get("details", {}),
                "screenshot": target_shot_rel,
                "appeal": inc_dict.get("appeal", None)
            })

        summary_data = {
            "session_id": session_dir.name,
            "student_name": student_name,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "score": f"{correct_count} / {total_count}",
            "score_pct": score_pct,
            "correct_count": correct_count,
            "total_count": total_count,
            "time_spent": time_spent,
            "total_violations": len(incidents),
            "status": status_key,
            "status_ru": status_ru,
            "status_color": status_color,
            "incidents": processed_incidents
        }

        summary_file = session_dir / "summary.json"
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary_data, f, indent=2, ensure_ascii=False)

        print(f"[SessionReportManager] Session successfully archived at: {session_dir}")
        return session_dir

    @staticmethod
    def submit_appeal(session_dir_or_id: Any, incident_id: str, reason: str, comment: str) -> Optional[Dict[str, Any]]:
        """
        Saves student appeal on a specific violation incident in summary.json.
        Returns the updated appeal structure or None if not found.
        """
        if isinstance(session_dir_or_id, (str, Path)):
            target_path = Path(session_dir_or_id)
            if not target_path.is_dir():
                target_path = REPORTS_DIR / str(session_dir_or_id)
        else:
            return None

        summary_file = target_path / "summary.json"
        if not summary_file.exists():
            return None

        try:
            with open(summary_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            appeal_entry = {
                "status": "pending",
                "reason": reason,
                "comment": comment,
                "submitted_at": datetime.now().strftime("%H:%M:%S"),
                "teacher_comment": ""
            }

            found = False
            for inc in data.get("incidents", []):
                if (
                    inc.get("incident_id") == incident_id
                    or str(inc.get("id")) == str(incident_id)
                    or f"inc_{inc.get('id', 0):03d}" == incident_id
                ):
                    inc["appeal"] = appeal_entry
                    found = True
                    break

            if found:
                with open(summary_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                print(f"[SessionReportManager] Appeal recorded for {incident_id} in {target_path.name}")
                return appeal_entry
        except Exception as e:
            print(f"[SessionReportManager] Error submitting appeal: {e}")
        return None

    @staticmethod
    def review_appeal(
        session_dir_or_id: Any,
        incident_id: str,
        new_status: str,
        teacher_comment: str = ""
    ) -> bool:
        """
        Instructor reviews an appeal: 'approved' | 'rejected'.
        If approved, incident is marked excused and session status is recalculated.
        """
        if isinstance(session_dir_or_id, (str, Path)):
            target_path = Path(session_dir_or_id)
            if not target_path.is_dir():
                target_path = REPORTS_DIR / str(session_dir_or_id)
        else:
            return False

        summary_file = target_path / "summary.json"
        if not summary_file.exists():
            return False

        try:
            with open(summary_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            updated = False
            for inc in data.get("incidents", []):
                if (
                    inc.get("incident_id") == incident_id
                    or str(inc.get("id")) == str(incident_id)
                    or f"inc_{inc.get('id', 0):03d}" == incident_id
                ):
                    if not inc.get("appeal"):
                        inc["appeal"] = {
                            "status": new_status,
                            "reason": "Рассмотрено преподавателем",
                            "comment": "",
                            "submitted_at": datetime.now().strftime("%H:%M:%S"),
                            "teacher_comment": teacher_comment
                        }
                    else:
                        inc["appeal"]["status"] = new_status
                        inc["appeal"]["teacher_comment"] = teacher_comment
                    updated = True
                    break

            if updated:
                active_violations = sum(
                    1 for inc in data.get("incidents", [])
                    if not (inc.get("appeal") and inc["appeal"].get("status") == "approved")
                )
                status_key, status_ru, status_color = get_status_info(active_violations)
                data["effective_violations"] = active_violations
                data["status"] = status_key
                data["status_ru"] = status_ru
                data["status_color"] = status_color

                with open(summary_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                print(f"[SessionReportManager] Appeal for {incident_id} reviewed -> {new_status}")
                return True
        except Exception as e:
            print(f"[SessionReportManager] Error reviewing appeal: {e}")
        return False

    @staticmethod
    def list_sessions() -> List[Dict[str, Any]]:
        """Scans reports/ and returns all sessions sorted from newest to oldest."""
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        sessions = []

        for item in REPORTS_DIR.iterdir():
            if item.is_dir():
                summary_file = item / "summary.json"
                if summary_file.exists():
                    try:
                        with open(summary_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            data["folder_path"] = str(item)
                            data["folder_name"] = item.name
                            sessions.append(data)
                    except Exception as e:
                        print(f"[SessionReportManager] Error loading session {item.name}: {e}")

        # Sort newest first by start_time
        sessions.sort(key=lambda s: s.get("start_time", ""), reverse=True)
        return sessions

    @staticmethod
    def get_session(folder_name: str) -> Optional[Dict[str, Any]]:
        """Loads a specific session by folder name."""
        summary_file = REPORTS_DIR / folder_name / "summary.json"
        if summary_file.exists():
            try:
                with open(summary_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    data["folder_path"] = str(summary_file.parent)
                    data["folder_name"] = folder_name
                    return data
            except Exception as e:
                print(f"[SessionReportManager] Error loading session: {e}")
        return None

    @staticmethod
    def export_session_html(session_dir: Path, output_file: Path) -> bool:
        """Exports a beautiful standalone HTML incident report with embedded proof."""
        try:
            summary_file = session_dir / "summary.json"
            if not summary_file.exists():
                return False
            with open(summary_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            incidents_rows = ""
            for inc in data.get("incidents", []):
                shot_html = "—"
                if inc.get("screenshot"):
                    shot_path = session_dir / inc["screenshot"]
                    if shot_path.exists():
                        try:
                            with open(shot_path, "rb") as img_f:
                                b64 = base64.b64encode(img_f.read()).decode("utf-8")
                                shot_html = f'<img src="data:image/jpeg;base64,{b64}" style="max-height: 80px; border-radius: 6px; cursor: pointer;" title="Фотофиксация"/>'
                        except Exception:
                            shot_html = inc["screenshot"]

                sev_color = "#ef4444" if inc.get("severity") in ["CRITICAL", "HIGH"] else "#f59e0b"

                appeal = inc.get("appeal")
                if appeal:
                    app_status = appeal.get("status", "pending")
                    if app_status == "approved":
                        app_badge = '<span style="background: rgba(34,197,94,0.2); color: #4ade80; padding: 3px 8px; border-radius: 6px; font-weight: 700; font-size: 12px;">✅ Одобрена</span>'
                    elif app_status == "rejected":
                        app_badge = '<span style="background: rgba(239,68,68,0.2); color: #f87171; padding: 3px 8px; border-radius: 6px; font-weight: 700; font-size: 12px;">❌ Отклонена</span>'
                    else:
                        app_badge = '<span style="background: rgba(245,158,11,0.2); color: #fbbf24; padding: 3px 8px; border-radius: 6px; font-weight: 700; font-size: 12px;">⏳ На рассмотрении</span>'

                    t_comment = f'<div style="color: #94a3b8; font-size: 11px; margin-top: 2px;">Вердикт: {appeal.get("teacher_comment")}</div>' if appeal.get("teacher_comment") else ''
                    appeal_td = f"""
                    <td>
                        {app_badge}
                        <div style="font-size: 11.5px; color: #cbd5e1; margin-top: 4px;"><strong>Причина:</strong> {appeal.get('reason', '')}</div>
                        <div style="font-size: 11px; color: #94a3b8;">{appeal.get('comment', '')}</div>
                        {t_comment}
                    </td>
                    """
                else:
                    appeal_td = '<td><span style="color: #64748b; font-size: 12px;">— Не подавалась</span></td>'

                incidents_rows += f"""
                <tr>
                    <td><strong>⏱️ {inc.get('time_code', '00:00')}</strong></td>
                    <td><span style="background: rgba(56,189,248,0.15); color: #38bdf8; padding: 4px 10px; border-radius: 6px; font-weight: 700;">{inc.get('type_ru', '')}</span></td>
                    <td><span style="color: {sev_color}; font-weight: 700;">{inc.get('severity', '')}</span></td>
                    <td>{inc.get('duration_sec', 1.5)} сек</td>
                    <td>{inc.get('description', '')}</td>
                    {appeal_td}
                    <td style="text-align: center;">{shot_html}</td>
                </tr>
                """

            if not incidents_rows:
                incidents_rows = '<tr><td colspan="7" style="text-align: center; padding: 20px; color: #4ade80;">🟢 В ходе тестирования нарушений регламента не зафиксировано!</td></tr>'

            html_content = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>Протокол прокторинга — {data.get('student_name')}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background-color: #0b1120; color: #f8fafc; margin: 0; padding: 40px 20px; }}
  .container {{ max-width: 1050px; margin: 0 auto; background-color: #1e293b; border: 1px solid #334155; border-radius: 16px; padding: 36px; box-shadow: 0 20px 40px rgba(0,0,0,0.5); }}
  h1 {{ margin: 0 0 10px; color: #38bdf8; font-size: 26px; }}
  .badge {{ display: inline-block; padding: 6px 16px; border-radius: 8px; font-weight: 800; font-size: 14px; background: {data.get('status_color')}; color: #0b1120; }}
  .meta-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin: 24px 0; background: #0f172a; padding: 20px; border-radius: 12px; border: 1px solid #334155; }}
  .meta-item .lbl {{ font-size: 12px; color: #94a3b8; text-transform: uppercase; font-weight: 700; margin-bottom: 4px; }}
  .meta-item .val {{ font-size: 18px; font-weight: 800; color: #f8fafc; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 24px; }}
  th {{ background: #0f172a; color: #94a3b8; text-align: left; padding: 12px 14px; font-size: 13px; text-transform: uppercase; border-bottom: 2px solid #334155; }}
  td {{ padding: 12px 14px; border-bottom: 1px solid #334155; font-size: 14px; vertical-align: middle; }}
  tr:hover {{ background: rgba(56, 189, 248, 0.05); }}
</style>
</head>
<body>
<div class="container">
  <div style="display: flex; justify-content: space-between; align-items: center;">
    <div>
      <h1>🛡️ Протокол тестирования с локальным прокторингом</h1>
      <div style="color: #94a3b8; font-size: 14px;">Система автоматизированного контроля экзамена и учета апелляций</div>
    </div>
    <div class="badge">{data.get('status_ru', '')}</div>
  </div>

  <div class="meta-grid">
    <div class="meta-item"><div class="lbl">Студент</div><div class="val">{data.get('student_name', '')}</div></div>
    <div class="meta-item"><div class="lbl">Результат теста</div><div class="val" style="color: #38bdf8;">{data.get('score', '')} ({data.get('score_pct', 0)}%)</div></div>
    <div class="meta-item"><div class="lbl">Время экзамена</div><div class="val">{data.get('time_spent', '')}</div></div>
    <div class="meta-item"><div class="lbl">Нарушений зафиксировано</div><div class="val" style="color: {data.get('status_color')};">{data.get('total_violations', 0)}</div></div>
  </div>

  <h2 style="font-size: 18px; color: #f8fafc; margin-top: 30px;">📋 Таймлайн зафиксированных инцидентов и апелляций:</h2>
  <table>
    <thead>
      <tr>
        <th>Таймкод</th>
        <th>Тип нарушения</th>
        <th>Уровень</th>
        <th>Длительность</th>
        <th>Описание инцидента</th>
        <th>Апелляция</th>
        <th style="text-align: center;">Доказательство</th>
      </tr>
    </thead>
    <tbody>
      {incidents_rows}
    </tbody>
  </table>
  <div style="margin-top: 30px; text-align: right; font-size: 12px; color: #64748b;">
    Сформировано автоматически системой Local Proctoring • {datetime.now().strftime("%d.%m.%Y %H:%M")}
  </div>
</div>
</body>
</html>"""
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(html_content)
            return True
        except Exception as e:
            print(f"[SessionReportManager] Error exporting HTML: {e}")
            return False

    @staticmethod
    def export_session_csv(session_dir: Path, output_file: Path) -> bool:
        """Exports session incident log with appeals to a CSV file."""
        try:
            summary_file = session_dir / "summary.json"
            if not summary_file.exists():
                return False
            with open(summary_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            with open(output_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Student", data.get("student_name", "")])
                writer.writerow(["Score", data.get("score", "")])
                writer.writerow(["TimeSpent", data.get("time_spent", "")])
                writer.writerow(["Status", data.get("status_ru", "")])
                writer.writerow([])
                writer.writerow(["TimeCode", "Type", "Severity", "DurationSec", "Description", "AppealStatus", "AppealReason", "AppealComment", "TeacherComment", "Screenshot"])
                for inc in data.get("incidents", []):
                    appeal = inc.get("appeal") or {}
                    writer.writerow([
                        inc.get("time_code", ""),
                        inc.get("type_ru", ""),
                        inc.get("severity", ""),
                        inc.get("duration_sec", ""),
                        inc.get("description", ""),
                        appeal.get("status", "none"),
                        appeal.get("reason", ""),
                        appeal.get("comment", ""),
                        appeal.get("teacher_comment", ""),
                        inc.get("screenshot", "")
                    ])
            return True
        except Exception as e:
            print(f"[SessionReportManager] Error exporting CSV: {e}")
            return False

    @staticmethod
    def ensure_demo_sessions():
        """
        Creates 3 realistic demo examination sessions if reports directory is empty,
        or ensures existing demo sessions have appeal records populated.
        """
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        existing = [d for d in REPORTS_DIR.iterdir() if d.is_dir() and (d / "summary.json").exists()]

        # If sessions exist, check if we need to backfill appeals/incident_ids
        if existing:
            for d in existing:
                try:
                    s_file = d / "summary.json"
                    with open(s_file, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    updated = False
                    for idx, inc in enumerate(data.get("incidents", [])):
                        if "incident_id" not in inc:
                            inc["incident_id"] = f"inc_{idx+1:03d}"
                            updated = True
                        time_str = inc.get("time", "")
                        try:
                            if time_str:
                                inc["timestamp"] = datetime.fromisoformat(time_str).strftime("%H:%M:%S")
                            else:
                                inc["timestamp"] = datetime.now().strftime("%H:%M:%S")
                            updated = True
                        except Exception:
                            inc["timestamp"] = "12:00:00"

                    # Add sample appeals for Ivanova and Petrova if missing
                    s_name = data.get("student_name", "")
                    if "Иванов" in s_name and data.get("incidents"):
                        inc0 = data["incidents"][0]
                        if not inc0.get("appeal"):
                            inc0["appeal"] = {
                                "status": "pending",
                                "reason": "Посмотрел на клавиатуру / в черновик",
                                "comment": "В этот момент сверял черновик с расчетами матрицы камеры.",
                                "submitted_at": "11:52:10",
                                "teacher_comment": ""
                            }
                            updated = True

                    elif "Петров" in s_name and len(data.get("incidents", [])) >= 2:
                        inc0 = data["incidents"][0]
                        if not inc0.get("appeal"):
                            inc0["appeal"] = {
                                "status": "rejected",
                                "reason": "Ложное срабатывание (в руке был предмет, а не телефон)",
                                "comment": "В руке был калькулятор, а не смартфон.",
                                "submitted_at": "13:17:40",
                                "teacher_comment": "На фотофиксации четко виден экран смартфона с включенным мессенджером."
                            }
                            updated = True

                        inc1 = data["incidents"][1]
                        if not inc1.get("appeal"):
                            inc1["appeal"] = {
                                "status": "approved",
                                "reason": "Посмотрел на клавиатуру / в черновик",
                                "comment": "Смотрел на клавиатуру при вводе ответа.",
                                "submitted_at": "13:18:05",
                                "teacher_comment": "Одобрено. Движение взгляда соответствует набору текста на клавиатуре."
                            }
                            updated = True

                    if updated:
                        with open(s_file, "w", encoding="utf-8") as f:
                            json.dump(data, f, indent=2, ensure_ascii=False)
                except Exception as e:
                    print(f"[SessionReportManager] Error backfilling demo session: {e}")
            return

        print("[SessionReportManager] Generating demo examination sessions for teacher dashboard...")

        demo_specs = [
            {
                "name": "Смирнова Анна Сергеевна",
                "days_ago": 0,
                "hour": 10,
                "minute": 15,
                "duration_min": 9,
                "correct": 10,
                "total": 10,
                "pct": 100,
                "incidents": []
            },
            {
                "name": "Иванов Алексей Дмитриевич",
                "days_ago": 0,
                "hour": 11,
                "minute": 40,
                "duration_min": 11,
                "correct": 8,
                "total": 10,
                "pct": 80,
                "incidents": [
                    {
                        "type": "LOOKING_AWAY",
                        "offset_sec": 145,
                        "duration_sec": 1.8,
                        "desc": "Непрерывный отвод головы вправо: 1.8с (порог 1.5с)",
                        "appeal": {
                            "status": "pending",
                            "reason": "Посмотрел на клавиатуру / в черновик",
                            "comment": "В этот момент сверял черновик с расчетами матрицы камеры.",
                            "submitted_at": "11:52:10",
                            "teacher_comment": ""
                        }
                    },
                    {
                        "type": "GAZE_AWAY",
                        "offset_sec": 380,
                        "duration_sec": 1.6,
                        "desc": "Отвод взгляда от экрана влево: 1.6с (порог 1.5с)",
                        "appeal": None
                    }
                ]
            },
            {
                "name": "Петров Дмитрий Владимирович",
                "days_ago": 0,
                "hour": 13,
                "minute": 10,
                "duration_min": 6,
                "correct": 5,
                "total": 10,
                "pct": 50,
                "incidents": [
                    {
                        "type": "PHONE_DETECTED",
                        "offset_sec": 95,
                        "duration_sec": 2.3,
                        "desc": "Обнаружен смартфон в рабочей зоне (уверенность 92%)",
                        "appeal": {
                            "status": "rejected",
                            "reason": "Ложное срабатывание (в руке был предмет, а не телефон)",
                            "comment": "В руке был калькулятор, а не смартфон.",
                            "submitted_at": "13:17:40",
                            "teacher_comment": "На фотофиксации четко виден экран смартфона с включенным мессенджером."
                        }
                    },
                    {
                        "type": "LOOKING_DOWN",
                        "offset_sec": 160,
                        "duration_sec": 2.1,
                        "desc": "Взгляд опущен вниз на колени: 2.1с",
                        "appeal": {
                            "status": "approved",
                            "reason": "Посмотрел на клавиатуру / в черновик",
                            "comment": "Смотрел на клавиатуру при вводе ответа.",
                            "submitted_at": "13:18:05",
                            "teacher_comment": "Одобрено. Движение взгляда соответствует набору текста на клавиатуре."
                        }
                    },
                    {
                        "type": "FOCUS_LOST",
                        "offset_sec": 240,
                        "duration_sec": 4.5,
                        "desc": "Потеря фокуса окна: попытка переключения на стороннее приложение (Alt+Tab)",
                        "appeal": None
                    },
                    {
                        "type": "MULTIPLE_FACES",
                        "offset_sec": 310,
                        "duration_sec": 2.0,
                        "desc": "Обнаружено второе лицо в кадре (подсказчик)",
                        "appeal": None
                    }
                ]
            }
        ]

        now = datetime.now()
        for spec in demo_specs:
            start_dt = now.replace(hour=spec["hour"], minute=spec["minute"], second=0)
            end_dt = start_dt + timedelta(minutes=spec["duration_min"], seconds=24)
            spent_fmt = f"{spec['duration_min']:02d}:24"

            # Create mock incident objects
            mock_incidents = []
            for inc_data in spec["incidents"]:
                inc_time = start_dt + timedelta(seconds=inc_data["offset_sec"])
                mock_incidents.append({
                    "incident_type": inc_data["type"],
                    "severity": "CRITICAL" if inc_data["type"] in ["PHONE_DETECTED", "FOCUS_LOST", "MULTIPLE_FACES"] else "HIGH",
                    "description": inc_data["desc"],
                    "timestamp": inc_time.isoformat(),
                    "details": {"duration": inc_data["duration_sec"]},
                    "screenshot_path": "",
                    "appeal": inc_data.get("appeal", None)
                })

            session_dir = SessionReportManager.save_session(
                student_name=spec["name"],
                start_time=start_dt,
                end_time=end_dt,
                correct_count=spec["correct"],
                total_count=spec["total"],
                score_pct=spec["pct"],
                time_spent=spent_fmt,
                incidents=mock_incidents
            )

            # Generate synthetic screenshot files for the incidents so the gallery looks complete
            screenshots_dir = session_dir / "screenshots"
            summary_file = session_dir / "summary.json"
            if summary_file.exists():
                with open(summary_file, "r", encoding="utf-8") as f:
                    s_data = json.load(f)

                for inc in s_data.get("incidents", []):
                    idx = inc["id"]
                    t_type = inc["type"]
                    shot_name = f"{idx:03d}_{t_type.lower()}.jpg"
                    shot_file = screenshots_dir / shot_name

                    # Draw an illustrative proctoring frame
                    img = np.full((360, 480, 3), 35, dtype=np.uint8)
                    cv2.rectangle(img, (0, 0), (480, 360), (50, 50, 60), 2)
                    cv2.putText(img, f"PROCTOR SNAPSHOT #{idx}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (56, 189, 248), 2)
                    cv2.putText(img, f"TYPE: {t_type}", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
                    cv2.putText(img, f"TIME: {inc['time_code']} | DUR: {inc['duration_sec']}s", (20, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)

                    if t_type == "PHONE_DETECTED":
                        cv2.rectangle(img, (220, 140), (290, 270), (0, 0, 255), 2)
                        cv2.putText(img, "CELL PHONE 92%", (215, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
                    elif t_type in ["LOOKING_AWAY", "LOOKING_DOWN"]:
                        cv2.circle(img, (240, 180), 50, (0, 200, 255), 2)
                        cv2.arrowedLine(img, (240, 180), (320, 180), (0, 180, 255), 3)
                        cv2.putText(img, "HEAD DEVIATION > 38 deg", (150, 250), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 200, 255), 1)
                    elif t_type == "FOCUS_LOST":
                        cv2.putText(img, "[WINDOW FOCUS LOST]", (140, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                        cv2.putText(img, "Switched away from kiosk", (140, 210), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)
                    elif t_type == "MULTIPLE_FACES":
                        cv2.circle(img, (160, 180), 45, (0, 255, 0), 2)
                        cv2.circle(img, (320, 170), 40, (0, 0, 255), 2)
                        cv2.putText(img, "FACE #1", (140, 125), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
                        cv2.putText(img, "FACE #2 (SUSPECT)", (280, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)

                    cv2.imwrite(str(shot_file), img)
                    inc["screenshot"] = f"screenshots/{shot_name}"

                with open(summary_file, "w", encoding="utf-8") as f:
                    json.dump(s_data, f, indent=2, ensure_ascii=False)
