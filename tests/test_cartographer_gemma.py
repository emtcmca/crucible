"""test_cartographer_gemma.py - the CAPABILITY_CARTOGRAPHER against a FOREIGN agent.

Plain English first. `architecture-spec.md:138` specifies the Cartographer as
proposing capability classes "for each tool the deterministic pre-pass could not
resolve", never final, unable to approve its own classification. This suite
proves those three properties on a real third-party agent -
`google/adk-samples` -> `python/agents/customer-service`, frozen at commit
`629310b7b845398841c814456289a34fbc766acf` (verified with `git rev-parse` in the
clone at `C:\\dev\\_sandbox\\adk-samples`; see
`docs/decisions-pending/gemma-cartographer-foreign-adk-2026-08-22.md`).

NO TEST HERE MAKES A MODEL CALL. `Cartographer` takes a `complete(prompt) -> str`
callable and every test passes a stub, so the contract is proved offline, with no
credential and at no cost. `crucible/cartographer/vertex.py` supplies the real
callable and is exercised by nothing in this file, deliberately.

THE MEASUREMENT THIS SUITE PINS, AND WHY IT IS THE HEADLINE.

`test_prepass_resolves_nothing_on_the_foreign_agent` records that the
deterministic pre-pass resolves **0 of 12** tools on this target, against 6 of 8
on our own refund agent (`tests/test_capability_prepass.py`). That is not a bug
in either number - it is the measurement that says `prepass.py`'s five rules key
on OUR agent's argument vocabulary (`amount` + `currency`, a `to` documented as
an email address, `status_to`, `*_agent`, `queue`) and none of it appears in
somebody else's agent.

It is pinned as a test rather than written in a document because two documents
already assert the opposite:

  * `docs/proof/third-party-target-recon-2026-08-22.md:306` - "tools 1, 5, 7, 8,
    10 resolve in the deterministic pre-pass on arg-shape alone". Written before
    the pre-pass existed. Running it resolves none of them.
  * `docs/decisions-pending/product-shape-2026-08-22.md:76` - "The deterministic
    pre-pass already resolves most of it". True of our agent, false of this one.

A number that contradicts two live documents belongs somewhere that fails loudly
when it changes.

WHAT THIS SUITE DOES NOT CLAIM. No accuracy figure for any classification -
nothing has been measured against a labelled set, and `gemma-scope.md` section 7
forbids stating one. The stub responses below are fixtures chosen to exercise
the validator; they are not a model's answers and no test treats them as
evidence about model quality.
"""

import json
import os

import pytest

from crucible.cartographer.extract import (
    ExtractionError,
    load_frozen_target,
)
from crucible.cartographer.gemma import (
    Cartographer,
    ProposalRejected,
    build_prompt,
    parse_response,
    split_residue,
    validate_proposal_set,
)
from crucible.cartographer.prepass import UNCLASSIFIED, classify_tool
from crucible.cartographer.ratify import (
    RatificationError,
    build_ratification,
    proposal_set_digest,
    to_manifest_entries,
)

PINNED_SHA = "629310b7b845398841c814456289a34fbc766acf"
PINNED_TOOL_COUNT = 12


@pytest.fixture(scope="module")
def frozen():
    return load_frozen_target("adk_customer_service")


@pytest.fixture(scope="module")
def specs(frozen):
    return frozen["tools"]


# --------------------------------------------------------------------------
# The frozen foreign target. Provenance is data, not a sentence in a doc.
# --------------------------------------------------------------------------

def test_frozen_target_provenance_is_pinned(frozen):
    """The fixture names the repository, the full 40-char SHA, and the file each
    tool was read from. `f4c19ab` reached three golden fixtures and a published
    proof file because a plausible-looking SHA had nothing behind it
    (`third-party-target-recon-2026-08-22.md` section 1)."""
    assert frozen["repository"] == "https://github.com/google/adk-samples"
    assert frozen["commit_sha"] == PINNED_SHA
    assert len(frozen["commit_sha"]) == 40, "a short SHA is ambiguous"
    assert frozen["tool_count"] == PINNED_TOOL_COUNT
    for spec in frozen["tools"]:
        prov = spec["provenance"]
        assert prov["source_file"].endswith("customer_service/tools/tools.py")
        assert prov["def_line"] > 0, "%s has no source line" % spec["tool_name"]


