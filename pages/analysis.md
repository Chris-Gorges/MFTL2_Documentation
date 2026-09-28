Measurements {#mftl_page_analysis}
============

One document, `docs/analysis.md` in the library, holds every measurement behind
the code comments, the decisions taken because of them, the designs that were
evaluated and rejected, and the issues that are still open. Every number in it
was produced by a program in `examples/` in a Release build.

| Document | Question |
|---|---|
| @subpage mftl_page_measurements | What does each part of a timestep cost, which design decisions did **not** pay off, what failed silently and how is it guarded now, and what is still open? |

---

# Re-run them rather than trusting the tables {#analysis_rerun}

Every table carries the machine it was measured on, and the development machine
is a laptop with **four performance cores**:

- **Above four ranks the absolute times are a lower bound.** An 8-rank run puts
  half the ranks on efficiency cores and the per-triangle costs roughly triple.
  The *ratios* survive that; the absolute numbers do not.
- **Cache-locality results do not transfer.** Morton renumbering buys no
  measurable time here despite cutting mean edge index distance 160×. That needs
  re-measuring on an x86 node with 1–2 MiB L2 per core.
- **I/O layout results transfer least of all.** One local SSD is the
  configuration least able to tell a shared collective file from $P$ per-rank
  files, and the one where the shared file cannot win.

```bash
python3 build_all.py            # Release; the benchmarks are meaningless otherwise
./build/layout_benchmark
mpirun -n 4 ./build/parallel_advection_redistribute_list
mpirun -n 4 ./build/leveque_remeshing_parallel

# and the scaling sweep, which runs the benchmark at several rank counts itself
python3 run_scaling.py --preset laptop --all
```

---

# What each benchmark answers {#analysis_benchmarks}

| Program | Question |
|---|---|
| `layout_benchmark.c` | interleaved vs. padded vs. split xyz, on four access patterns |
| `parallel_advection_redistribute_list.c` | what a whole timestep costs, how much of it is communication, and (`--ab N`) what skipping unchanged bodies is worth |
| `orient3d_predicate_profile.c` | does the plain orientation determinant misclassify thin-film contact, and what does the adaptive one cost |
| `leveque_remeshing_singleproc.c` | what the serial remesher does to a sphere stretched into a filament and back |
| `leveque_remeshing_parallel.c` | over 150 remeshed timesteps, does the distributed answer track the serial one, is it reproducible to the bit, and what does a phase cost |
| `remesh_phase_profile.c` | where the time goes inside one distributed remeshing phase |
| `remesh_regime_sweep.c` | where the spanning/dispersed crossover lies, and what coarsening, the gather and the balancer buy |
| `parallel_advection_scaling.c` | strong, weak and granularity scaling of the timestep; swept over rank counts by `run_scaling.py` |

The single-rank kernel benchmarks (geometry, vertex normals, the update kernel)
were retired together with the persistent triangle frames they compared; their
tables are kept in §1 of @ref mftl_page_measurements as the record of why.
