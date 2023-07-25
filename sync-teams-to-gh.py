"""
Requires classic token with permissions "Repo" and "Admin"
"""

import yaml
import requests
import argparse
import os
import json
import argparse
import functools
import sys


org = "scientific-python"
api = "https://api.github.com"

headers = {
    "Accept": "application/vnd.github+json",
    "Accept": "application/vnd.github.v3.repository+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "Authorization": f"token {os.environ['GH_TOKEN']}",
}

parser = argparse.ArgumentParser()
parser.add_argument(
    '-n', '--dry-run',
    action='store_true'
)
parser.add_argument(
    '-m', '--membership',
    action='store_true', help="Print current team membership/permissions as YAML"
)
parser.add_argument(
    '-q', '--quiet',
    action='store_true', help='Suppress HTTP method output'
)
args = parser.parse_args()


if args.membership:
    args.quiet = True


DARK_GRAY = "\033[1;90m"
RESET = "\033[0m"


def qprint(*pargs, **kwargs):
    if not args.quiet:
        print(*pargs, **kwargs)


def get(url, fail_ok=False):
    """Get with paging.
    """
    if url.startswith('/'):
        url = api + url

    page = 1
    more_pages = True
    while more_pages:
        if page == 1:
            qprint(f'{DARK_GRAY}GET {url}{RESET}')
        else:
            qprint(f'{DARK_GRAY}GET {url} [{page}]{RESET}')

        r = requests.get(url + f"?page={page}", headers=headers)

        try:
            data = r.json()
        except json.decoder.JSONDecodeError:
            qprint("Error: cannot decode JSON response")
            sys.exit(1)

        if fail_ok and "message" in data:
            data["status"] = r.status_code
            return data

        if "message" in data:
            qprint(f"Error retrieving {url}: {data['message']}")
            sys.exit(1)

        if "next" in r.links:
            page += 1
        else:
            more_pages = False

    return data


def http_method(url, data={}, method=None):
    request_method = getattr(requests, method.lower())

    if method is None:
        raise RuntimeError("Need HTTP method")

    if url.startswith('/'):
        url = api + url

    if not args.dry_run:
        qprint(f'{DARK_GRAY}{method} {url}{RESET}')
        r = request_method(url, headers=headers, json=data)
        try:
            data = r.json()
        except json.decoder.JSONDecodeError:
            return {}

        if "message" in data:
            qprint(f"Error retrieving {url}: {data['message']}")
            sys.exit(1)

    else:
        qprint(f'Dry run: {method} [{url}]')


post = functools.partial(http_method, method='POST')
patch = functools.partial(http_method, method='PATCH')
put = functools.partial(http_method, method='PUT')
delete = functools.partial(http_method, method='DELETE')

config = yaml.load(open("teams.yaml"), Loader=yaml.SafeLoader)
config = {team["name"]: team for team in config}

gh_teams = {team["name"]: team for team in get(f"/orgs/{org}/teams")}


if args.membership:
    out = []

    for team, data in list(gh_teams.items()):
        team_slug = data['slug']
        members = {
            member["login"]
            for member in get(f"/orgs/{org}/teams/{team_slug}/members")
        }

        gh_repos = get(f"/orgs/{org}/teams/{team_slug}/repos")
        permissions = [
            {'repo': repo['name'], 'role': repo['role_name']}
            for repo in gh_repos
        ]

        t = {
            'name' : team,
            'description': data['description'],
            'members': list(members)
        }
        if permissions:
            t['permissions'] = permissions

        out.append(t)

    for team in out:
        print(yaml.dump([team], sort_keys=False))

    sys.exit()


desired_teams = set(config)
existing_teams = set(gh_teams)
missing_teams = desired_teams - existing_teams


for team in missing_teams:
    team_info = config[team]

    qprint(f"Creating `{team}` team")
    post(
        f"/orgs/{org}/teams",
        {
            "name": team_info["name"],
            "description": team_info["description"],
            "privacy": "closed"
        }
    )

if missing_teams:
    # Refetch teams list
    gh_teams = {team["name"]: team for team in get(f"/orgs/{org}/teams")}


for team in config.values():
    name = team["name"]
    gh_team = gh_teams[team["name"]]
    team_slug = gh_team["slug"]

    # Detect and patch differences between config file team and GH team
    # Currently, only description.
    config_description = team.get("description")
    if (config_description and
        (config_description != gh_team["description"])):

        qprint(f"Updating `{team_slug}` description to `{config_description}`")
        patch(
            f"/orgs/{org}/teams/{team_slug}",
            {"description": config_description}
        )

    members = {
        member["login"]
        for member in get(f"/orgs/{org}/teams/{team_slug}/members")
    }
    members_added = set(team["members"]) - members
    members_removed = members - set(team["members"])

    for username in members_added:
        qprint(f"Adding `{username}` to `{team_slug}`")
        put(
            f"/orgs/{org}/teams/{team_slug}/memberships/{username}",
            {"role": "member"}
        )

    for username in members_removed:
        qprint(f"Removing `{username}` from `{team_slug}`")
        delete(f"/orgs/{org}/teams/{team_slug}/memberships/{username}")

    for repo_role in team.get("permissions", []):
        repo = repo_role["repo"]
        role = repo_role["role"]
        owner = "scientific-python"

        response = get(
            f"/orgs/{org}/teams/{team_slug}/repos/{owner}/{repo}",
            fail_ok=True
        )
        gh_role = response.get("role_name")

        if gh_role != role:
            if role is None:
                qprint(f"Revoking `{team_slug}` access from repo `{owner}/{repo}`")
                delete(f"/orgs/{org}/teams/{team_slug}/repos/{owner}/{repo}")
            else:
                qprint(f"Changing `{team_slug}` role from `{gh_role}` to `{role}` on `{owner}/{repo}`")
                put(
                    f"/orgs/{org}/teams/{team_slug}/repos/{owner}/{repo}",
                    {"permission": role}
                )