def test_frozen_target_digest_is_recomputed_on_load(frozen, tmp_path):
    """`load_frozen_target` recomputes the digest instead of trusting it, so a
    hand-edited fixture fails at load rather than at the point where a
    classification built on it is being defended."""
    import crucible.cartographer.extract as extract

    tampered = json.loads(json.dumps(frozen))
    tampered["tools"][0]["args"][0]["name"] = "recipient"
    path = tmp_path / "adk_customer_service.json"
    path.write_text(json.dumps(tampered), encoding="utf-8")

    original_dir = extract.FROZEN_DIR
    extract.FROZEN_DIR = str(tmp_path)
    try:
        with pytest.raises(ExtractionError) as exc:
            extract.load_frozen_target("adk_customer_service")
    finally:
        extract.FROZEN_DIR = original_dir
    assert "has been edited" in str(exc.value)


def test_registry_matches_the_sample_source(frozen):
    """The twelve names mirror the sample's own `tools=[...]` registry. Asserted
    rather than trusted: if upstream adds a thirteenth tool, the frozen list
    goes stale silently, and a tool with no manifest handle classifies
    UNCLASSIFIED, which is ALLOWED, which switches the policy off for it."""
    names = [s["tool_name"] for s in frozen["tools"]]
    assert names == [
        "send_call_companion_link", "approve_discount", "sync_ask_for_approval",
        "update_salesforce_crm", "access_cart_information", "modify_cart",
        "get_product_recommendations", "check_product_availability",
        "schedule_planting_service", "get_available_planting_times",
        "send_care_instructions", "generate_qr_code",
    ]
    assert len(set(names)) == PINNED_TOOL_COUNT


# --------------------------------------------------------------------------
# THE MEASUREMENT. Pinned, and it contradicts two live documents.
# --------------------------------------------------------------------------

def test_prepass_resolves_nothing_on_the_foreign_agent(specs):
    """0 of 12. See this file's docstring for what that means and which two
    documents it corrects.

    This test is the reason the Cartographer is warranted here AND the reason
    the split is not currently buying what `gemma-scope.md` section 6 designed
    it to buy: with an empty left-hand side, the model is classifying
    everything, which is the exact condition the memo warns about. Do not
    "fix" this by adding rules until the number looks better - a rule added to
    move a metric is a rule tuned to a fixture."""
    resolved, residue = split_residue(specs)
    assert len(resolved) == 0
    assert len(residue) == PINNED_TOOL_COUNT
    for spec in specs:
        result = classify_tool(spec)
        assert result["resolved"] is False
        assert result["classes"] == (UNCLASSIFIED,)
        assert result["evidence"] == ()


def test_prepass_is_unclassified_not_inert_on_the_foreign_agent(specs):
    """UNCLASSIFIED ("we do not know") never degrades to the empty set ("we know,
    and it is nothing"). `capabilities.py` treats those as different claims and
    the second one is much stronger."""
    for spec in specs:
        result = classify_tool(spec)
        assert result["classes"] != ()
        assert result["classes"] == (UNCLASSIFIED,)


# --------------------------------------------------------------------------
# The blindness boundary: what the model is shown, and what it is not.
# --------------------------------------------------------------------------

def _spec(name, args, docstring="", agent="a"):
    return {
        "tool_name": name,
        "docstring": docstring,
        "args": [{"name": n, "type": "str", "description": d} for n, d in args],
        "declaring_agent": agent,
        "transport": "function",
    }


RESOLVABLE = _spec(
    "email_customer",
    [("to", "The customer's email address."), ("body", "The message body.")],
    docstring="Email the customer.\n\nArgs:\n    to: The customer's email address.\n",
)


def test_the_model_never_sees_a_tool_the_prepass_resolved():
    """The split is enforced in code, not in the prompt. A tool the pre-pass
    answered is absent from the residue, so it cannot reach `build_prompt`."""
    unresolvable = _spec("ping", [("nonce", "an opaque token")])
    resolved, residue = split_residue([RESOLVABLE, unresolvable])
    assert [s["tool_name"] for s, _ in resolved] == ["email_customer"]
    assert [s["tool_name"] for s in residue] == ["ping"]

    prompt = build_prompt(residue)
    assert "ping" in prompt
    assert "email_customer" not in prompt


def test_prompt_carries_every_residue_tool_and_its_arguments(specs):
    prompt = build_prompt(specs)
    for spec in specs:
        assert spec["tool_name"] in prompt
        for arg in spec["args"]:
            assert arg["name"] in prompt


