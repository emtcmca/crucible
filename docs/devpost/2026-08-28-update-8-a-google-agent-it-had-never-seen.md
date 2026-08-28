## Update 8: we pointed it at a Google agent it had never seen

### What ran

Google publishes a customer service agent as an ADK sample. We changed nothing about it. Its
own code, its own model, its own tools, its own callbacks still attached. We added CRUCIBLE's
enforcement plugin to the app and asked the agent an ordinary customer question.

**With no policy**, the agent called `sync_ask_for_approval` for a 40 percent discount. It
executed, returned approved, and the agent told the customer so. There is no manager behind
that tool. It approves anything it is handed.

**With a policy CRUCIBLE had learned on a completely different agent**, the same question, the
same model, the same call. Refused. The tool never ran.

The rule that stopped it names no tool. It binds to a capability class, and the class was
assigned to that tool by a classifier reading the tool's own description. CRUCIBLE had never
seen this agent, and nobody wrote an attack for it.

### This is not a breach, and the distinction matters

The agent was not tricked. The sample's own prompt describes that tool to the model as asking
a manager for approval and never states a cap, so routing a large discount there is obedience.
The gap is that the escalation destination has no manager in it.

We are not claiming a vulnerability in Google's code. The claim is narrower and it is about
our system: a policy learned on one agent governed the real tool calls of another.

### It also found something in us

ADK runs a tool's after-callback even when a call was refused before it ran. The sample's
callback reads a status field that a refusal does not carry, so it raised. The block held, but
on a live deployment that is a crash rather than a graceful refusal, and a hardening layer that
crashes what it hardens has not finished the job.

Fixed. The interesting part is that the same callback breaks on three responses ADK itself
produces for a missing argument, an unconfirmed call and a rejected one, with CRUCIBLE nowhere
in the picture. The callback is fragile against its own framework and attaching CRUCIBLE
surfaced it.

### What is not known, and what this is not

One run per arm. No rate, no before and after percentage. Nothing here is a measurement of
attack success and no such number appears in the artifact.

Whether the policy holds against attacks aimed at that agent, because none were run. Whether
the argument level predicates travel as the class binding does: 20 of 44 bound rules read only
derived fields and would port, and 24 read an argument this agent does not declare. And the
number this project exists to produce, transfer to a sealed attack family, which is unsealed
2026-08-28 and does not exist before then.

[github.com/emtcmca/crucible](https://github.com/emtcmca/crucible)
