# Campus Delivery Planner

A small website that uses Prolog to plan package deliveries. The robot starts at the mailroom and carries one package at a time. SQLite stores the campus locations, roads, and packages.

## Run

Requires Python 3 and [SWI-Prolog](https://www.swi-prolog.org/). In this folder, run:

```sh
python3 server.py
```

Open **http://localhost:8000** in your browser. Press **Ctrl+C** in the terminal to stop the server.

## Demo

1. Click **Find plan**, then **Play** or **Next step** to follow the robot.
2. Turn off the mailroom–library road and find a new plan.
3. Turn off both roads to the lab and find a plan to see an unreachable delivery.
4. Turn roads back on or add a package with a pickup and destination.

Road and package changes are saved in `campus.db`. To restore the original setup, stop the server, delete `campus.db`, and start it again.

Prolog uses breadth-first search to find a shortest sequence of legal actions. This is symbolic AI planning, not machine learning. Inspired by [Planning container shipping using Prolog](https://quantumprolog.sgml.net/container-planning-demo/part1.html).

The original terminal demo is also available: run `swipl -s prolog/planner.pl` and enter `demo(normal).`, `demo(detour).`, or `demo(disconnected).` at the prompt.

## Project files

```text
📁 cosc631-week9/
├── 🐍 server.py                  # Web server and SQLite storage
├── 🗄️ campus.db                 # Created on first run (not committed)
├── 📁 prolog/
│   └── 🧩 planner.pl            # Delivery planning logic
├── 📁 web/
│   ├── 🌐 index.html            # Page layout
│   ├── 📜 app.js                # Page behavior
│   ├── 🎨 style.css             # Page styling
│   └── 📁 vendor/
│       ├── 📜 alpine.min.js     # Alpine.js library
│       └── 📄 ALPINE-LICENSE.md  # Alpine.js license
├── ⚙️ .gitignore
└── 📝 README.md
```