def test_prompt_is_blind_to_the_corpus_the_policy_and_the_tripwire(specs):
    """`architecture-spec.md:138` - the Cartographer "runs before any round
    exists". A prompt that mentioned an attack, a rule, or a verdict would mean
    it does not."""
    prompt = build_prompt(specs).lower()
    for forbidden in ("attack", "breach", "policy", "tripwire", "deny(",
                      "constrain_arg", "episode.", "red team", "jailbreak"):
        assert forbidden not in prompt, "prompt leaked %r" % forbidden


def test_build_prompt_refuses_an_empty_batch():
    """If the pre-pass resolved everything, there is nothing for a model to do
    and calling one is spend with no question attached. `gemma-scope.md`
    section 6 blesses that outcome explicitly."""
    with pytest.raises(ValueError):
        build_prompt([])


def test_propose_short_circuits_when_there_is_no_residue():
    """The same rule, at the component level: the completer is never called."""
    calls = []

    def never(prompt):  # pragma: no cover - proving it is not reached
        calls.append(prompt)
        return "{}"

    out = Cartographer(never).propose([RESOLVABLE])
    assert calls == []
    assert out["proposals"] == ()
    assert out["prompt"] is None
    assert out["resolved_tool_names"] == ("email_customer",)


# --------------------------------------------------------------------------
# Valid proposals, and the evidence contract.
# --------------------------------------------------------------------------

def _proposal(name, classes, evidence, confidence=0.6):
    return {
        "tool_name": name,
        "proposed_classes": list(classes),
        "model_self_reported_confidence": confidence,
        "evidence": list(evidence),
    }


def _arg_cite(cls, arg, why="because"):
    return {"capability_class": cls, "cites": {"kind": "argument", "value": arg},
            "citation": why}


def _full_valid_response(specs):
    """A syntactically valid response covering all twelve residue tools.

    Every citation names an argument the tool actually declares. These are
    FIXTURES for the validator, not a model's opinions - no test reads a class
    here as a claim about what the tool does."""
    proposals = []
    for spec in specs:
        arg = spec["args"][0]["name"] if spec["args"] else None
        if arg is None:
            proposals.append(_proposal(spec["tool_name"], [UNCLASSIFIED], []))
        else:
            proposals.append(_proposal(
                spec["tool_name"], ["CAP_MUTATES_DURABLE_STATE"],
                [_arg_cite("CAP_MUTATES_DURABLE_STATE", arg)]))
    return json.dumps({"proposals": proposals})


def test_end_to_end_against_a_stub_produces_unratified_proposals(specs):
    seen = {}

    def stub(prompt):
        seen["prompt"] = prompt
        return _full_valid_response(specs)

    out = Cartographer(stub, model_id="stub/none").propose(specs)
    assert len(out["proposals"]) == PINNED_TOOL_COUNT
    assert out["residue_tool_names"] == tuple(s["tool_name"] for s in specs)
    assert out["ratified"] is False
    for p in out["proposals"]:
        assert p["ratified"] is False
        assert p["source"] == "CAPABILITY_CARTOGRAPHER"
    assert seen["prompt"] == out["prompt"]


def test_every_proposed_class_carries_evidence(specs):
    out = Cartographer(lambda _p: _full_valid_response(specs)).propose(specs)
    for p in out["proposals"]:
        for cls in p["proposed_classes"]:
            if cls == UNCLASSIFIED:
                continue
            assert any(e["capability_class"] == cls for e in p["evidence"]), (
                "%s proposes %s with no evidence" % (p["tool_name"], cls))


def test_evidence_citations_resolve_against_the_tool_declaration(specs):
    """The point of the `cites` block: a reviewer can check every citation
    against the tool signature without re-running anything."""
    by_name = {s["tool_name"]: s for s in specs}
    out = Cartographer(lambda _p: _full_valid_response(specs)).propose(specs)
    for p in out["proposals"]:
        spec = by_name[p["tool_name"]]
        arg_names = {a["name"] for a in spec["args"]}
        for e in p["evidence"]:
            if e["cites"]["kind"] == "argument":
                assert e["cites"]["value"] in arg_names
            else:
                assert e["cites"]["value"] in spec["docstring"]


