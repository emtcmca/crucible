# The "Open in Cloud Shell" button: the URL, and the two ways it 404s

**This file is the single source for that URL.** Copy the snippet, never retype the
URL. It carries two parameters that are easy to drop and expensive to drop, and both
have already been dropped once in this repository.

Sibling of `docs/cloudshell-tutorial.md`, which is the guided pane the button opens.
Deliberately **not** moved into a `docs/cloudshell/` directory: the tutorial path is
baked into the URL below, into `README.md`, and into anything a judge has already
opened, and a second copy at a second path is a second source of truth.

---

## The snippet

```markdown
[![Open in Cloud Shell](https://gstatic.com/cloudssh/images/open-btn.svg)](https://shell.cloud.google.com/cloudshell/editor?cloudshell_git_repo=https://github.com/emtcmca/crucible&cloudshell_git_branch=main&cloudshell_tutorial=docs/cloudshell-tutorial.md)
```

## The URL on its own, for pasting into a browser

```
https://shell.cloud.google.com/cloudshell/editor?cloudshell_git_repo=https://github.com/emtcmca/crucible&cloudshell_git_branch=main&cloudshell_tutorial=docs/cloudshell-tutorial.md
```

## What each parameter does

| Parameter | Value | Why it is there |
|---|---|---|
| *(path)* | `/cloudshell/editor` | The documented path. **Not `/cloudshell/open`.** |
| `cloudshell_git_repo` | `https://github.com/emtcmca/crucible` | Required. The repo to clone. |
| `cloudshell_git_branch` | `main` | **Optional in Google's docs, mandatory for us.** See below. |
| `cloudshell_tutorial` | `docs/cloudshell-tutorial.md` | Path *within the repo* to the Markdown rendered in the guided pane. |

No other parameter is set. `cloudshell_workspace`, `cloudshell_open_in_editor`,
`cloudshell_print`, `cloudshell_image`, `ephemeral` and `show` all exist and are all
omitted on purpose: every parameter is another thing that can be wrong in a link a
judge opens once, and none of them buys anything the tutorial pane does not already do.

## The two failure modes, both already committed once

**1. `cloudshell_git_branch` defaults to `master`.** Google's documentation, read
2026-08-25: *"Branch from the Git repository to clone. Only applicable when
`cloudshell_git_repo` is specified. **The default branch is master.**"* This repository
has no `master`: `git ls-remote --symref origin HEAD` returned
`ref: refs/heads/main HEAD` on 2026-08-25. Omit the parameter and the clone fails, on
2026-08-25, against a branch that does not exist, and **the judge finds that, not us.**

**2. The path is `/cloudshell/editor`.** Google's own example, verbatim:
`https://shell.cloud.google.com/cloudshell/editor?cloudshell_git_repo=http://path-to-repo/sample.git`

Both were verified against `docs.cloud.google.com/shell/docs/open-in-cloud-shell` on
2026-08-22 and again on 2026-08-25. The 2026-08-22 lane recorded both findings in its
commit message and then **shipped a badge with neither of them applied**. `README.md`
line 13 has carried `/cloudshell/open` with no `cloudshell_git_branch` since
2026-08-22. Recording a gotcha is not applying it.

## What it costs the judge

Nothing, and the tutorial says so on its first screen. Cloud Shell's free tier, from
`docs.cloud.google.com/shell/docs/quotas-limits` read 2026-08-25: **50 hours per week**,
**5 GB** of persistent `$HOME`, sessions **terminate after 40 minutes** non-interactive
and are **capped at 12 hours**. The judge authenticates as themselves, so no credential
of ours is shipped into a browser, which was the entire objection to a browser sandbox
for a project whose subject is agents holding permissions they should not.

The tutorial runs **only zero-model-call components**. It does not run the loop. The
loop needs Vertex AI against the judge's own billing, and a tutorial step that spends a
stranger's money is worse than no step.

## Verification status

**The URL string is UNVERIFIED-PENDING-OPEN.** Its path, its parameter names and the
branch default are all verified against Google's live documentation on 2026-08-25, and
the branch value is verified against `origin/HEAD`. **Nobody has opened it.** A URL that
parses is not a URL that resolves.

To settle it, a human opens the URL above in a browser signed in to any Google account
and confirms three things:

1. Cloud Shell provisions and the terminal lands inside a clone of this repository.
2. `git rev-parse --abbrev-ref HEAD` inside that clone prints `main`.
3. The guided tutorial pane opens on the right showing **"CRUCIBLE — see it work in
   five minutes"**, with six steps.

If step 3 shows a raw file or an empty pane, `cloudshell_tutorial` is resolving wrong
and the path in it is the thing to check first.
