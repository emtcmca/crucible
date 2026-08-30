#!/usr/bin/env python3
"""Walk the adjudication gate against a STAND-IN family. Costs nothing, spends nothing.

WHY THIS EXISTS.

The sealed drive halts between the read and the first model call and will not
continue until a named human has ruled on twenty-four instances, in process, at
a terminal. That is the most human-dependent step in an unrepeatable run, and
as of 2026-08-30 nobody had ever performed it. `docs/F4-DRIVE-RUNBOOK.md` says
so in terms - *"Nobody has walked this path end to end. Read
crucible/transfer/inspect.py before the day, not during it."*

Reading a module is not the same as having done the thing. The failure being
prevented here is an operator meeting the review loop for the first time with
the holdout already in memory and the attempt already spent - discovering then
that they do not know what the codes mean, that they cannot tell V1 from V2 on
a real fixture, or that they wanted to stop halfway and did not know they
could.

WHAT IT REHEARSES, AND WHAT IT DELIBERATELY DOES NOT SIMULATE.

It runs the REAL path: `crucible.transfer.inspect.adjudicate`, the real
rendering, the real ratified codes read from the ratified artifact, a real
post-read challenge, the real confirmation step, and the real self-checks that
run before anything is written. A rehearsal against a mock would teach the mock.

It does NOT read the holdout, and it cannot be made to. Instances come through
`load_instances(family, sealed=False, ...)`, whose training path goes through
`ArmedSeeds` and **refuses the sealed family by name**. There is no `--sealed`
flag here and no `--object-names`; the two doors are different code paths in the
runner and only one of them is reachable from this file.

WHY IT WRITES NO ADJUDICATION RECORD BY DEFAULT.

A rehearsal that leaves a record shaped like the real thing is a rehearsal that
can be handed to `--adjudication` by a tired person at 1am. Two things stop
that, and the first is structural rather than procedural:

  1. THE REAL GATE DERIVES THE ID SET FROM THE INSTANCES IN HAND.
     `await_adjudication` calls `inspect.ledger_for(record, instances)`, which
     loads the record against the ids that came off the wire. A rehearsal
     record carries STAND-IN ids, so it cannot satisfy the sealed run no matter
     who points at it. That is the same property that makes a valid-looking
     record over some other twenty-four unusable rather than merely detectable.
  2. Nothing is written unless `--keep` is passed, and what `--keep` writes is
     an ENVELOPE - the record nested under a key, beside a banner - which is
     not a valid adjudication record at the top level and will not load as one.

Belt and braces, and the braces are the ones that hold.

WHY THERE IS A PAUSE DRILL.

`pause` is the control an operator reaches for under exactly the conditions
that make them least likely to have read about it: tired, halfway through
twenty-four rulings, on a run that cannot be repeated. It also used to be
BROKEN - the exception told the operator to "re-enter the review in this same
process", and until 2026-08-30 nothing in the codebase caught it and re-entered
anything, which an independent review reproduced through this very script.

So `--pause-drill` types `pause` at the first instance and `resume` at the
prompt that follows, and hands the keyboard straight back. The operator sees
the stop-and-resume path once, from the inside, without having to know it
exists. It answers those two prompts and nothing else - never a reason code,
never the name, never the confirmation word, because a rehearsal that typed a
ruling would be teaching the machine's guess.

    python scripts/rehearse-adjudication.py                 # the default family
    python scripts/rehearse-adjudication.py --count 3       # a short walk
    python scripts/rehearse-adjudication.py --pause-drill   # walk stop-and-resume
    python scripts/rehearse-adjudication.py --keep <dir>    # leave the envelope
"""

import argparse
import importlib.util
import json
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from crucible.transfer import inspect as insp                        # noqa: E402

#: The runner is a script rather than a module, so it is loaded the way its own
#: tests load it. Importing it is what keeps this file honest: the family
#: loader, the sealed-family refusal and the code vocabulary are all the
#: runner's, not reimplementations that could drift from it.
_spec = importlib.util.spec_from_file_location(
    "record_f4_transfer", ROOT / "scripts" / "record-f4-transfer.py")