def test_a_docstring_citation_must_be_verbatim(specs):
    """A quote copied from the docstring passes; the same claim paraphrased does
    not. A model cannot invent a quotation past this check."""
    spec = [s for s in specs if s["tool_name"] == "send_call_companion_link"][0]
    verbatim = "Sends a link to the user's phone number"
    assert verbatim in spec["docstring"]

    ok = [_proposal("send_call_companion_link", ["CAP_EXTERNAL_COMMS"], [{
        "capability_class": "CAP_EXTERNAL_COMMS",
        "cites": {"kind": "docstring", "value": verbatim},
        "citation": "the docstring says the tool sends something to a phone number",
    }])]
    assert validate_proposal_set(ok, [spec])[0]["proposed_classes"] == ("CAP_EXTERNAL_COMMS",)

    paraphrased = [_proposal("send_call_companion_link", ["CAP_EXTERNAL_COMMS"], [{
        "capability_class": "CAP_EXTERNAL_COMMS",
        "cites": {"kind": "docstring", "value": "Sends an SMS link to the customer"},
        "citation": "same claim, not the same words",
    }])]
    with pytest.raises(ProposalRejected) as exc:
        validate_proposal_set(paraphrased, [spec])
    assert exc.value.code == "E_CITATION_NOT_GROUNDED"


def test_grounding_is_per_tool_not_a_global_argument_lookup(specs):
    """NEGATIVE CONTROL. A citation that is valid for one tool must fail on
    another. Without this, a validator that checked "is this string an argument
    name anywhere in the batch" would pass every test above."""
    by_name = {s["tool_name"]: s for s in specs}
    borrowed = "phone_number"
    assert borrowed in {a["name"] for a in by_name["send_call_companion_link"]["args"]}
    assert borrowed not in {a["name"] for a in by_name["modify_cart"]["args"]}

    bad = [_proposal("modify_cart", ["CAP_EXTERNAL_COMMS"],
                     [_arg_cite("CAP_EXTERNAL_COMMS", borrowed)])]
    with pytest.raises(ProposalRejected) as exc:
        validate_proposal_set(bad, [by_name["modify_cart"]])
    assert exc.value.code == "E_CITATION_NOT_GROUNDED"


# --------------------------------------------------------------------------
# Rejections. One test per code - "it raised" is not the same as "the right
# check fired".
# --------------------------------------------------------------------------

def test_rejects_a_proposal_for_a_tool_the_prepass_resolved():
    """The architectural rejection. The Cartographer sees residue only; a
    proposal for an already-resolved tool means the split leaked."""
    residue = [_spec("ping", [("nonce", "opaque")])]
    bad = [_proposal("ping", [UNCLASSIFIED], []),
           _proposal("email_customer", ["CAP_READS_PII"],
                     [_arg_cite("CAP_READS_PII", "to")])]
    with pytest.raises(ProposalRejected) as exc:
        validate_proposal_set(bad, residue, resolved_names=("email_customer",))
    assert exc.value.code == "E_TOOL_ALREADY_RESOLVED"
    assert exc.value.tool_name == "email_customer"


def test_rejects_a_tool_that_is_not_in_the_batch(specs):
    bad = [_proposal("delete_everything", ["CAP_MUTATES_DURABLE_STATE"],
                     [_arg_cite("CAP_MUTATES_DURABLE_STATE", "x")])]
    with pytest.raises(ProposalRejected) as exc:
        validate_proposal_set(bad, [specs[0]])
    assert exc.value.code == "E_TOOL_NOT_IN_RESIDUE"


def test_rejects_a_class_outside_the_six(specs):
    spec = specs[0]
    bad = [_proposal(spec["tool_name"], ["CAP_SENDS_SMS"],
                     [_arg_cite("CAP_SENDS_SMS", spec["args"][0]["name"])])]
    with pytest.raises(ProposalRejected) as exc:
        validate_proposal_set(bad, [spec])
    assert exc.value.code == "E_UNKNOWN_CLASS"


def test_rejects_unclassified_mixed_with_a_real_class(specs):
    spec = specs[0]
    arg = spec["args"][0]["name"]
    bad = [_proposal(spec["tool_name"], [UNCLASSIFIED, "CAP_EXTERNAL_COMMS"],
                     [_arg_cite("CAP_EXTERNAL_COMMS", arg)])]
    with pytest.raises(ProposalRejected) as exc:
        validate_proposal_set(bad, [spec])
    assert exc.value.code == "E_UNCLASSIFIED_MIXED"


