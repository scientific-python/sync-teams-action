# Synchronize team membership / permissions

This actions reads in a `teams.yaml` file which specifies team
membership and permission.  It then synchronizes that with GitHub,
making changes as necessary.

Note that it only touches teams that are specified in the
`teams.yaml`. In other words, if a team is deleted from the YAML file,
the synchronization script won't do anything about it (it has no
knowledge of history).

## Using the action

In the repository that contains your `teams.yaml`, add `.github/workflows/sync-teams.yaml`:

```
name: Teams
on:
  push:
    branches:
      - main

jobs:
  sync_teams:
    name: Sync
    runs-on: ubuntu-latest
    steps:
      - name: Checkout teams list
        uses: actions/checkout@v3
        with:
          ref: main

      - uses: scientific-python/sync-teams-action@main
        with:
          token: ${{ secrets.SYNC_TEAMS_TOKEN }}
```

You will also need to set `SYNC_TEAMS_TOKEN` as a repository secret.
See the [token](#token) section below.

## `teams.yaml` format

```yaml
- name: SPEC Steering Committee
  description:
  members:
    - stefanv
    ...
  permissions:
    - repo: specs
      role: maintain

- name: Community Managers
  description: Scientific Python Community Managers
  members:
    - stefanv
    ...
  permissions:
    - repo: specs
      role: triage
```

## Token

The script requires a classic token with `org` and `admin` permissions, exported as a `GH_TOKEN` environment variable.

A token can be created at:

https://github.com/settings/tokens/new

## Initial creation of `teams.yaml`

Existing team membership can be downloaded from GitHub using:

```
sync-teams-to-gh.py --download > teams.yaml
```

## Revoking team access from repo

Set `role` to None:

```
  permissions:
    - repo: myrepo
      role:
```
