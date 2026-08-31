# Uploading the demo video to YouTube

**You are free to upload now.** The video is built, verified and will not change
again unless you ask for a change. Nothing downstream is waiting on it, and
YouTube processing runs from minutes to hours, so the sooner it is up the more
slack you have before 17:00 PT.

**One thing first: watch this build.** The cut changed after you last viewed it
— the audio lead-in trim and the outro card both landed since. Sixty seconds of
skimming beats discovering a problem after the deadline locks.

```
tools\capture\out\crucible.mp4     204.8s (3:24.8)  1920x1080  -13.4 LUFS
```

---

## The safe order

Upload **unlisted** first, check it, then flip to **public**. YouTube's
processing can change how a file looks and sounds, and unlisted lets you see the
processed version before anyone else can.

### 1. Upload

youtube.com → **Create → Upload videos** → pick `crucible.mp4`.

### 2. Details

Title and description are below, ready to paste.

| setting | value | why |
|---|---|---|
| **Audience** | **"No, it's not made for kids"** | required, and the wrong answer disables embedding, which is how Devpost shows the video on your project page |
| **Age restriction** | none | an age-restricted video will not embed |
| **Category** (Show more) | Science & Technology | |
| **Visibility** | **Unlisted for now** | flip to Public in step 4 |

### 3. Check the processed version

Wait for processing to finish, then watch it on YouTube, not locally:

- **Does the audio play?** A container-level defect got past a local check once
  in this project already.
- **Is 1080p offered** in the quality menu? If only 360p is there, processing is
  not finished.
- **Is the terminal text readable** at 1080p in the N6a beat? That beat is the
  contest's proof the backend runs on Google Cloud, and it is sped 1.75x.

### 4. Go public and verify

Flip Visibility to **Public**, then open the link in an **incognito window**.

**The organiser's checklist names this step specifically.** An unlisted or
private video is a submission a judge cannot watch, and you will not find that
out from your own browser, which is signed in as you.

### 5. Paste the link into Devpost

The **Video demo link** field, which is required. `https://youtu.be/<id>` or the
full watch URL both work.

---

## Title

```
CRUCIBLE: break the agent, ship the policy
```

## Description

```
CRUCIBLE is a pre-deployment hardening harness for AI agents that hold real
permissions. A red-team model attacks a target agent, a pure-code tripwire
rules on what the agent actually CALLED rather than on anything it said, a
Coroner writes the autopsy and structurally cannot propose a fix, and an
Armorer compiles a patch in a three-verb policy language with no allow verb.
A pure-code gate then refuses to promote a fix it cannot prove.

Built for the Google Cloud "All Things Agentic" hackathon, track: The
Fortified Enterprise Fleet.

Run it yourself in your browser, no credential and no cloud project:
https://shell.cloud.google.com/cloudshell/editor?cloudshell_git_repo=https://github.com/emtcmca/crucible&cloudshell_git_branch=main&cloudshell_tutorial=docs/cloudshell-tutorial.md

Source, Apache-2.0:
https://github.com/emtcmca/crucible

Built on Google Cloud: Vertex AI (Gemini 3.7-flash, 3.6-flash,
3.5-flash-lite), Vertex Model Garden (managed Gemma), Cloud Run, Cloud
Storage, Cloud IAM, Cloud Logging, Cloud Build, Artifact Registry, Cloud
Trace. Agent Development Kit 2.1.0, with enforcement at the before_tool
callback.

What this is not: eleven days, one person, one target agent. No users. Not
reviewed, endorsed, or responded to by Google in any way. Every figure is
single-sample, k=1, with no stability estimate. A held-out attack family
exists and is still sealed, so no transfer result is claimed. The repository
says all of this on its own front page, in a section called "what is not
defensible today".
```

---

## After it is public

**Do not replace or re-edit the video after 17:00 PT.** The organiser's
checklist is explicit: everything locks at the deadline, and material changes
before winners are announced can raise an eligibility question. If you spot
something afterwards, leave it.