def test_rejects_a_class_with_no_evidence(specs):
    """`prepass.py`'s doctrine, enforced on the model: "a classification with no
    citable evidence is a guess wearing a confidence number"."""
    spec = specs[0]
    bad = [_proposal(spec["tool_name"], ["CAP_EXTERNAL_COMMS"], [])]
    with pytest.raises(ProposalRejected) as exc:
        validate_proposal_set(bad, [spec])
    assert exc.value.code == "E_CLASS_WITHOUT_EVIDENCE"


def test_rejects_evidence_citing_an_argument_the_tool_does_not_declare(specs):
    spec = specs[0]
    bad = [_proposal(spec["tool_name"], ["CAP_MOVES_MONEY"],
                     [_arg_cite("CAP_MOVES_MONEY", "amount_cents")])]
    with pytest.raises(ProposalRejected) as exc:
        validate_proposal_set(bad, [spec])
    assert exc.value.code == "E_CITATION_NOT_GROUNDED"


def test_rejects_an_empty_class_list(specs):
    """An empty list would claim "this tool has no capabilities". UNCLASSIFIED
    is how a model says it does not know; the two are different claims."""
    spec = specs[0]
    bad = [_proposal(spec["tool_name"], [], [])]
    with pytest.raises(ProposalRejected) as exc:
        validate_proposal_set(bad, [spec])
    assert exc.value.code == "E_NO_CLASSES"


def test_rejects_a_silently_dropped_tool(specs):
    """Twelve in, eleven out is a manifest with a hole in it, and the hole is
    ALLOWED by default."""
    partial = json.loads(_full_valid_response(specs))["proposals"][:-1]
    with pytest.raises(ProposalRejected) as exc:
        validate_proposal_set(partial, specs)
    assert exc.value.code == "E_INCOMPLETE_COVERAGE"
    assert "generate_qr_code" in str(exc.value)


def test_rejects_a_duplicate_proposal(specs):
    spec = specs[0]
    arg = spec["args"][0]["name"]
    one = _proposal(spec["tool_name"], ["CAP_EXTERNAL_COMMS"],
                    [_arg_cite("CAP_EXTERNAL_COMMS", arg)])
    with pytest.raises(ProposalRejected) as exc:
        validate_proposal_set([one, dict(one)], [spec])
    assert exc.value.code == "E_DUPLICATE_TOOL"


def test_rejects_a_response_that_is_not_json():
    with pytest.raises(ProposalRejected) as exc:
        parse_response("Sure! Here are the capability classes I would propose:")
    assert exc.value.code == "E_NOT_JSON"


def test_rejects_an_empty_response():
    with pytest.raises(ProposalRejected) as exc:
        parse_response("   ")
    assert exc.value.code == "E_EMPTY_RESPONSE"


def test_tolerates_a_json_code_fence(specs):
    """Models emit one regardless of instructions. Tolerating the fence is not
    the same as salvaging malformed JSON, which is refused above."""
    fenced = "```json\n" + _full_valid_response(specs) + "\n```"
    assert len(parse_response(fenced)) == PINNED_TOOL_COUNT


# --------------------------------------------------------------------------
# The human gate. Nothing reaches a manifest without a person.
# --------------------------------------------------------------------------

def _propose(specs):
    return Cartographer(lambda _p: _full_valid_response(specs),
                        model_id="google/gemma-4-26b-a4b-it").propose(specs)


def _accept_all(proposal_set):
    return {p["tool_name"]: {"decision": "accept", "reason": "reviewed"}
            for p in proposal_set["proposals"]}


def test_a_proposal_cannot_enter_a_manifest_unratified(specs):
    """The property `gemma-scope.md` section 6 says is the one that makes the
    component defensible."""
    ps = _propose(specs)
    with pytest.raises(RatificationError) as exc:
        to_manifest_entries(ps, None)
    assert exc.value.code == "E_NOT_RATIFIED"


def test_the_cartographer_cannot_ratify_itself(specs):
    ps = _propose(specs)
    with pytest.raises(RatificationError) as exc:
        build_ratification(ratified_by="CAPABILITY_CARTOGRAPHER",
                           ratified_on="2026-08-22",
                           proposals=ps["proposals"],
                           decisions=_accept_all(ps))
    assert exc.value.code == "E_SELF_APPROVAL"


def test_an_unreviewed_tool_blocks_the_whole_ratification(specs):
    ps = _propose(specs)
    decisions = _accept_all(ps)
    decisions.pop("generate_qr_code")
    with pytest.raises(RatificationError) as exc:
        build_ratification(ratified_by="Eric Tetzlaff", ratified_on="2026-08-22",
                           proposals=ps["proposals"], decisions=decisions)
    assert exc.value.code == "E_UNREVIEWED_TOOL"
    assert "generate_qr_code" in str(exc.value)


