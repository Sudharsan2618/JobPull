"""
View stored jobs and their descriptions.

  python view.py                 -> accepted jobs, one line each
  python view.py --all           -> include rejected
  python view.py --source naukri -> filter by source
  python view.py --full          -> print full description of each job
  python view.py --title python  -> substring filter on title
"""
import argparse

from store import get_collection


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="include rejected jobs")
    ap.add_argument("--source", default=None, help="linkedin | indeed | naukri")
    ap.add_argument("--full", action="store_true", help="print full descriptions")
    ap.add_argument("--title", default=None, help="substring filter on title")
    ap.add_argument("--limit", type=int, default=50)
    args = ap.parse_args()

    query = {}
    if not args.all:
        query["accepted"] = True
    if args.source:
        query["source"] = args.source.lower()
    if args.title:
        query["title"] = {"$regex": args.title, "$options": "i"}

    client, col = get_collection()
    try:
        total = col.count_documents(query)
        print(f"{total} job(s) match {query}\n")
        for j in col.find(query).limit(args.limit):
            flag = "OK " if j.get("accepted") else "REJ"
            print(f"[{flag}][{j.get('source','?'):8s}] {j.get('title','')}  |  "
                  f"{j.get('company','')}  |  {j.get('location','')}")
            print(f"        url: {j.get('job_url','')}")
            if not j.get("accepted"):
                print(f"        reason: {j.get('rejectionReason')}")
            if j.get("experience"):
                print(f"        experience: {j.get('experience')}")
            if j.get("skills"):
                print(f"        skills: {', '.join(j['skills'][:12])}")
            desc = j.get("description") or ""
            if args.full:
                print(f"        --- description ---\n{desc}\n")
            else:
                snippet = desc.replace("\n", " ")[:180]
                if snippet:
                    print(f"        desc: {snippet}...")
            print()
    finally:
        client.close()


if __name__ == "__main__":
    main()
