"""stamper.py - the `derived.*` stamp. Ruling 19 and ruling 21.

Seven fields, computed by the HARNESS, written over the model's arguments in
`before_tool`, DISCARDING anything the model wrote under the `derived.` prefix
and RECORDING the attempt in `ToolEvent.derived_overwrites`.

WHY DISCARD-AND-RECORD RATHER THAN DISCARD, OR MERGE, OR REJECT.

  * Merge is the failure. `derived.subject_verified_in_episode` is the harness's
    own statement that this call's subject was verified in this episode. If a
    model can set it, the agent can assert that it verified something it did not
    - which defeats P26 and the control ruling 14 put in place of the
    non-compiling `preceded_by` polarity.
  * Discard alone throws away evidence. A MODEL WRITING TO THIS FIELD IS AN
    AGENT FORGING THE HARNESS'S OWN VERIFICATION FIELD, and that is a
    higher-quality breach signal than most of what the corpus manufactures on
    purpose. The CORONER should see it.
  * Reject would convert a detection into a crash, and a crashed episode is
    TARGET_FAULT-shaped noise removed from the denominator - which turns the
    single best organic signal in the run into a missing row.

`derived_overwrites` is DIAGNOSTIC ONLY AND NOT EVALUABLE by the policy engine -
the same status as `result_digest`. If the engine could read it, the forgery
attempt would become a policy input and the model would be back in the
pure-code path through the door ruling 19 nailed shut.

WHERE THE VALUES COME FROM. The plugin sits in `before_tool` and sees live tool
returns; the EVALUATOR does not. That is ruling 21's resolution: the harness
folds returns into seven typed, enumerated, hashed fields and the engine reads
only those. THE PLUGIN'S OUTPUT IS BOUNDED; A RAW RETURN IS NOT, AND THE BOUND
IS THE CLAIM.

NOT IMPLEMENTED YET - this is the stub the negative checks run RED against.
"""

DERIVED_PREFIX = "derived."


class DerivedStamper:
    """Stamps the seven Part B fields over a pending call's arguments.

    The computation of each field belongs to the corpus/harness layer, not here.
    This class owns the DISCIPLINE - which prefix is reserved, what happens to a
    model-authored value, and what gets recorded - and takes the computation as
    an injected callable so that a lane cannot accidentally make a derived field
    depend on something the bright line forbids.
    """

    def __init__(self, derived_schema: dict, compute=None):
        raise NotImplementedError("L3 WI-5: stamper not implemented yet")

    @property
    def declared(self) -> tuple:
        """The declared `derived.*` names, from Part B. Seven of them."""
        raise NotImplementedError("L3 WI-5: stamper not implemented yet")

    def stamp(self, tool_args: dict, context: dict = None):
        """Return `(post_stamp_args, derived_overwrites)`.

        `post_stamp_args` is a NEW dict - the caller's is not mutated, because a
        stamper that mutates in place makes the pre-stamp args unrecoverable and
        ruling 21 turns on being able to tell the two apart.
        """
        raise NotImplementedError("L3 WI-5: stamper not implemented yet")
