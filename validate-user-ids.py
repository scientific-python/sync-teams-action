import argparse
import json
import os
import sys
import urllib.error
import urllib.request
import yaml


def fetch_user_id(username, token):
    """Fetches the GitHub user ID for a given username."""
    url = f"https://api.github.com/users/{username}"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github.v3+json")
    req.add_header("User-Agent", "scientific-python-sync")

    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            return data["id"]
    except urllib.error.HTTPError as e:
        print(f"Error fetching {username}: {e.code} {e.reason}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error fetching {username}: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Validate GitHub user IDs in user-ids.yaml"
    )
    parser.add_argument(
        "--sync",
        action="store_true",
        help="Add missing, remove extra usernames in user-ids.yaml to match teams.yaml",
    )
    args = parser.parse_args()

    # Load teams
    try:
        with open("teams.yaml", "r") as f:
            teams = yaml.safe_load(f)
    except Exception as e:
        print(f"Failed to load teams.yaml: {e}", file=sys.stderr)
        sys.exit(1)

    all_members = {m for team in teams for m in team.get("members", [])}

    try:
        with open("user-ids.yaml", "r") as f:
            captured_user_ids = yaml.safe_load(f) or []
    except FileNotFoundError:
        captured_user_ids = []

    user_id_map = {entry["name"]: entry.get("id") for entry in captured_user_ids}

    token = os.environ.get("GH_TOKEN")
    if not token:
        print("Error: GH_TOKEN environment variable is not set.", file=sys.stderr)
        print("       Generate a token with no added roles/permissions.", file=sys.stderr)
        sys.exit(1)

    cache_file = ".user-id-cache.json"
    try:
        with open(cache_file) as f:
            cache = json.load(f)
        print(f"Loaded cache from {cache_file}.")
    except FileNotFoundError:
        cache = {}
        print(f"No cache found; will create {cache_file}.")

    # Fetch and match IDs
    fetched_ids = {}
    for username in sorted(all_members):
        if username in cache:
            fetched_ids[username] = cache[username]
        else:
            print(f"Fetching ID for {username}...")
            fetched_ids[username] = fetch_user_id(username, token)
            cache[username] = fetched_ids[username]
            with open(cache_file, "w") as f:
                json.dump(cache, f)

        current_id = user_id_map.get(username)
        if username in user_id_map and current_id != fetched_ids[username]:
            print(
                f"Error: ID for `{username}` differs! Existing: `{current_id}`, fetched: `{fetched_ids[username]}`.",
                file=sys.stderr,
            )
            print(
                "This may indicate a username was reused. Remove the user from user-ids.yaml and re-run with --sync.",
                file=sys.stderr,
            )
            sys.exit(1)

    missing_members = all_members - user_id_map.keys()
    extra_members = user_id_map.keys() - all_members

    if missing_members:
        print("The following users are in teams.yaml but missing from user-ids.yaml:")
        for m in sorted(missing_members):
            print(f"  - {m}")
    if extra_members:
        print("The following users are in user-ids.yaml but not in teams.yaml:")
        for m in sorted(extra_members):
            print(f"  - {m}")

    if args.sync:
        with open("user-ids.yaml", "w") as f:
            for username in sorted(all_members):
                if username in missing_members:
                    print(f"Adding {username}")
                f.write(f"- name: {username}\n")
                f.write(f"  id: {fetched_ids[username]}\n")
        for m in sorted(extra_members):
            print(f"Removed {m}")
        print("Successfully updated user-ids.yaml")
    else:
        if missing_members or extra_members:
            print("\nRun validate-user-ids.py --sync locally to update user-ids.yaml.", file=sys.stderr)
            sys.exit(1)
        print("Validation successful. No user IDs changed.")


if __name__ == "__main__":
    main()
