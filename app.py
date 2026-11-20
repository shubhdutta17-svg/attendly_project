"""Attendly: a small attendance site using Python's built-in WSGI server."""

from datetime import date, datetime
from html import escape
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import parse_qs
import json
import os
import secrets

ROOT = Path(__file__).parent
PUBLIC = ROOT
DATA_FILE = ROOT / "attendance.json"
TEACHER_USERNAME = "teacher"
TEACHER_PASSWORD = "teach123"
SESSIONS = set()

STUDENTS = [
    {"id": "STU-101", "name": "Aarav Sharma"},
    {"id": "STU-102", "name": "Mira Patel"},
    {"id": "STU-103", "name": "Kabir Singh"},
    {"id": "STU-104", "name": "Ananya Rao"},
    {"id": "STU-105", "name": "Dev Mehta"},
    {"id": "STU-106", "name": "Isha Kapoor"},
    {"id": "STU-107", "name": "Rohan Das"},
    {"id": "STU-108", "name": "Sana Khan"},
    {"id": "STU-109", "name": "Vihaan Joshi"},
    {"id": "STU-110", "name": "Nisha Verma"},
]
VALID_STATUSES = {"Present", "Absent", "Late", "Not marked"}


def read_records():
    """Load attendance saved in JSON. Start empty on the first run."""
    if not DATA_FILE.exists():
        return {}
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_records(records):
    DATA_FILE.write_text(json.dumps(records, indent=2), encoding="utf-8")


def valid_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date().isoformat()
    except (TypeError, ValueError):
        return date.today().isoformat()


def template(filename):
    return (PUBLIC / filename).read_text(encoding="utf-8")


def login_page(error=""):
    page = template("index.html").replace("{{PAGE}}", "login")
    page = page.replace("{{CONTENT}}", template("login.html"))
    return page.replace("{{ERROR}}", escape(error))


def student_rows(attendance):
    rows = []
    for student in STUDENTS:
        student_id = student["id"]
        selected = attendance.get(student_id, "Not marked")
        options = "".join(
            f'<option value="{status}"{" selected" if selected == status else ""}>{status}</option>'
            for status in ("Not marked", "Present", "Absent", "Late")
        )
        name = escape(student["name"])
        rows.append(
            "<tr>"
            f'<td><span class="student-name">{name}</span></td>'
            f'<td><span class="student-id">{student_id}</span></td>'
            f'<td><label class="sr-only" for="{student_id}">Attendance for {name}</label>'
            f'<select id="{student_id}" name="{student_id}">{options}</select></td>'
            "</tr>"
        )
    return "\n".join(rows)


def dashboard_page(chosen_date, attendance, saved=False):
    present = sum(value == "Present" for value in attendance.values())
    absent = sum(value == "Absent" for value in attendance.values())
    late = sum(value == "Late" for value in attendance.values())
    marked = present + absent + late
    rate = round((present + late) * 100 / marked) if marked else 0
    page = template("index.html").replace("{{PAGE}}", "dashboard")
    content = template("dashboard.html")
    values = {
        "{{DATE}}": escape(chosen_date),
        "{{DATE_LABEL}}": date.fromisoformat(chosen_date).strftime("%A, %d %B %Y"),
        "{{STUDENT_ROWS}}": student_rows(attendance),
        "{{TOTAL}}": str(len(STUDENTS)),
        "{{PRESENT}}": str(present),
        "{{ABSENT}}": str(absent),
        "{{LATE}}": str(late),
        "{{RATE}}": str(rate),
        "{{MESSAGE}}": "Attendance saved successfully." if saved else "",
    }
    for marker, value in values.items():
        content = content.replace(marker, value)
    return page.replace("{{CONTENT}}", content).replace("{{ERROR}}", "")


