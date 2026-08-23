# custom_charts

User- or AI-authored Base Charts saved into a workfile rather than the software. A saved one resolves and behaves identically to a built-in.

`gate.py` runs a static check before anything is compiled or executed: allowed imports only, a short banned-builtins list, exactly one function matching the `chart_inputs` signature. There is no sandboxing beyond this, and no check on what the function actually returns.

`resolve.py` looks a `base_chart_name` up against the built-in registry first, then the workfile's saved Custom Charts.

`bundle.py` builds the document handed to an AI: the contract, the chart's complete current file rather than just its function, and its live data.

`contract.py` is both the enforced whitelist and the explanation an author reads. When the rendering contract changes, this file is the change. A Custom Chart saved against an older contract has to be re-saved by hand; nothing migrates it.
