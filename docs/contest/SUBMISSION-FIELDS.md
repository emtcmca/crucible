# Devpost submission fields — what to paste where

**Written 2026-08-31.** One place for the values that go into the form, so they
are not retyped from memory at 16:50 PT. Every row names where it came from.

**Everything locks 2026-08-31 17:00 PT.** After that: no repo edits, no video
replacement, no material changes, until winners are announced.

---

## The fields

| field | value | source |
|---|---|---|
| **Track** | The Fortified Enterprise Fleet | `docs/contest/CONTEST.md` §3 |
| **Google SDK used** | **ADK** | `google-adk==2.1.0`, imported and load-bearing at `crucible/plugin/adk.py:78` |
| **Project start date** | **2026-08-20** | `git log --reverse`, first commit `fc3a612` at 10:45:12 -0400. Submission period opened 08-03 |
| **Repository** | https://github.com/emtcmca/crucible | public, Apache-2.0. **No `testing@devpost.com` share needed** |
| **Video** | *(paste the YouTube link once processed)* | must be **public**, checked in an **incognito window**, **under 4:00** |
| **Architecture diagram** | `docs/diagrams/loop.svg` | upload the rendered PNG from `tools/capture/out/cards/02-architecture.png` |
| **Hosted project URL** | **see the ruling below** | |
| **Startup Excellence opt-in** | **DO NOT OPT IN** | needs an incorporated organisation and a corporate email. Solo and unaffiliated is not eligible |

## Additional links

| what | URL |
|---|---|
| LinkedIn post about the build, 2026-08-31 | https://www.linkedin.com/feed/update/urn:li:activity:7500205777584963584/ |

**On the LinkedIn link.** It belongs in an *additional links* or *supporting
material* field, not in the project story and not in a Devpost update. The story
is the record of what was built and when; a link to a post about the build is a
different kind of artifact and mixing them dilutes the thing the story is
evidence for. It is also not a substitute for anything the rules require.

---

## The hosted URL ruling

**Submit no hosted URL.** Name the browser path instead.

The Cloud Run service is `--no-allow-unauthenticated` with **zero IAM bindings**,
so a judge who opens the URL gets a 403. The rules require login credentials in
the testing instructions for a private site, and minting a credential for a
harness whose whole subject is agents holding permissions they should not is the
wrong trade for a field that is *highly encouraged* rather than mandatory.

**What to say in the testing instructions instead:**

> The project runs in a judge's own browser with no credential and no cloud
> project: the README's **Open in Cloud Shell** button runs the pure-code
> components end to end. Evidence bundles replay offline with
> `python -m crucible.replay <bundle>`, which opens no socket and reads no
> credential, enforced by an AST lint plus a test that runs the viewer with the
> environment stripped and the socket module replaced by something that raises.
> The Cloud Run service is deployed and serving under its own service account;
> it is left unauthenticated-by-default because it drives a paid model behind a
> budget alert that stops nothing, and the demo video shows it live instead.

Full reasoning: `docs/contest/AUDIT-stage-one-2026-08-30.md`, Row 8.

---

## Before you submit

- [ ] Video **public**, verified in an **incognito window**, **under 4:00**
- [ ] Video shows the backend on Google Cloud — that is the N6a terminal beat
- [ ] `git status --porcelain` empty, and `origin/main` current
- [ ] `python scripts/pre-read-seal-proof.py` prints **VERDICT PASS**
- [ ] `python scripts/contract-check.py` prints **ALL PASSES OK**
- [ ] Update 10 posted
- [ ] Project story updated — the transfer section says there is no transfer result

**Nothing may be torn down before 2026-10-01.** Availability runs through the
Judging Period, not to the submission deadline.
