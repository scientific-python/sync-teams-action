import yaml
import requests
import argparse
import os
import json

org = "scientific-python"
members_url = f"https://api.github.com/orgs/{org}/members"
user_url = "https://api.github.com/users/"
invite_url = f"https://api.github.com/orgs/{org}/invitations"

headers = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "Authorization": f"token {os.environ['GH_TOKEN']}",
}

page = 1
existing_members = []
while page_members := (
    requests.get(members_url + f"?page={page}", headers=headers).json()
):
    if 'message' in page_members:
        print(page_members["message"])
        sys.exit(1)
    page += 1
    existing_members += page_members
existing_members = set([m["login"].lower() for m in existing_members])

desired_members = yaml.load(open("members.yaml"), Loader=yaml.SafeLoader)
desired_members = set([m.lower() for m in desired_members])

missing_members = desired_members - existing_members

for member in missing_members:
    print(f"Inviting {member}...")

    user = requests.get(user_url + member, headers=headers).json()
    if "message" in user:
        print(f"Error inviting {member}: {user['message']}")
        continue
    user_id = user["id"]

    response = requests.post(
        invite_url,
        json={"invitee_id": user_id, "role": "direct_member"},
        headers=headers
    ).json()
    if "message" in response:
        print(response["message"])
        continue

    response.raise_for_status()
