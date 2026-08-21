"""
custom_tables/
Custom Tables -- user- or AI-authored Base Tables saved into a workfile,
mirroring chartgen.output_generation.execution.charts.custom_charts field for
field, for the table domain. Static validation and compilation (gate.py),
built-in-then-custom resolution (resolve.py), the AI-facing download
bundle (bundle.py), and the shared contract both enforce and explain
(contract.py).

Unlike Custom Charts, there is no shape_type scoping -- every Base Table
takes the same table_inputs (an already-resolved grid), so a saved custom
table is a valid option everywhere, always, the moment it's saved.
"""
