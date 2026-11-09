The per-timestep loop {#mftl_page_timestep}
=====================

[TOC]

This page is the call-order contract. Everything on it is load-bearing, and most
of it is **silent when wrong** — the mesh stays structurally valid, every
integrity check still passes, and the numbers are quietly stale or quietly
partial.

---

# Without redistribution {#ts_no_redist}

When the partition is not being changed this step:

```c
for (int o = 0; o < ens->n_local_objects; ++o)          /* 1. advect         */
{
  MFTL_Object *obj = ens->local_objects[o];
  MFTL_FOREACH_OWNED_VERTEX(obj, /* move p[0..2] */ );
}
MFTLEnsembleUpdate(ens);                                  /* 2. geometry+stats */
MFTLEnsembleUpdateVertexNormals(ens, MFTL_NORMAL_WEIGHT_AREA);  /* 3. optional */
```

**There is no rebuild step between 1 and 2.** Positions are authoritative and
live only in `verts.pos`; the geometry pass gathers them through the compact
connectivity and builds seam-corrected edge vectors in registers, so moving a
vertex leaves no cached array stale and nothing has to be remembered afterwards.

The normals of OWNED vertices need no communication, because the halo is
vertex-complete (@ref ts_vertex_normals); MFTLEnsembleUpdateVertexNormals() adds
one ghost exchange so that ghost normals are exact too. A caller that reads owned
vertices only may call the local MFTLComputeVertexNormals() per object instead.

---

# With redistribution {#ts_redist}

```c
/* 1 */ for (int o = 0; o < ens->n_local_objects; ++o)
          MFTL_FOREACH_OWNED_VERTEX(ens->local_objects[o], /* move p[0..2] */ );
/* 2 */ MFTLUpdateGhostPositions(ens);
/* 3 */ MFTLEnsembleComputeTriangleGeometry(ens);   /* every object, ghosts included */
/* 4 */ MFTLRedistribute(ens);                      /* invalidates every MFTL_Object* */
/* 5 */ MFTLEnsembleUpdate(ens);                    /* optional, but see below */
/* 6 */ MFTLEnsembleUpdateVertexNormals(ens, MFTL_NORMAL_WEIGHT_AREA);  /* optional */
```

<!-- figure: timestep-validity
What is valid after each call of the loop with redistribution. Stale: computed
from positions that have moved since. Unspecified: left undefined on purpose by
the redistribution; that is what its 3× smaller wire format costs, and a pass
restores it. Invalid: an `MFTL_Object*` held across step 4.
-->

Three things about this order are load-bearing, and **all three are silent when
wrong**:

### The ghost sync must precede the geometry pass

A triangle's three vertices can belong to three different ranks. Computing its
centroid before step 2 uses last step's positions for whichever corners are
ghosts.

### The geometry pass must cover the ghosts too

Hence MFTLEnsembleComputeTriangleGeometry(), i.e.
`MFTLComputeTriangleGeometry(obj, obj->tris.n)` and not `tris.n_local`, in step 3.
Redistribution routes
triangles by their **cached centre**; refreshing only the owned ones makes two
ranks disagree about a ghost's destination, and the entity is duplicated or lost
depending on which way the disagreement falls.

MFTLRedistribute() guards this: a body whose #MFTL_DERIVED_GEOMETRY bit is
clear — no pass over all its triangles since the last ghost sync, topology
change or redistribution — has its geometry recomputed before it is routed,
counted in `n_objects_centres_recomputed` and warned about once. That covers a
skipped step 3, an owned-only step 3 and a step 3 before step 2, at the price of
the pass you skipped. Moving vertices *after* step 3 is not seen, but every
holder then routes by the same old centres: one step behind, still consistent.
Generated meshes leave the generator with current geometry.

### There is deliberately no geometry cache to refresh in the loop

MFTLComputeTriangleGeometry() dispatches between a compact-index path and the
construction-time half-edge fallback, and both gather the current positions.
Persistent per-triangle frames existed here once and were removed: they were
72 B/triangle of state that the documented loop wrote and discarded unread, and
deleting them was worth 1.23× on the whole timestep. The measurement is
`docs/analysis.md` §1.2 in the library.

### Pointers do not survive a redistribution

A rank holds an #MFTL_Object exactly for the bodies it holds entities of: a body
whose entities all left is destroyed, one that arrived is created. **An
`MFTL_Object*`, a list slot and `n_local_objects` are invalid after step 4.** Keep
the body id and re-fetch with MFTLEnsembleFindLocalObject() (which returns
`MFTL_NULL` when this rank no longer holds the body). Advecting through a stale
pointer lost 93 % of a sphere's volume in twelve steps at np = 2 while every
structural check passed (`test_leveque_parallel_conserves`).

---

# With remeshing and front corrections {#ts_corrections}

```c
/* 1 */ advect the owned vertices;
/* 2 */ MFTLUpdateGhostPositions(ens);
/* 3 */ MFTLEnsembleRemoveUndulations(ens, &und, &ust);        /* optional: TSUR3D */
/* 4 */ MFTLEnsembleComputeTriangleGeometry(ens);
/* 5 */ MFTLRemeshEnsemble(ens, &params, &rst);                 /* or MFTLRedistribute(ens) */
/* 6 */ MFTLEnsembleApplyTopologyChanges(ens, &topo, &tst);     /* optional */
/* 7 */ MFTLEnsembleCorrectVolumes(ens, &vol, &vst);            /* LAST */
```

with MFTLEnsembleSetReferenceVolumes() called once before the loop. The two
corrections are separate calls on purpose: the remesher's Phong back-projection
moves its smoothed vertices back onto the surface the call RECEIVED, so a normal
correction made inside the call would be undone. Undulations come from the
advection and are removed before the remesh, which then keeps the smoothing; the
volume correction restores, last, what the advection, the remesh and a topology
change moved -- once per step is enough, a second call after step 2 changes the
shape at second order only. The reference volume travels with each body through
step 5's redistribution and is handed on by step 6. See @ref mftl_mod_correction.

---

# What a redistribution leaves behind {#ts_redist_leaves}

@warning **Redistribution invalidates all cached geometry except the vertex
         positions.**

It returns an object with valid topology, valid positions and
#MFTL_DERIVED_TOPOLOGY set (#MFTL_DERIVED_GEOMETRY clear). But:

| Array | State after MFTLRedistribute() |
|---|---|
| `verts.pos` | valid |
| `tris.verts`, `tris.neighbors` | valid (emitted during the rebuild) |
| `tris.area`, `tris.normal`, `tris.center` | **unspecified** |
| `verts.normal` | **unspecified** |

That is what buys the 3× smaller wire format: the alternative is to pack the
areas, normals and centres onto the wire so that a timestep ends with valid
triangle geometry. A solver that consumes triangle geometry *after* the
redistribution therefore owes one more pass.

`examples/parallel_advection_redistribute_list.c` runs it as step 5 and times it
**separately**, because a redistribute timing that excludes the pass it defers
credits the redistribution with a saving it has not finished paying for.

@note Step 5 is bound by **first touch**, not by its kernel. The geometry pass
      that restores what redistribution drops runs on pools the redistribution
      has just rewritten, and costs 6.4 ns/triangle against 2.9 ns for the same
      function on a resident mesh.

---

# Vertex normals and the vertex-complete halo {#ts_vertex_normals}

MFTLComputeVertexNormals() accumulates

\f[
  \vect{N}_v = \frac{\sum_{t \ni v} A_t\, \hat{\vect{n}}_t}
                    {\norm{\sum_{t \ni v} A_t\, \hat{\vect{n}}_t}}
\f]

over **all** triangles including ghosts. An owned vertex therefore gets the exact
answer *iff* every triangle incident to it is present locally.

That is a stronger requirement on redistribution than "one layer of edge-adjacent
ghost triangles", and it is exactly what buys the pass zero communication. The
redistribution halo rule — a triangle travels to the owner of each of its three
**corners** as well as each of its three edge neighbours — is what supplies it.

@warning **Ghost vertices hold a PARTIAL SUM**, correctly normalised and quietly
         wrong. That is the trap: it looks exactly like a real normal.
         MFTLEnsembleUpdateVertexNormals() closes it with one ghost exchange.
         Call that unless you are certain you read owned vertices only.

---

# Which calls are collective {#ts_collective}

**Collective** — every rank of the ensemble's communicator must call them,
including ranks that hold no body:

- MFTLEnsembleCreate(), MFTLEnsembleUpdate(), MFTLEnsembleUpdateGlobalCounts(),
  MFTLEnsembleUpdateVertexNormals(), MFTLEnsembleMeanEdgeLength()
- MFTLEnsembleReduceBodies(), MFTLEnsembleExscanBodies()
- MFTLGenerateSphere(), MFTLPublishGeneratedBodies()
- MFTLRedistribute(), MFTLRedistributeWithOwners(),
  MFTLRedistributeSetSkipUnchangedBodies()
- MFTLUpdateGhostPositions(), MFTLUpdateGhostVertexNormals()
- MFTLWriteVtu()
- MFTLRemeshEnsemble(), MFTLRemeshEnsembleParallel(),
  MFTLRemeshEnsembleDispersed(), MFTLRemeshChooseStrategy(),
  MFTLRemeshMeasureBodies()
- MFTLSpatialHaloResolveRadii(), MFTLExtendSpatialHalo(),
  MFTLExtendSpatialHaloNearBodies(), MFTLEnsembleIntersectObjects()
- MFTLTopologyDetectEvents(), MFTLEnsembleReconstructBodies(),
  MFTLEnsembleApplyTopologyChanges()
- MFTLSettingsLoad(), MFTLSettingsLoadArgs(), MFTLSettingsCreateEnsemble(),
  MFTLSettingsResolve()

**Deliberately local** — each rank works on its own partition:

- MFTLObjectBuildDerived(), MFTLObjectReorderMorton()
- MFTLBuildIndexedMesh(), MFTLBuildTopologyFromIndexList(),
  MFTLGenerateSphereLocal()
- MFTLComputeTriangleGeometry(), MFTLEnsembleComputeTriangleGeometry(),
  MFTLComputeVertexNormals()
- MFTLRemeshObject(), MFTLRemeshMarkFrozen(), MFTLDilateFrozenBand(),
  MFTLDetectFeatures(), MFTLSmoothTangential(), MFTLMeanEdgeLength()
- MFTLRasterizeSignedDistance(), MFTLExtractLevelSet(),
  MFTLBuildMeshFromLevelSet(), MFTLLabelConnectedComponents(),
  MFTLTopologyLattice()
- MFTLWriteVtk()
- MFTL_GenerateLBVH(), MFTL_RefitLBVH(), MFTL_IntersectObjects()
- MFTLSettingsDefaults(), MFTLSettingsParse(), MFTLSettingsSet(),
  MFTLSettingsGet(), MFTLSettingsCheck(), MFTLSettingsWrite(),
  MFTLSettingsChooseCuts()

`test_vertex_normals_np3` exists to make an accidentally-introduced collective in
the local list deadlock in CI.

@warning MFTLRemeshEnsemble() **dispatches**: `nproc == 1` takes the serial path
         unchanged; above that MFTLRemeshChooseStrategy() (itself collective — it
         measures the bodies) picks the dispersed or the spanning driver. **Both
         drivers must be reached by every rank**, so the choice is made from
         reduced data and never from anything local. Two ranks entering different
         drivers is an immediate deadlock with no diagnostic.

---

# Adding remeshing to the loop {#ts_remeshing}

Remeshing is not a per-timestep necessity for every solver, but when it is in the
loop the ordering constraint is:

```
advect  →  ghost sync  →  geometry  →  REDISTRIBUTE  →  REMESH
```

The remesher returns the canonical partition with current triangle geometry
(`verts.normal` excepted), so no further pass is owed for triangle quantities.
Remeshing must follow the redistribution, not precede it, because the parallel
remesher's freeze test reads the *current* partition: an entity is frozen exactly
when some other rank holds a copy of it, and MFTLRemeshMarkFrozen() derives that
from `corner >= verts.n_local || neighbour >= tris.n_local`. Derive the target
length with the collective MFTLEnsembleMeanEdgeLength(), never the rank-local
MFTLMeanEdgeLength().

@warning `MFTL_RemeshParameters::parallel_phase_budget` defaults to 32, which
         means *run until no rank wants to do anything*. That is right for a
         one-shot remesh and measurably wrong inside a per-timestep loop, in both
         directions at once — worse volume conservation, worse triangle quality
         **and** five times slower. Set it to 2–8 for a loop. The full
         measurement table is on the field's documentation.

@note Remeshing renumbers global ids at the end of every pass, and it has to:
      splits hand out fresh ids and collapses retire them, so ids stay unique but
      stop being dense — and `src/communication/` sizes its arrival lookup tables
      from `next_*_gid`. The cost is that pool indices **and** global ids are both
      unstable across a remesh, so nothing external may hold either.

---

# Adding contact detection to the loop {#ts_contact}

```
... → REDISTRIBUTE → MFTLEnsembleIntersectObjects()
```

MFTLEnsembleIntersectObjects() builds one BVH per held body, grows its own
spatial halo (MFTLExtendSpatialHaloNearBodies()) and discards it again. Call
MFTLExtendSpatialHalo() yourself only when you need the halo for something else.

@warning **The spatial halo is transient and cannot be otherwise.**
         Redistribution keeps only owned triangles, so a halo cannot survive a
         repartition. Each MFTLExtendSpatialHalo() *replaces* the previous
         patches; grow it after redistribution.

@note **Contact detection is discrete-time: there is no CCD.** A pair whose
      relative displacement in one step exceeds the sum of their sizes passes
      through without ever being coincident at a sampled instant, and both
      samples correctly report nothing. This bites when the timestep is set by a
      CFL condition on the *flow* rather than by the approach velocity of two
      surfaces, which is the normal case.

---

# Adding topology changes to the loop {#ts_topology}

MFTLEnsembleApplyTopologyChanges() goes where a remeshing pass would: after the
vertices moved and the ghost positions were synchronised, and before the geometry
a solver reads. A call that detects nothing changes nothing; one that
reconstructs closes with MFTLRedistribute() (and the remesh in
`MFTL_TopologyOptions::remesh`), so every pointer rule above applies. Bodies can
appear and disappear: `n_bodies_global` is the size of the body-id space, and
ids of vanished bodies are never reused.

---

# Driving the loop from a settings file {#ts_settings}

Every block the calls above take — #MFTL_RemeshParameters,
#MFTL_TopologyOptions, #MFTL_BVHBuildParams, #MFTL_VtkOptions — is a section of
#MFTL_Settings, and each section carries an `every` that says how often the call
is due. A loop configured by a file therefore reads:

```c
for (int step = 0; step < n_steps; ++step)
{
  /* move owned vertices, MFTLUpdateGhostPositions, triangle geometry (ghosts included) */
  if (MFTLSettingsDue(cfg.remesh.every, step)) MFTLRemeshEnsemble(ens, &cfg.remesh.params, &st);
  else                                         MFTLRedistribute(ens);
  if (MFTLSettingsDue(cfg.topology.every, step)) MFTLEnsembleApplyTopologyChanges(ens, &cfg.topology.options, &ts);
  if (MFTLSettingsDue(cfg.contact.every, step))  MFTLEnsembleIntersectObjects(ens, &cfg.contact.params, cb, data);
  if (MFTLSettingsDue(cfg.output.every, step))   MFTLWriteVtu(ens, name, &cfg.output.vtk);
}
```

The order is the one this page derives; the settings change how often each call
runs, never where it goes. Two things are specific to the file-driven form.
MFTLSettingsResolve() must run after the bodies exist and before the loop, because
the lengths left at 0 — the remesh target and everything derived from it — are
measured from the mesh. And because the remesh strategy, the phase budget and
`redistribute.skip_unchanged_bodies` change which collectives run, the struct
must be identical on every rank: load it with MFTLSettingsLoad(), and change a
field afterwards only identically everywhere (MFTLSettingsResolve() checks, and
names the first key that differs). `examples/settings_driven_run.c` is the
complete program; @ref mftl_mod_settings has the file format and every rule.
