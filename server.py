#!/usr/bin/env python3
"""Local web server and SQLite storage for the Prolog delivery planner."""

import json
import sqlite3
import subprocess
from contextlib import closing
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
DB = ROOT / "campus.db"
WEB = ROOT / "web"


def connect():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def initialize():
    with closing(connect()) as db, db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS locations (name TEXT PRIMARY KEY);
        CREATE TABLE IF NOT EXISTS roads (
            id INTEGER PRIMARY KEY, origin TEXT NOT NULL REFERENCES locations(name),
            destination TEXT NOT NULL REFERENCES locations(name),
            open INTEGER NOT NULL DEFAULT 1 CHECK (open IN (0, 1)),
            UNIQUE(origin, destination));
        CREATE TABLE IF NOT EXISTS packages (
            id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE,
            origin TEXT NOT NULL REFERENCES locations(name),
            destination TEXT NOT NULL REFERENCES locations(name),
            CHECK (origin != destination));
        """)
        if not db.execute("SELECT 1 FROM locations LIMIT 1").fetchone():
            db.executemany(
                "INSERT INTO locations VALUES (?)",
                [(x,) for x in ("mailroom", "library", "cafeteria", "lab")],
            )
            db.executemany(
                "INSERT INTO roads(origin, destination) VALUES (?, ?)",
                [
                    ("mailroom", "library"),
                    ("mailroom", "cafeteria"),
                    ("library", "lab"),
                    ("cafeteria", "lab"),
                ],
            )
            db.executemany(
                "INSERT INTO packages(name, origin, destination) VALUES (?, ?, ?)",
                [("books", "mailroom", "library"), ("lab supplies", "mailroom", "lab")],
            )


def snapshot(db):
    return {
        "locations": [
            r["name"] for r in db.execute("SELECT name FROM locations ORDER BY name")
        ],
        "roads": [dict(r) for r in db.execute("SELECT * FROM roads ORDER BY id")],
        "packages": [dict(r) for r in db.execute("SELECT * FROM packages ORDER BY id")],
    }


def make_plan(db):
    campus = snapshot(db)
    payload = {
        "roads": [
            {"from": road["origin"], "to": road["destination"]}
            for road in campus["roads"]
            if road["open"]
        ],
        "packages": [
            {
                "name": package["name"],
                "start": package["origin"],
                "destination": package["destination"],
            }
            for package in campus["packages"]
        ],
    }
    result = subprocess.run(
        [
            "swipl",
            "-q",
            "-s",
            str(ROOT / "prolog" / "planner.pl"),
            "-g",
            "web_plan",
            "-t",
            "halt",
        ],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        timeout=15,
        check=True,
    )
    return json.loads(result.stdout)


def update_road(db, data):
    if type(data.get("id")) is not int or type(data.get("open")) is not bool:
        raise ValueError("Invalid road.")
    result = db.execute(
        "UPDATE roads SET open = ? WHERE id = ?", (data["open"], data["id"])
    )
    if not result.rowcount:
        raise ValueError("Road not found.")


def add_package(db, data):
    name = data.get("name", "")
    if not isinstance(name, str):
        raise ValueError("Invalid package name.")
    name = name.strip()
    if not name or len(name) > 40 or name == "none":
        raise ValueError(
            "Enter a package name (up to 40 characters, excluding 'none')."
        )
    db.execute(
        "INSERT INTO packages(name, origin, destination) VALUES (?, ?, ?)",
        (name, data.get("origin"), data.get("destination")),
    )


def delete_package(db, data):
    package_id = data.get("id")
    if type(package_id) is not int:
        raise ValueError("Package not found.")
    result = db.execute("DELETE FROM packages WHERE id = ?", (package_id,))
    if not result.rowcount:
        raise ValueError("Package not found.")


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB), **kwargs)

    def reply(self, status, data):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if urlparse(self.path).path == "/api/data":
            with closing(connect()) as db:
                self.reply(200, snapshot(db))
        else:
            super().do_GET()

    def do_POST(self):
        handlers = {
            "/api/road": update_road,
            "/api/package": add_package,
            "/api/delete-package": delete_package,
        }
        path = urlparse(self.path).path
        if path not in handlers and path != "/api/plan":
            self.reply(404, {"error": "Not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 0 or length > 10000:
                raise ValueError("Invalid request size.")
            data = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(data, dict):
                raise ValueError("Invalid request.")

            with closing(connect()) as db, db:
                if path == "/api/plan":
                    result = make_plan(db)
                else:
                    handlers[path](db, data)
                    result = {"ok": True}
            self.reply(200, result)
        except sqlite3.IntegrityError:
            self.reply(
                400, {"error": "Invalid input. Check package name and locations."}
            )
        except (ValueError, TypeError) as error:
            self.reply(400, {"error": str(error)})
        except (OSError, subprocess.SubprocessError):
            self.reply(
                500,
                {
                    "error": "Could not run the Prolog planner. Check that SWI-Prolog is installed."
                },
            )


if __name__ == "__main__":
    initialize()
    print("Open http://localhost:8000 (press Ctrl+C to stop)", flush=True)
    ThreadingHTTPServer(("127.0.0.1", 8000), Handler).serve_forever()
