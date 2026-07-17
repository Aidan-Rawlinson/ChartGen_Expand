# ChartGen — Primer

*TBN Internal · Read this first. No prior context assumed.*

---

## 1. What ChartGen Is

ChartGen is under active development, built and maintained by a single developer. This document describes what it is built to do; the Feature List is the authority on what is currently built versus planned.

ChartGen is a comparative analysis and reporting tool. It takes benchmarking data collected from NHS organisations and turns it into PowerPoint and PDF outputs — from individualised reports run at scale across an entire comparator population, to one-off reports and standalone presentations.

Most reporting software is special-purpose — built around one specific output, with that structure assumed from the start. ChartGen is general-purpose: it makes no assumption about what a report should look like, so it can produce any length or structure — from a one-page flyer to a two-hundred-page report — draw on any appropriately-shaped data source, and render almost any visualisation, rather than being built around one fixed design.

With sufficient configuration, a report's structure — not just its data — can change from one organisation to the next: different page counts, different charts, different analysis, different sources. This is algorithmic personalisation: the rules decide the shape of the report, not just what fills it in.

---

## 2. Why It Exists

The Benchmarking Network runs benchmarking exercises across a wide range of clients, using a wide range of methods. At the centre of all of it is comparative analysis.

Comparative analysis is a naturally bounded field. A large amount of raw data is collected, but once the initial calculations are done, the ways that data then gets used are relatively few — nothing like the long tail of techniques found in other analytical disciplines. The datasets themselves are modest, well short of "big data" scale. This is what makes a purpose-built system like ChartGen feasible: the problem space is constrained enough to be systematised.

ChartGen exists to take that comparative analysis and turn it into reports and presentations — whether that's one individualised report per organisation across a whole benchmarking exercise, a single one-off output, or, with sufficient configuration, a batch where each organisation's report differs algorithmically in structure as well as content — without manually rebuilding each one by hand.

---

## 3. What Comparative Analysis Is

At its core, comparative analysis is about **context** — a number on its own is close to meaningless; it only becomes meaningful once placed against something else. This is the essence of the field: **meaning-through-comparison**.

That meaning follows a pipeline:

**The Insight Pipeline**
Information → Context → Actionable Insight → Decision/Intervention

A value can be compared against four broad types of reference:

- **Self-comparison** (temporal) — How something is performing now compared to how it performed before.
  - Own past performance

- **Peer comparison** (social) — How something is performing compared to others — similar peers, top performers, or comparable examples elsewhere.
  - Peers
  - Exemplars
  - Other fields

- **Standards-based comparison** (normative) — How something is performing against agreed standards.
  - Targets
  - Standards
  - Processes

- **Cross-metric comparison** (dimensional) — How something is performing when viewed alongside a different but connected metric.
  - Similar metrics: e.g. Inpatient patient satisfaction vs Outpatient patient satisfaction
  - Related metrics: e.g. Cost per bed & Cost per 100,000 population

### Key Supporting Concepts

**Summary statistics** are the standard way of describing a population's data.

A **comparator** — referred to as a **unit** throughout these documents, since "comparator" is not widely understood within the company — is a single organisation or entity being compared against others.

A comparison population (including peer groups) — referred to as **population** throughout these documents — is the set of units being compared against.

Data passes through **normalisation** before any of this analysis can happen — here meaning bringing data from different sources into a single, consistent structure and format.

An example data pathway: Online Toolkit → Benchmarking Software → PowerPoint presentation.

---

## 4. Origin and Design Intent

ChartGen replaces a previous system built on Excel and VBA. The move to Python was driven by three main factors: stability, extendibility, and access to a vastly larger charting ecosystem — opening up visualisation possibilities that Excel's own charting could never support.

ChartGen is designed to be general-purpose: it should be able to produce outputs in any layout or formatting, accept appropriately-shaped data from any source, and visualise that data in almost any way. This intent runs through the whole system — it is why the architecture favours generality and configurability over fixed, hardcoded solutions, even where a narrower approach might look simpler at first glance.

ChartGen is a three-stage pipeline: variable input → narrow middle → variable output. Data sources and output formats are intentionally unconstrained — any appropriately-shaped source in, any layout or structure out. The middle stage is not unconstrained: comparative analysis is a bounded field, and the middle's job is normalisation into consistent, structured data flows, not open-ended analysis logic.

When writing or refactoring code for this system:

- Do not let variability at the input or output stage propagate into the middle.
- For the data flow, a normalisation step at the boundary should almost always be preferred to a special case in the core.
- The canonical data shapes, the Population tables, and the Running Order are all normalised — the first two on the data side, the Running Order on the process side, as a legible method for building variable outputs rather than one-off assembly logic per output.
- When building new code, first check which stage it belongs to. If it's in the middle, the mechanism itself must stay normalised and constrained, even if what it acts on or produces is highly variable or specific.

---

## 5. Who's Involved

ChartGen is used by TBN staff to produce benchmarking reports. It is designed, built, and maintained by a single developer. The reports it produces are read by the NHS organisations taking part in each benchmarking exercise.
