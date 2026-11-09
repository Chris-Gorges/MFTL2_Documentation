---
hide:
  - navigation
  - toc
---

# MFTL

<p class="mftl-hero-tagline">
A distributed-memory C11 library for triangulated surface meshes &mdash;
built to carry a front through a flow solver.
</p>

[What MFTL is](overview.md){ .md-button .md-button--primary }
[Build it](guide/building.md){ .md-button }
[:material-tune-variant: All settings](settings.md){ .md-button .mftl-button-settings }
[API reference](api/index.md){ .md-button }
{ .mftl-hero-actions }

---

## Start here

<div class="grid cards" markdown>

-   :material-vector-triangle:{ .lg .middle } &nbsp; __Overview__

    ---

    What the library does today, what it deliberately does not, and the shortest
    complete program that creates a sphere and writes it out.

    [:octicons-arrow-right-24: Read the overview](overview.md)

-   :material-hammer-wrench:{ .lg .middle } &nbsp; __Building &amp; testing__

    ---

    CMake, the three build modes, the seventy-two CTest entries, and why
    `-march=native` is off by default.

    [:octicons-arrow-right-24: Build and run the suite](guide/building.md)

-   :material-layers-triple-outline:{ .lg .middle } &nbsp; __Architecture__

    ---

    One idea decides the file layout: topology wants AoS, geometry wants SoA,
    and both live in one allocation per entity class.

    [:octicons-arrow-right-24: Read the one idea](guide/architecture.md)

-   :material-timer-outline:{ .lg .middle } &nbsp; __The timestep__

    ---

    The per-timestep call order, with and without redistribution &mdash; and the
    three things in it that are silent when wrong.

    [:octicons-arrow-right-24: Get the order right](guide/timestep.md)

</div>

---

## Configure a run

<div class="grid" markdown>

<div markdown>

Every runtime option of the library &mdash; the domain and its decomposition,
remeshing, topology changes, contact, output &mdash; is set from **one settings
file per simulation**, and any of it can be overridden on the command line.

The reference lists every key with its default, what it accepts and what it
does, with a filter to find it and a complete file to start from. A misspelled
key is an error that names the key you meant, never a silent default.

[:material-tune-variant: Browse all settings](settings.md){ .md-button .mftl-button-settings }

</div>

```toml
# run.toml
[remesh]
every             = 1
target_length     = 0.0      # hold the starting resolution
parallel_strategy = "auto"

[topology]
every = 5                    # breakup and coalescence

[output]
every  = 10
prefix = "out/run"
```

</div>

---

## Go deeper

<div class="grid cards" markdown>

-   :material-shield-check-outline:{ .lg .middle } &nbsp; __Invariants__

    ---

    The properties that must survive any change, each named together with the
    test that guards it.

    [:octicons-arrow-right-24: What must stay true](guide/invariants.md)

-   :material-view-module-outline:{ .lg .middle } &nbsp; __Twelve modules__

    ---

    One module is one `src/` directory, one public header and one theory
    chapter. Start from the dependency graph.

    [:octicons-arrow-right-24: Browse the modules](modules/index.md)

<!-- measurements -->
-   :material-chart-line:{ .lg .middle } &nbsp; __Measured, not assumed__

    ---

    One measurement document: what was measured, what was decided because of
    it, what was rejected, and what is still open.

    [:octicons-arrow-right-24: Read the numbers](analysis/index.md)

<!-- /measurements -->

-   :material-api:{ .lg .middle } &nbsp; __API reference__

    ---

    Every function, macro, struct and field, generated from the sources &mdash;
    plus the full Doxygen manual with call graphs.

    [:octicons-arrow-right-24: Open the reference](api/index.md)

</div>

---

## The shape of a run

```
MFTLSettingsLoad → MFTLSettingsCreateEnsemble → MFTLEnsembleAddObject → MFTLGenerateSphere
  → MFTLSettingsResolve → MFTLRedistribute
per timestep:
  move owned vertices → MFTLUpdateGhostPositions → MFTLEnsembleComputeTriangleGeometry
  → MFTLRedistribute → MFTLEnsembleUpdate
  → MFTLRemeshEnsemble / MFTLEnsembleApplyTopologyChanges   (every cfg.remesh / cfg.topology .every steps)
  → MFTLEnsembleIntersectObjects                           (contact, every cfg.contact.every steps)
  → MFTLWriteVtu                                            (output, every cfg.output.every steps)
```

The order is not decorative. Three of those steps are load-bearing and fail
silently when swapped, and every `MFTL_Object*` is invalid after a
redistribution &mdash; [the timestep page](guide/timestep.md) says why.