def test_ratification_binds_to_the_exact_proposals_reviewed(specs):
    """Sign, then change one proposed class, then try to use the signature. The
    digest moves and the record stops matching - the person is bound to the
    bytes they read, not to the tool names."""
    ps = _propose(specs)
    record = build_ratification(ratified_by="Eric Tetzlaff", ratified_on="2026-08-22",
                                proposals=ps["proposals"], decisions=_accept_all(ps))
    assert to_manifest_entries(ps, record)

    tampered = dict(ps)
    swapped = list(ps["proposals"])
    swapped[0] = dict(swapped[0], proposed_classes=("CAP_MOVES_MONEY",))
    tampered["proposals"] = tuple(swapped)

    with pytest.raises(RatificationError) as exc:
        to_manifest_entries(tampered, record)
    assert exc.value.code == "E_DIGEST_MISMATCH"


def test_accept_amend_and_reject_produce_three_different_outcomes(specs):
    """NEGATIVE CONTROL for the gate. A ratifier that could only rubber-stamp
    would pass every test above. This one demands the three verdicts land
    differently: accepted keeps the model's classes and is stamped
    `cartographer`; amended takes the human's classes and is stamped `human`;
    rejected produces no manifest entry at all."""
    ps = _propose(specs)
    decisions = _accept_all(ps)
    decisions["approve_discount"] = {
        "decision": "amend",
        "classes": ["CAP_MOVES_MONEY", "CAP_ESCALATES_PRIVILEGE"],
        "reason": "the verb is an authorization decision, not only a write",
    }
    decisions["get_available_planting_times"] = {
        "decision": "reject", "reason": "a pure read of non-personal data",
    }
    record = build_ratification(ratified_by="Eric Tetzlaff", ratified_on="2026-08-22",
                                proposals=ps["proposals"], decisions=decisions)
    entries = {e["tool_name"]: e for e in to_manifest_entries(ps, record)}

    assert "get_available_planting_times" not in entries
    assert len(entries) == PINNED_TOOL_COUNT - 1

    amended = entries["approve_discount"]
    assert amended["capability_classes"] == ("CAP_MOVES_MONEY", "CAP_ESCALATES_PRIVILEGE")
    assert amended["classified_by"] == "human"

    accepted = entries["modify_cart"]
    assert accepted["classified_by"] == "cartographer"
    assert accepted["capability_classes"] == ("CAP_MUTATES_DURABLE_STATE",)

    for entry in entries.values():
        assert entry["human_confirmed"] is True
        assert entry["ratified_by"] == "Eric Tetzlaff"
        assert entry["evidence"], "%s reached the manifest with no evidence" % entry["tool_name"]


def test_amending_to_a_class_outside_the_six_is_refused(specs):
    ps = _propose(specs)
    decisions = _accept_all(ps)
    decisions["modify_cart"] = {"decision": "amend", "classes": ["CAP_WHATEVER"],
                                "reason": "typo"}
    with pytest.raises(RatificationError) as exc:
        build_ratification(ratified_by="Eric Tetzlaff", ratified_on="2026-08-22",
                           proposals=ps["proposals"], decisions=decisions)
    assert exc.value.code == "E_UNKNOWN_CLASS"


def test_digest_ignores_the_prompt_and_the_raw_response(specs):
    """Re-running the model changes both without changing a classification. A
    ratification that expired on whitespace is one people route around."""
    ps = _propose(specs)
    same_classifications = dict(ps, prompt="different prompt text",
                                raw_response="different raw text")
    assert (proposal_set_digest(ps["proposals"])
            == proposal_set_digest(same_classifications["proposals"]))


# --------------------------------------------------------------------------
# Structural: the module cannot ratify, no matter how it is called.
# --------------------------------------------------------------------------

def test_the_cartographer_module_contains_no_path_that_ratifies():
    """A behavioural test proves the paths exercised. This proves the absence of
    one - there is no line in `gemma.py` that sets ratified true. Same shape as
    the Armorer never writing a rule ID."""
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "crucible", "cartographer", "gemma.py")
    with open(path, encoding="utf-8") as fh:
        source = fh.read()
    for forbidden in ('"ratified": True', "'ratified': True",
                      '"human_confirmed": True', "ratified=True"):
        assert forbidden not in source, "gemma.py can ratify: %r" % forbidden
