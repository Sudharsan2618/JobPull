"""JobPull console — service + API layer.

A thin, readable layer on top of the existing pipeline scripts. Each module in
`app/services` does ONE job; `app/routes` exposes them over HTTP; `app/server.py`
wires it together. The existing run.py / run_workday.py / analyze.py keep working
unchanged — this layer reuses config, store, pool, title_filter and the sources.
"""
