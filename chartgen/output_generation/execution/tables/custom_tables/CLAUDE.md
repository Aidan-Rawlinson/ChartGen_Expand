# custom_tables

Mirrors `charts/custom_charts/` field for field, for the table domain.

`contract.py` keeps its own copy of the allowed-imports whitelist and banned-names list. It is identical in content to the chart domain's today, and is deliberately not imported from it: the two rendering domains are independent, and a future divergence in one should carry no risk to the other.

Standing guidance for Base Table authors lives in this contract text, not in code comments elsewhere, because the bundle download and paste-back flow is in practice the only way a Base Table gets built or modified.

`bundle.py` takes an opt-in `include_charts` flag, off by default. When set, it appends each `{Cn}` cell's Chart Store entry, source and live data, so the whole table including its embedded charts can be rebuilt from the one document.
