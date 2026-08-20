"""`target/` - the agent under test. NOT part of CRUCIBLE.

This package is the SUBJECT of the measurement, not part of the instrument. It
imports nothing from `crucible/` and nothing from `crucible/` imports it. The
harness reaches it the way it will reach any other target on D9: through the ADK
plugin surface, over declared tool signatures, with a capability manifest mapping
those tools to classes.

If this package ever needs to import a CRUCIBLE module in order to behave
correctly, the target has stopped being a target.
"""
