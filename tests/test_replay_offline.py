"""test_replay_offline.py - L6's negative check NC-1, written BEFORE the viewer.

    REPLAY RUNS FROM A CLEAN CHECKOUT WITH NO CREDENTIALS IN THE ENVIRONMENT.

The repository is PUBLIC and the judge-reproduction path is the reason the demo
can say "the bundles are in the repo, replay them yourself" instead of running a
multi-minute live loop on camera. If replay needs a credential, a stranger cannot
run it, and the reproduction claim is not merely unproven - it is untestable.

TWO INSTRUMENTS, AND NEITHER IS SUFFICIENT ALONE
------------------------------------------------
STATIC. `crucible.replay.offline_lint` walks the AST of every module under
`crucible/replay/` and refuses network clients, cloud SDKs, subprocess, and ANY
read of the process environment. It catches a credential path that the current
bundle happens not to exercise - a branch nobody took today is still a branch.

RUNTIME. The viewer is executed in a SUBPROCESS whose environment has been
stripped to the handful of variables an interpreter needs to start, and again in
a subprocess where `socket` has been replaced with something that raises. The
static lint cannot see a module name assembled at runtime; the runtime check
cannot see a branch that was not taken. Together they cover both halves, and
saying so is `CONVENTIONS.md` section 8 rule 9 - log the drop.

WHY THE STRAWMEN ARE THE POINT
------------------------------
A scrubbed-environment harness that is not actually scrubbing anything passes
every test forever. So a script that DOES read a credential is run under the same
harness and must FAIL, and a script that DOES open a socket is run under the
socket block and must FAIL. Without those two cases this file proves that the
viewer runs, not that it runs offline.
"""

import json
import os
import pathlib
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent
GOLDEN = REPO / "contracts" / "golden" / "C6-evidence_bundle.valid.json"

from tests import strawman_replay  # noqa: E402


# --------------------------------------------------------------------------
# The scrubbed environment. Deliberately minimal: what is NOT here is the
# assertion, so every addition needs a reason written next to it.
# --------------------------------------------------------------------------

KEEP = (
    "PATH",         # find the interpreter's own DLLs and, on POSIX, itself
    "PATHEXT",      # Windows: without it CreateProcess cannot resolve python
    "SYSTEMROOT",   # Windows: the CRT and the socket stack read this at startup
    "SystemRoot",
    "COMSPEC",
    "TEMP", "TMP", "TMPDIR",
    "WINDIR",
)

# Anything matching these is a credential, a project binding, or a token. If one
# of them survives into the child, the harness is not testing what it claims.
FORBIDDEN_SUBSTRINGS = ("GOOGLE", "GCLOUD", "CLOUDSDK", "GCP", "AWS", "AZURE",
                        "ANTHROPIC", "OPENAI", "VERTEX", "CREDENTIAL", "TOKEN",
                        "SECRET", "API_KEY", "APIKEY", "PASSWORD", "SESSION")


def scrubbed_env():
    env = {k: os.environ[k] for k in KEEP if k in os.environ}
    env["PYTHONPATH"] = str(REPO)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def test_the_scrub_actually_removes_something():
    """If the harness leaves credentials in place, every case below passes for
    the wrong reason. This is the check on the check."""
    env = scrubbed_env()
    leaked = [k for k in env
              if any(s in k.upper() for s in FORBIDDEN_SUBSTRINGS)]
    assert not leaked, "scrubbed env still carries %s" % leaked


def run_offline(args, env=None, block_network=False, tmp_path=None):
    """Run a command in a child process with the scrubbed environment, and
    optionally with the socket module replaced by something that raises."""
    env = env or scrubbed_env()
    if not block_network:
        return subprocess.run([sys.executable] + args, capture_output=True,
                              text=True, env=env, cwd=str(REPO))
    driver = tmp_path / "no_network.py"
    driver.write_text(
        "import runpy, socket, sys\n"
        "class NetworkAttempted(OSError):\n"
        "    pass\n"
        "def _blocked(*a, **k):\n"
        "    raise NetworkAttempted('offline replay tried to reach the network')\n"
        "socket.socket = _blocked\n"
        "socket.create_connection = _blocked\n"
        "socket.getaddrinfo = _blocked\n"
        "mod = sys.argv.pop(1)\n"
        "sys.argv[0] = mod\n"
        "try:\n"
        "    runpy.run_module(mod, run_name='__main__')\n"
        "except SystemExit as e:\n"
        "    raise SystemExit(e.code)\n",
        encoding="utf-8")
    return subprocess.run([sys.executable, str(driver)] + args,
                          capture_output=True, text=True, env=env, cwd=str(REPO))


# --------------------------------------------------------------------------
# THE RUNTIME HALF - the viewer must run with nothing in the environment.
# --------------------------------------------------------------------------

