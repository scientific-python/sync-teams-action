# Synchronize team membership / permissions

## `teams.yaml`

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

## Revoking team access from repo

Set `role` to None:

```
  permissions:
    - repo: myrepo
      role:
```