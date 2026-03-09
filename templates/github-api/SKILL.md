# github-api

A SkillForge skill for searching and managing GitHub pull requests, issues, and repositories.

## Tools

### search_pull_requests
Search GitHub pull requests by state, assignee, label, and repository.

**Parameters:**
- `query` (string, required): Search query string
- `state` (string, optional): "open", "closed", or "all" (default: "open")
- `assignee` (string, optional): GitHub username or "@me"
- `repo` (string, optional): "owner/repo" filter

### get_issue
Retrieve a specific GitHub issue by number.

**Parameters:**
- `repo` (string, required): "owner/repo"
- `issue_number` (integer, required): Issue number

## Permissions
- network: api.github.com
- env: GITHUB_TOKEN

## Examples
- "find my open PRs" → search_pull_requests(state="open", assignee="@me")
- "show issues in myorg/myrepo" → search_pull_requests(repo="myorg/myrepo")