def test_viewer_runs_with_no_credentials_in_the_environment():
    r = run_offline(["-m", "crucible.replay", str(GOLDEN)])
    assert r.returncode == 0, "exit %s\n%s\n%s" % (r.returncode, r.stdout, r.stderr)
    assert "run_20260824_141207_a91f3c" in r.stdout


def test_viewer_runs_with_the_network_removed(tmp_path):
    r = run_offline(["crucible.replay", str(GOLDEN)],
                    block_network=True, tmp_path=tmp_path)
    assert r.returncode == 0, "exit %s\n%s\n%s" % (r.returncode, r.stdout, r.stderr)
    assert "NetworkAttempted" not in r.stderr


def test_viewer_rejects_a_damaged_bundle_with_a_nonzero_exit(tmp_path):
    """The CLI's contract for anything scripting it: a bundle that fails
    integrity exits non-zero. A viewer that prints a defect and exits 0 is the
    same failure as one that renders a blank, one layer out."""
    bundle = json.loads(GOLDEN.read_text(encoding="utf-8"))
    damaged = tmp_path / "damaged.json"
    damaged.write_text(json.dumps(strawman_replay.mutate(
        bundle, "episode_missing_derived_schema_hash")), encoding="utf-8")
    r = run_offline(["-m", "crucible.replay", str(damaged)])
    assert r.returncode != 0
    assert "derived_schema_hash" in (r.stdout + r.stderr)


# --------------------------------------------------------------------------
# THE STRAWMEN - proof that the two harnesses above can fail at all.
# --------------------------------------------------------------------------

def test_a_credential_reading_script_FAILS_under_the_same_harness(tmp_path):
    script = tmp_path / "needs_credential.py"
    script.write_text(
        "import os\n"
        "print(os.environ['GOOGLE_APPLICATION_CREDENTIALS'])\n", encoding="utf-8")
    r = run_offline([str(script)])
    assert r.returncode != 0, (
        "a script that reads GOOGLE_APPLICATION_CREDENTIALS succeeded under the "
        "scrubbed environment. THE SCRUB IS NOT SCRUBBING, and every offline "
        "claim in this file is unsupported.")
    assert "KeyError" in r.stderr


def test_a_socket_opening_script_FAILS_under_the_network_block(tmp_path):
    mod_dir = tmp_path / "netmod"
    mod_dir.mkdir()
    (mod_dir / "__init__.py").write_text("", encoding="utf-8")
    (mod_dir / "__main__.py").write_text(
        "import socket\n"
        "socket.socket()\n", encoding="utf-8")
    env = scrubbed_env()
    env["PYTHONPATH"] = str(tmp_path) + os.pathsep + str(REPO)
    r = run_offline(["netmod"], env=env, block_network=True, tmp_path=tmp_path)
    assert r.returncode != 0, (
        "a script that opened a socket succeeded under the network block. THE "
        "BLOCK IS NOT BLOCKING.")
    assert "NetworkAttempted" in r.stderr


# --------------------------------------------------------------------------
# THE STATIC HALF - the lint over crucible/replay/.
# --------------------------------------------------------------------------

def test_replay_package_is_clean_under_the_offline_lint():
    from crucible.replay import run_offline_lint
    findings = run_offline_lint()
    assert findings == [], "\n".join(str(f) for f in findings)


@pytest.mark.parametrize("name", sorted(strawman_replay.LINT_MUST_FLAG))
def test_offline_lint_flags_the_strawman_sources(name):
    """A lint aimed only at code that is already clean has never been shown to
    detect anything."""
    from crucible.replay import scan_offline_source
    source = getattr(strawman_replay, name)
    findings = scan_offline_source(source, path="<%s>" % name)
    assert findings, (
        "offline lint found nothing in strawman_replay.%s. %s"
        % (name, strawman_replay.LINT_MUST_FLAG[name]))


def test_offline_lint_reports_a_missing_root_rather_than_passing():
    """A lint pointed at a path that does not exist passes forever. That is the
    same defect class as a check that cannot fail, and import_lint.py already
    pays for it in the tripwire; the fix travels."""
    from crucible.replay import run_offline_lint
    findings = run_offline_lint(roots=("crucible/no_such_package",))
    assert findings, "a lint aimed at nothing reported clean"
    assert "missing root" in str(findings[0])


def test_offline_lint_is_not_fooled_by_a_prefix_that_merely_looks_denied():
    """`googleapiclient` must be caught and `google_fonts_helper` must not.
    Matching on dotted SEGMENTS rather than characters is what keeps a lint
    from being relaxed the first time it fires on something legitimate - and a
    lint that is relaxed once is a lint that is relaxed again."""
    from crucible.replay import scan_offline_source
    assert scan_offline_source("import googleapiclient.discovery\n")
    assert not scan_offline_source("import google_fonts_helper\n")