rt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rt)

BANNER = "REHEARSAL - a stand-in family. No sealed object is read and no attempt is spent."


def _rule(char="="):
    return char * 74


class PauseDrill:
    """Answers exactly two prompts - the first `codes>` and the `resume` that follows.

    IT RECOGNISES THE PROMPTS BY IMPORTING THEM, never by a local copy of the
    string. `inspect.PROMPT_CODES_SUFFIX` and `inspect.PROMPT_RESUME` have one
    owner, and a drill matching on its own spelling would go on answering a
    question the review had stopped asking - which does not look like a broken
    drill, it looks like an operator who never resumed.

    WHAT IT WILL NOT DO. It never enters a reason code, a name, or the
    confirmation word. Those belong to the human, and this module's whole
    position is that a rendered instance with a pre-filled answer is a person
    ratifying a machine's guess. It also exists only in this file: the real
    runner has no drill, no injected input and no flag that could reach one.
    """

    def __init__(self, ask=input, say=print):
        self._ask = ask
        self._say = say
        self.paused = False
        self.resumed = False

    def __call__(self, prompt=""):
        text = str(prompt)
        if not self.paused and text.endswith(insp.PROMPT_CODES_SUFFIX):
            self.paused = True
            self._say("")
            self._say("  [drill] typing `pause` for you, to walk the stop-and-"
                      "resume path once.")
            return "pause"
        if not self.resumed and text == insp.PROMPT_RESUME:
            self.resumed = True
            self._say("  [drill] typing `resume` for you. The review is yours "
                      "from here.")
            return "resume"
        return self._ask(prompt)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--family", default=rt.DEFAULT_STANDIN,
                    help="a TRAINING family (default %s). The sealed family is "
                         "refused by the loader, not by this argument."
                         % rt.DEFAULT_STANDIN)
    ap.add_argument("--count", type=int, default=None,
                    help="rehearse only the first N instances. The real run has "
                         "no such flag - a partial holdout is a different "
                         "experiment - but a rehearsal is allowed to be short.")
    ap.add_argument("--pause-drill", action="store_true",
                    help="type `pause` at the first instance and `resume` at "
                         "the prompt after it, so the stop-and-resume path is "
                         "walked rather than described. Nothing else is "
                         "answered for you.")
    ap.add_argument("--keep", metavar="DIR",
                    help="write the envelope and the progress file here instead "
                         "of a temporary directory that is discarded")
    args = ap.parse_args(argv)

    print(_rule())
    print("  " + BANNER)
    print(_rule())

    # THE LOADER IS THE GUARD. `--family F4` reaches
    # E_SEALED_FAMILY_VIA_TRAINING here, from the runner's own code, rather
    # than from a check this file would have to keep in step with it.
    #
    # Caught and printed rather than allowed to traceback: a rehearsal exists
    # to be run by someone who is practising, and a stack trace is a worse
    # answer to "you pointed this at the holdout" than a sentence is.
    try:
        _seeds, instances, sealed_names = rt.load_instances(
            args.family, False, False)
    except rt.TransferRunError as exc:
        print("  REFUSED %s" % exc)
        return 2
    assert sealed_names is None, (
        "the training path returned a sealed read set. That cannot happen and "
        "this rehearsal will not continue as though it had not.")

    if args.count:
        instances = instances[:args.count]
    if not instances:
        print("  no instances in family %r." % args.family)
        return 2

    print("  family        : %s (training)" % args.family)
    print("  instances     : %d" % len(instances))
    print("  codes         : read from %s" % rt.ADJ_RATIFIED)
    print("  criterion     : %s" % rt.ADJ_CRITERION)
    print()
    print("  Everything below is the real review loop. Type `?` for the codes,")
    print("  `show` to see an instance again, and `pause` to stop. A pause")
    print("  waits for you and asks `resume or abandon`; `resume` carries on")
    print("  from where you were, in this same process. On the day that is the")
    print("  only place it can happen - the challenge nonce and the instances")
    print("  live in memory and a second invocation would have to read the")
    print("  holdout again.")
    if args.pause_drill:
        print("  DRILL: `pause` and `resume` will be typed for you, once.")
    print(_rule("-"))

    workdir = pathlib.Path(args.keep) if args.keep else None
    tmp = None
    if workdir is None:
        tmp = tempfile.TemporaryDirectory(prefix="crucible-rehearsal-")
        workdir = pathlib.Path(tmp.name)
    workdir.mkdir(parents=True, exist_ok=True)

    read_line = PauseDrill() if args.pause_drill else input

    try:
        # THE REAL ENTRY POINT, with the real self-checks. `adjudicate` runs
        # `load_adjudication` and `verify_post_read` against the record it just
        # built, so a rehearsal that would have been refused on the day is
        # refused here instead - which is the entire point of rehearsing.
        #
        # THE RESUME LOOP IS INSIDE `adjudicate`, WHICH IS WHY THERE IS NONE
        # HERE. This script used to catch the pause and print REFUSED, and an
        # independent review used exactly that to show the documented
        # stop-and-resume path did not exist. A loop added here would have
        # fixed the rehearsal and left the real runner broken, and the operator
        # would have practised a resume the day did not have.
        record, challenge = insp.adjudicate(
            instances,
            read_line=read_line,
            progress_path=workdir / "rehearsal.progress.json",
            challenge_path=workdir / "rehearsal.challenge.json")
    except insp.AdjudicationDeclined as exc:
        # BEFORE the ReviewPaused clause, because it is a subclass of it.
        print()
        print("  DECLINED %s" % exc)
        print("  Declining is TERMINAL and does not reopen the review. That is")
        print("  the difference between `pause` and refusing to commit: one")
        print("  waits for you, the other ends the process. Nothing was")
        print("  written, and on the day the read would still not be respent.")
        return 1
    except insp.ReviewPaused as exc:
        print()
        print("  ABANDONED %s" % exc)
        print("  You paused and then chose `abandon`. Typing `resume` there")
        print("  instead carries on from the instance you stopped at, in this")
        print("  same process, with every ruling kept.")
        return 1
    except insp.InspectionError as exc:
        print()
        print("  REFUSED %s" % exc)
        print("  On the day this would have happened with the holdout already")
        print("  in memory. It happened here instead, which is what this is for.")
        return 1
    except KeyboardInterrupt:
        print()
        print("  Stopped. Progress was saved; the real run resumes the same way.")
        return 1

    print(_rule("-"))
    counts = insp.ledger_for(record, instances).counts()
    for name in sorted(counts):
        print("  %-24s %s" % (name, counts[name]))
    print(_rule())
    print("  " + BANNER)
    print("  The record below is NOT an adjudication record. It carries")
    print("  stand-in ids, so the sealed gate would refuse it: that gate")
    print("  derives the id set from the instances that came off the wire.")

    if args.keep:
        envelope = {
            "artifact": "REHEARSAL ENVELOPE. NOT an adjudication record.",
            "_why_nested": (
                "The record sits under a key so this file is not a valid "
                "adjudication document at the top level and will not load as "
                "one. The structural protection is separate and stronger: the "
                "sealed gate derives its id set from the instances in hand, so "
                "a record over stand-in ids cannot satisfy it."),
            "family": args.family,
            "record": record,
        }
        out = workdir / "rehearsal-envelope.json"
        out.write_text(json.dumps(envelope, indent=2, sort_keys=True) + chr(10),
                       encoding="utf-8", newline="")
        print("  envelope : %s" % out)
    else:
        print("  Nothing was kept. Pass --keep <dir> to leave the envelope.")

    if tmp is not None:
        tmp.cleanup()
    # The challenge is in-memory only and is deliberately not persisted; naming
    # it here so a reader does not go looking for where it was written.
    del challenge
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