def response(start_response, status, body, content_type="text/html; charset=utf-8", extra_headers=None):
    content = body.encode("utf-8")
    headers = [("Content-Type", content_type), ("Content-Length", str(len(content))), ("X-Content-Type-Options", "nosniff")]
    if extra_headers:
        headers.extend(extra_headers)
    start_response(status, headers)
    return [content]


def application(environ, start_response):
    """The WSGI app function used both locally and by PythonAnywhere."""
    method = environ.get("REQUEST_METHOD", "GET")
    path = environ.get("PATH_INFO", "/")
    session_cookie = SimpleCookie(environ.get("HTTP_COOKIE", ""))
    cookie = session_cookie.get("attendly_session")
    session_id = cookie.value if cookie else ""
    is_logged_in = session_id in SESSIONS

    if method == "GET" and path == "/styles.css":
        try:
            return response(start_response, "200 OK", template("styles.css"), "text/css; charset=utf-8")
        except OSError:
            return response(start_response, "404 Not Found", "Stylesheet not found", "text/plain; charset=utf-8")

    form = {}
    if method == "POST":
        try:
            length = min(int(environ.get("CONTENT_LENGTH") or 0), 100_000)
            raw = environ["wsgi.input"].read(length).decode("utf-8")
            form = parse_qs(raw, keep_blank_values=True)
        except (ValueError, UnicodeDecodeError):
            return response(start_response, "400 Bad Request", "Invalid form data", "text/plain; charset=utf-8")

    if method == "POST" and path == "/login":
        username = form.get("username", [""])[0].strip().lower()
        password = form.get("password", [""])[0]
        if username == TEACHER_USERNAME and password == TEACHER_PASSWORD:
            new_session = secrets.token_urlsafe(24)
            SESSIONS.add(new_session)
            secure = "; Secure" if environ.get("wsgi.url_scheme") == "https" else ""
            cookie_header = f"attendly_session={new_session}; HttpOnly; SameSite=Lax; Path=/{secure}"
            return response(start_response, "303 See Other", "", extra_headers=[("Location", "/"), ("Set-Cookie", cookie_header)])
        return response(start_response, "401 Unauthorized", login_page("Username or password is incorrect. Please try again."))

    if not is_logged_in:
        return response(start_response, "200 OK", login_page())

    if method == "POST" and path == "/logout":
        SESSIONS.discard(session_id)
        expired = "attendly_session=; HttpOnly; SameSite=Lax; Path=/; Max-Age=0"
        return response(start_response, "303 See Other", "", extra_headers=[("Location", "/"), ("Set-Cookie", expired)])

    if method == "POST" and path == "/attendance":
        chosen_date = valid_date(form.get("date", [""])[0])
        attendance = {}
        for student in STUDENTS:
            student_id = student["id"]
            status = form.get(student_id, ["Not marked"])[0]
            attendance[student_id] = status if status in VALID_STATUSES else "Not marked"
        records = read_records()
        records[chosen_date] = attendance
        try:
            save_records(records)
        except OSError:
            return response(start_response, "500 Internal Server Error", "Could not save attendance. Check folder permissions.", "text/plain; charset=utf-8")
        return response(start_response, "303 See Other", "", extra_headers=[("Location", f"/?date={chosen_date}&saved=1")])

    if method == "GET" and path == "/":
        query = parse_qs(environ.get("QUERY_STRING", ""))
        chosen_date = valid_date(query.get("date", [date.today().isoformat()])[0])
        attendance = read_records().get(chosen_date, {})
        saved = query.get("saved", [""])[0] == "1"
        return response(start_response, "200 OK", dashboard_page(chosen_date, attendance, saved))

    return response(start_response, "404 Not Found", "Page not found", "text/plain; charset=utf-8")


if __name__ == "__main__":
    from wsgiref.simple_server import make_server

    host = "0.0.0.0"
    port = int(os.environ.get("PORT", "8000"))
    print(f"Attendly is running on {host}:{port}")
    print("Demo login: teacher / teach123")
    make_server(host, port, application).serve_forever()
