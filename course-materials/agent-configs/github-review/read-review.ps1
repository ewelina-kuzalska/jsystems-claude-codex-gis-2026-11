# Read-only public-course review collection. Uses the caller's existing gh auth.
param(
    [Parameter(Mandatory = $true)]
    [ValidateRange(1, 2147483647)]
    [int]$PrNumber
)
$ErrorActionPreference = 'Stop'
$upstream = 'LucasMatuszewski/jsystems-claude-codex-gis-2026-11'
gh pr view $PrNumber --repo $upstream --json number,url,headRefOid,headRefName,baseRefName
if ($LASTEXITCODE -ne 0) { throw 'Could not read upstream PR metadata.' }
foreach ($endpoint in @(
    "repos/$upstream/pulls/$PrNumber/reviews",
    "repos/$upstream/pulls/$PrNumber/comments",
    "repos/$upstream/issues/$PrNumber/comments"
)) {
    gh api --method GET --paginate $endpoint
    if ($LASTEXITCODE -ne 0) { throw "Could not read $endpoint" }
}
