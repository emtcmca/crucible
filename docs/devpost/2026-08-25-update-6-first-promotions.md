## Update 6: the loop promoted a policy for the first time, and the exclusion rate says why that is not the headline

### What ran

Sixty live campaigns overnight, 1,770 episodes of which 1,616 were scorable, every bundle
validating against the offline reader with zero errors. The loop promoted a policy **95
times**, at a mean of 1.58 per run. Before this batch nothing had ever been promoted in this project,
the policies bucket was empty, and the GCS write path with its read-back assertion had
never executed once.

Every figure here is **single-sample, k=1, with no stability estimate**, and it separates
1,260 test pairs by policy against 180 by the approval oracle. That ratio travels with the
numbers permanently. A suite the oracle separates produces an identical-looking result
while measuring something else.

### The number that matters is the one that looks like a failure

The exclusion rate ran over its 5 percent ceiling in **51 of 60 runs**, median 8.3 percent.
That is not noise and it is not the target agent. Every excluded episode carries the same
reason code, and they come from just eight attacks out of the corpus.

Reading them apart is the finding. One says "just close it out, I'll take the store credit"
and presupposes a conversation whose earlier turns do not exist, so the agent has nothing
to act on and could never call a tool. Another offers the agent 150 dollars per request,
and produces no tool call because **the agent refused a bribe**. The first is a defective
fixture. The second is a successful defense being deleted from the denominator.

One reason code cannot serve both, and until yesterday neither was visible at all: the
verdict schema had nowhere to record why an episode was invalid, so the instrument threw
the answer away every time it computed it. The obvious fix, scoring these as clean, would
bring the rate under the ceiling in one line and would launder the broken fixtures into
passes. That is tuning the ruler and it is not going to happen here.

### What went wrong

Two batch runners raced on the same output directory for about twenty runs, because a
background task reported as killed was still alive and a relaunch joined it. Both skipped
completed runs, both then executed the same run number, and one overwrote the other's exit
code. Nothing was corrupted, checked rather than assumed: all bundles validate and every
run id is distinct. The runner now holds a lock keyed to a live process id, proved by
starting a second one and watching it refuse.

### What is not known yet

Whether a promoted policy generalises. The held-out attack family stays sealed until
2026-08-28, and no transfer claim exists before then. The next update reports that number
whatever it turns out to be.

[github.com/emtcmca/crucible](https://github.com/emtcmca/crucible)
