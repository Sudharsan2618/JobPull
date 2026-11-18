"""Mongo access for the console: collections, created lazily, with the indexes
the API's hot queries rely on.

  jobs      — the job-pull-simple.jobs pool (now carries a `profiles` array)
  companies — the connector registry the UI manages
  runs      — one document per pipeline run (Schedules/Runs screen)
  users     — one document per signed-in user (Auth0 sub + chosen track)
"""
from pymongo import MongoClient, ASCENDING, DESCENDING

import config

_client = None
_dbh = None


def db():
    global _client, _dbh
    if _dbh is None:
        if not config.MONGODB_URI:
            raise ValueError("MONGODB_URI not set in JobPull/.env")
        _client = MongoClient(config.MONGODB_URI, serverSelectionTimeoutMS=8000)
        _client.admin.command("ping")
        _dbh = _client[config.DB_NAME]
        _ensure_indexes(_dbh)
    return _dbh


def _ensure_indexes(h):
    jc = h[config.JOBS_COLLECTION]
    # Hot query: a track's matched jobs, newest first.
    jc.create_index([("profiles", ASCENDING), ("lastSeenAt", DESCENDING)], name="idx_profiles_seen")
    jc.create_index([("accepted", ASCENDING), ("lastSeenAt", DESCENDING)], name="idx_acc_seen")
    jc.create_index([("source", ASCENDING)], name="idx_source")
    # Analytics buckets scan by createdAt.
    jc.create_index([("createdAt", DESCENDING)], name="idx_created")
    h["companies"].create_index([("name", ASCENDING)], unique=True, name="idx_co_name")
    h["runs"].create_index([("startedAt", DESCENDING)], name="idx_run_started")
    h["users"].create_index([("sub", ASCENDING)], unique=True, name="idx_user_sub")


def jobs():
    return db()[config.JOBS_COLLECTION]


def companies():
    return db()["companies"]


def runs():
    return db()["runs"]


def users():
    return db()["users"]


def close():
    global _client, _dbh
    if _client is not None:
        _client.close()
    _client = None
    _dbh = None
