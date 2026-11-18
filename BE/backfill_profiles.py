"""
One-time backfill: set `profiles` on every stored job from its title, so the
track-filtered API works over existing data. Idempotent — safe to re-run.

    cd BE && .venv/Scripts/python.exe backfill_profiles.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pymongo import MongoClient, UpdateOne

import config
from title_filter import profiles_for


def main():
    client = MongoClient(config.MONGODB_URI, serverSelectionTimeoutMS=8000)
    col = client[config.DB_NAME][config.JOBS_COLLECTION]

    ops, n = [], 0
    for d in col.find({}, {"title": 1}):
        ops.append(UpdateOne({"_id": d["_id"]},
                             {"$set": {"profiles": profiles_for(d.get("title", ""))}}))
        if len(ops) >= 1000:
            col.bulk_write(ops, ordered=False); n += len(ops); ops = []
    if ops:
        col.bulk_write(ops, ordered=False); n += len(ops)

    genai = col.count_documents({"profiles": "genai"})
    fresher = col.count_documents({"profiles": "fresher"})
    print(f"backfilled profiles on {n} jobs")
    print(f"  profiles contains 'genai'   : {genai}")
    print(f"  profiles contains 'fresher' : {fresher}")
    client.close()


if __name__ == "__main__":
    main()
