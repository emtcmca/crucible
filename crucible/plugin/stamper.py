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
attempt would become a policy input and the model would be back in the pure-code
path through the door ruling 19 nailed shut.

WHERE THE VALUES COME FROM. The plugin sits in `before_tool` and sees live tool
returns; the EVALUATOR does not. That is ruling 21's resolution: the harness
folds returns into seven typed, enumerated, hashed fields and the engine reads
only those. THE PLUGIN'S OUTPUT IS BOUNDED; A RAW RETURN IS NOT, AND THE BOUND
IS THE CLAIM.

THE COMPUTATION IS INJECTED, and that is a boundary rather than a convenience.
This class owns the DISCIPLINE - which prefix is reserved, what happens to a
model-authored value, what gets recorded. The per-field computation belongs to
the corpus/harness layer. Keeping them apart is what makes ruling 19's two
refusals checkable in one place: no content classifier, and NO MODEL-COMPUTED
`derived.*` FIELD, because a model-computed input argument launders a model into
the pure-code path without touching the component.
"""

DERIVED_PREFIX = "derived."


class DerivedStamper:
    """Stamps the seven Part B fields over a pending call's arguments."""

    def __init__(self, derived_schema: dict, compute=None):
        self.schema = derived_schema or {}
        self._declared = tuple(
            f["name"] for f in self.schema.get("derived_fields", []))
        self._compute_fn = compute

    @property
    def declared(self) -> tuple:
        """The declared `derived.*` names, from Part B. Seven of them.

        Read out of the schema rather than restated as a constant: section 8
        rule 11, one concept one name, and ruling 19 already drifted between
        six and seven in two documents written the same day.
        """
        return self._declared

    def _compute(self, name, tool_args, context):
        if self._compute_fn is None:
            raise ValueError(
                "no derived-field computation was supplied for %r. The stamper "
                "owns the discipline, not the arithmetic - see the module "
                "docstring." % name)
        return self._compute_fn(name, tool_args, context)

    def stamp(self, tool_args: dict, context: dict = None):
        """Return `(post_stamp_args, derived_overwrites)`.

        `post_stamp_args` is a NEW dict - the caller's is not mutated, because a
        stamper that mutates in place makes the pre-stamp args unrecoverable,
        and ruling 21 turns on being able to tell the two apart: the recorded
        event carries POST-stamp args so replay READS the values rather than
        recomputing them, and the overwrite record is evidence about what the
        PRE-stamp args said.
        """
        source = dict(tool_args or {})
        overwrites = []
        for key in sorted(k for k in source if k.startswith(DERIVED_PREFIX)):
            overwrites.append({"path": key, "model_value": source[key]})

        post = {k: v for k, v in source.items() if not k.startswith(DERIVED_PREFIX)}
        for name in self._declared:
            post[name] = self._compute(name, source, context)

        # An UNDECLARED derived.* key is removed rather than kept. Part B
        # declares seven and the prefix is reserved, so anything else under it
        # is model-authored by definition - and no rule can read it either, the
        # validator refuses an undeclared derived path (N6). Leaving it would
        # put an arbitrary model-chosen value into the recorded args under a
        # namespace whose entire meaning is "the harness computed this".
        return post, overwrites
