MFTL — MultiFlow Triangulation Library {#mainpage}
======================================

MFTL is an HPC C11 library for distributed-memory (MPI) manipulation of closed
and open **triangulated surface meshes**, built for front tracking and
immersed-boundary CFD simulations.

It carries a surface through a flow solver: it partitions the mesh over a
Cartesian process grid, keeps a halo consistent, computes the per-timestep
geometry, remeshes the surface as it deforms, detects contact between bodies,
performs breakup and coalescence, and writes the result to VTK.

@note Read @ref mftl_page_architecture before changing anything structural.
      Most of the file layout follows from the one idea described there, and a
      change that ignores it will look local and will not be.

---

## Start here

| Page | What it answers |
|---|---|
| @subpage mftl_page_architecture | Why the memory layout is the way it is, and the three invariants every module may assume |
| @subpage mftl_page_building | How to configure, build, test, and generate this manual |
| @subpage mftl_page_timestep | The per-timestep call order, and the three things in it that are silent when wrong |
| @subpage mftl_page_invariants | Properties that must survive any change, each with the test that guards it |
| @subpage mftl_page_modules | The fourteen implementation modules, each with its own theory page |

The reference material is reachable from the navigation bar: **Modules** groups
the API by architectural layer, **Data Structures** lists every struct, and
**API Index** is the alphabetical list of every function, macro and typedef.

---

## What the library does today

- **Ensemble / domain** — MPI topology, Cartesian process grid, periodic bounds;
  a sparse per-rank list of the bodies a rank holds
- **Object pools** — the AoS+SoA container, one allocation per entity class
- **Half-edge topology with implicit indexing** — navigation, twin rebuilding,
  boundary marking, integrity checking, connected components
- **Derived per-triangle arrays** and the `MFTL_FOREACH_*` hot-loop iterators
- **Morton renumbering** of the pools
- **Periodic-aware geometry** — the fused per-timestep geometry + per-body
  quality pass, area- or angle-weighted vertex normals, closest point on a
  triangle, signed-distance rasterisation
- **Mesh construction** — indexed lists, icospheres, and marching cubes with a
  generated, crack-free case table
- **Per-body collectives over each body's holders** — reductions and exclusive
  prefix sums that do not grow with the number of bodies
- **Redistribution and ghost synchronisation** over a 26-neighbour graph
  communicator, with a global fallback path
- **VTK output** — a serial debug dump and a parallel writer (ASCII or raw
  binary; one file per rank, or one shared file via MPI-IO)
- **Isotropic remeshing** — split/collapse/flip/smooth, feature detection, and a
  three-subspace tangential smoother; **distributed** in two strategies chosen
  by one ratio (shift the cut planes, or move the bodies)
- **LBVH and contact detection** — Morton radix-split tree, explicit-stack dual
  traversal, Shewchuk-adaptive orientation predicate, exact Guigue–Devillers
  narrow phase, self-proximity, and the spatial halo that brings the other side
  of a cross-rank contact to the reporting rank
- **Topology changes** — breakup and coalescence by opposing-triangle detection,
  union-field signed distance, distributed marching cubes and a Newton volume
  correction, identical at every process count
- **Run configuration** — every runtime option in one struct, one settings file
  per simulation plus `section.key=value` overrides, validated with line numbers
  and "did you mean" suggestions, identical on every rank by construction

**Absent:** open-surface generators (other than a level set through
MFTLBuildMeshFromLevelSet()), GTS I/O, topological ghost-layer growth,
continuous-time (swept) contact or topology detection, and a mesh *reader* of
any format.

---

## The shortest complete program

```c
#include "mftl_core.h"

int main(int argc, char **argv)
{
  MPI_Init(&argc, &argv);
  MFTLRegisterMpiTypes();

  int    cuts[3]     = {2, 2, 1};
  double lo[3]       = {0.0, 0.0, 0.0};
  double hi[3]       = {1.0, 1.0, 1.0};
  bool   periodic[3] = {true, true, true};

  MFTL_Ensemble *ens = MFTLEnsembleCreate(MPI_COMM_WORLD, cuts, lo, hi, periodic, 4);

  MFTL_Object *drop   = MFTLObjectCreate(0);
  double       ctr[3] = {0.5, 0.5, 0.5};
  MFTLEnsembleAddObject(ens, drop);           /* the ensemble owns it now */
  MFTLGenerateSphere(drop, ctr, 0.2, 3);      /* collective; built on rank 0 */

  MFTLRedistribute(ens);                      /* spread it; `drop` is now invalid */
  MFTLEnsembleUpdate(ens);                    /* geometry + per-body quality */
  MFTLEnsembleUpdateVertexNormals(ens, MFTL_NORMAL_WEIGHT_AREA);  /* ghosts too */

  MFTL_VtkOptions opt = MFTLVtkDefaults();
  MFTLWriteVtu(ens, "droplet", &opt);

  MFTLEnsembleDestroy(&ens);                  /* cascades to every object */
  MFTLFreeMpiTypes();
  MPI_Finalize();
  return 0;
}
```

Every MFTL call above except MFTLObjectCreate() and MFTLVtkDefaults() is
**collective**. After MFTLRedistribute() a rank holds an #MFTL_Object only for
the bodies it holds entities of, so pointers are re-fetched by body id with
MFTLEnsembleFindLocalObject(); see @ref mftl_page_timestep.

### The same program, configured by a file

A simulation normally takes its options from a settings file rather than from
literals. Each library call then takes its block straight out of #MFTL_Settings:

```c
MFTL_Settings cfg;
MFTLSettingsDefaults(&cfg);
MFTLSettingsLoad(&cfg, "run.toml", MPI_COMM_WORLD);        /* rank 0 reads, every rank parses */
MFTLSettingsLoadArgs(&cfg, argc, argv, MPI_COMM_WORLD);    /* remesh.every=2 on the command line */

MFTL_Ensemble *ens = MFTLSettingsCreateEnsemble(&cfg, MPI_COMM_WORLD);   /* [domain] */
MFTL_Object *drop = MFTLObjectCreate(0);
MFTLEnsembleAddObject(ens, drop);
MFTLGenerateSphere(drop, cfg.sphere.center, cfg.sphere.radius, cfg.sphere.refinements);
MFTLSettingsResolve(&cfg, ens);                            /* lengths derived from the mesh */

MFTLRedistribute(ens);
MFTLRemeshEnsemble(ens, &cfg.remesh.params, &stats);
MFTLWriteVtu(ens, cfg.output.prefix, &cfg.output.vtk);
```

Every key, its default and what it means: @ref mftl_mod_settings, and
`mftl_settings template` prints them as an annotated file to start from.

---

## Reading order for the theory

The library's design rests on a small number of decisions that each have a
measured or structural justification. In rough dependency order:

1. **One allocation per entity class** (@ref mftl_memory) — makes "the AoS grew
   but the SoA did not" inexpressible rather than merely unlikely.
2. **Implicit half-edge indexing** (@ref mftl_topology) — half-edge \f$3t+k\f$
   *is* corner \f$k\f$ of triangle \f$t\f$, so `next`, `prev` and `face` are
   arithmetic and a whole family of traversal corruptions cannot occur.
3. **Ownership is a prefix** (@ref mftl_types) — one notion of ownership, carried
   by the index itself.
4. **The halo rule is vertex-complete** (@ref mftl_communication) — a triangle
   travels to the owner of each of its three corners *and* each of its three edge
   neighbours, which is what makes vertex normals communication-free and what
   the parallel remesher's freeze test reads backwards.
5. **Minimum-image edges at the point of use** (@ref mftl_geometry) — positions
   are stored wrapped, and every consumer forms seam-consistent edge vectors in
   registers, so periodicity needs no cached state.

---

## Measured results that contradict the design's own predictions

These are the reason to read the measurement document (`docs/analysis.md` in
the library) rather than the code comments alone.

| # | Expectation | Measurement |
|---|---|---|
| 1 | Persistent per-triangle frames pay off | Faster in isolation (1.25–2.00×), but their build cost and 72 B/triangle did not amortise in a moving, redistributed loop; removing them made the timestep 1.23× faster |
| 2 | Morton renumbering pays for itself | No measurable time on Apple silicon despite cutting mean edge index distance 160× |
| 3 | Splitting `verts.pos` into three arrays helps | Faster for gathers, slower for scatters, by similar amounts — a wash |
| 4 | The update kernel fails to vectorise because of the nine-way reduction | It does not; 26 % of the pass is one `sqrt` plus one divide, which is irreducible |
| 5 | Quality statistics cost ~5 % on top of geometry | **+90 %** (1.64 → 3.11 ns/triangle) — fusing is still right, but it is not free |
| 6 | Skipping unchanged bodies saves about the body fraction the geometry predicts (60–75 %) | 77–86 % of bodies skippable, 1.6–2.1× on the redistribution phase |
| 7 | MPI-IO makes output faster | It does not; dropping ASCII does. The 23–32× came entirely from raw binary replacing `printf` |
| 8 | The poor final remesh was an operator bug | It was **feature detection on a smooth surface** — set `feature_angle_threshold` to 180 for any smooth closed interface |
| 9 | The frozen share follows \f$1-(1-2\delta/h)^3\f$ | It over-predicts by about 2× (71 % against 36.6 % measured) |

---

## Author and licence

Christian Gorges. The radix sort in `src/arrayfunctions/` derives from Cameron
Hart's zlib-licensed implementation (its notice is preserved in the source
file), and the adaptive orientation predicate in `src/bvh/bvh_predicates.c`
follows Jonathan Shewchuk's public-domain robust predicates (Discrete Comput.
Geom. 18, 1997).
