import yaml
import requests
import argparse
import os

org = "scientific-python"
members_url = f"https://api.github.com/orgs/{org}/members"
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
        raise RuntimeError(page_members["message"])
    print(f"Fetched page {page}")
    page += 1
    existing_members += page_members
existing_members = set([m["login"].lower() for m in existing_members])

desired_members = yaml.load(open("member.yaml"), Loader=yaml.SafeLoader)
desired_members = set([m.lower() for m in desired_members])

missing_members = desired_members - existing_members

for member in missing_members:
    response = requests.post(
        invite_url,
        data={"invitee_id": member, "role": "direct_member"},
        headers=headers
    )
    if "message" in response:
        raise RuntimeError(response["message"])
    response.raise_for_status()
