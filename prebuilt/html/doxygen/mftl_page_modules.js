var mftl_page_modules =
[
    [ "How they depend on each other", "mftl_page_modules.html#modules_deps", null ],
    [ "What each one owns", "mftl_page_modules.html#modules_owns", null ],
    [ "`src/arrayfunctions/` — Sorting and duplicate removal", "mftl_mod_arrayfunctions.html", [
      [ "Algorithm", "mftl_mod_arrayfunctions.html#arr_algorithm", [
        [ "Small inputs", "mftl_mod_arrayfunctions.html#arr_cutoff", null ]
      ] ],
      [ "Interface notes", "mftl_mod_arrayfunctions.html#arr_interface", null ]
    ] ],
    [ "`src/object/` — The mesh container", "mftl_mod_object.html", [
      [ "One pool is one allocation", "mftl_mod_object.html#object_one_block", null ],
      [ "The size API", "mftl_mod_object.html#object_size_api", null ],
      [ "Derived connectivity", "mftl_mod_object.html#object_derived", null ],
      [ "Morton renumbering", "mftl_mod_object.html#object_morton", null ],
      [ "Hot-loop iterators", "mftl_mod_object.html#object_iterators", null ]
    ] ],
    [ "`src/topology/` — Half-edge connectivity", "mftl_mod_topology.html", [
      [ "The half-edge structure with implicit indexing", "mftl_mod_topology.html#topo_implicit", null ],
      [ "Rebuilding twins", "mftl_mod_topology.html#topo_twins", null ],
      [ "Boundary is a property of the surface, not of the partition", "mftl_mod_topology.html#topo_boundary", null ],
      [ "Walking a fan", "mftl_mod_topology.html#topo_fan", null ],
      [ "Integrity checking", "mftl_mod_topology.html#topo_integrity", null ],
      [ "Connected components", "mftl_mod_topology.html#topo_components", null ],
      [ "The flag word", "mftl_mod_topology.html#topo_flags", null ]
    ] ],
    [ "`src/geometry/` — Periodic-aware geometry", "mftl_mod_geometry.html", [
      [ "The minimum-image convention", "mftl_mod_geometry.html#geom_minimum_image", null ],
      [ "Triangle area, normal and centroid", "mftl_mod_geometry.html#geom_triangle", [
        [ "A normal is always a unit vector", "mftl_mod_geometry.html#geom_unit_normal", null ]
      ] ],
      [ "Vertex normals", "mftl_mod_geometry.html#geom_vertex_normals", [
        [ "Exactness needs a vertex-complete halo", "mftl_mod_geometry.html#autotoc_md30", null ]
      ] ],
      [ "Closest point and signed distance", "mftl_mod_geometry.html#geom_sdf", null ]
    ] ],
    [ "`src/mesh_creation/` — Mesh construction", "mftl_mod_meshgen.html", [
      [ "One conversion point", "mftl_mod_meshgen.html#meshgen_one_builder", null ],
      [ "The icosphere", "mftl_mod_meshgen.html#meshgen_icosahedron", [
        [ "Generation is rank-0 serial", "mftl_mod_meshgen.html#meshgen_collective", null ]
      ] ],
      [ "Marching cubes", "mftl_mod_meshgen.html#meshgen_mc", [
        [ "A table generated from one face rule", "mftl_mod_meshgen.html#autotoc_md40", null ],
        [ "Lattice-keyed extraction", "mftl_mod_meshgen.html#autotoc_md41", null ]
      ] ]
    ] ],
    [ "`src/ensemble/` — The library handle and the per-body collectives", "mftl_mod_ensemble.html", [
      [ "Ensemble → Domain → Objects", "mftl_mod_ensemble.html#ens_model", null ],
      [ "The MPI topology is built once", "mftl_mod_ensemble.html#ens_topology", null ],
      [ "The fused update pass", "mftl_mod_ensemble.html#ens_update", null ],
      [ "Per-body reductions over the holders", "mftl_mod_ensemble.html#ens_reduce", null ],
      [ "Per-body exclusive scans", "mftl_mod_ensemble.html#ens_exscan", null ],
      [ "Decomposition metric", "mftl_mod_ensemble.html#ens_local", null ]
    ] ],
    [ "`src/communication/` — Distributed memory", "mftl_mod_communication.html", [
      [ "Ownership and the halo rule", "mftl_mod_communication.html#comm_redistribute", [
        [ "What the wire carries", "mftl_mod_communication.html#comm_wire", null ]
      ] ],
      [ "The redistribution algorithm", "mftl_mod_communication.html#comm_algorithm", [
        [ "The global-id table", "mftl_mod_communication.html#comm_gid_table", null ],
        [ "A body that did not move is not touched", "mftl_mod_communication.html#comm_skip", null ],
        [ "Memory policy", "mftl_mod_communication.html#autotoc_md17", null ]
      ] ],
      [ "Ghost synchronisation", "mftl_mod_communication.html#comm_ghost", null ],
      [ "The spatial halo", "mftl_mod_communication.html#comm_spatial", [
        [ "Records, extents and the pair broad phase", "mftl_mod_communication.html#comm_halo_pairs", null ]
      ] ],
      [ "Known limitations", "mftl_mod_communication.html#comm_deferred", null ]
    ] ],
    [ "`src/remeshing/` — Isotropic surface remeshing", "mftl_mod_remeshing.html", [
      [ "Notation", "mftl_mod_remeshing.html#rem_notation", null ],
      [ "The serial algorithm", "mftl_mod_remeshing.html#rem_algorithm", [
        [ "The length band", "mftl_mod_remeshing.html#rem_band", null ],
        [ "The sweep order", "mftl_mod_remeshing.html#rem_order", null ]
      ] ],
      [ "Operators under implicit indexing", "mftl_mod_remeshing.html#rem_operators", [
        [ "The collapse predicate", "mftl_mod_remeshing.html#rem_approval", null ],
        [ "Valence optimisation", "mftl_mod_remeshing.html#autotoc_md49", null ]
      ] ],
      [ "Features and smoothing", "mftl_mod_remeshing.html#rem_features", [
        [ "Smoothing is a projection", "mftl_mod_remeshing.html#rem_smoothing", null ],
        [ "Feature detection on a smooth surface", "mftl_mod_remeshing.html#rem_features_off", null ]
      ] ],
      [ "Compaction", "mftl_mod_remeshing.html#rem_compaction", null ],
      [ "Distributed remeshing: the obstacle", "mftl_mod_remeshing.html#rem_parallel", [
        [ "Dispatch", "mftl_mod_remeshing.html#rem_dispatch", null ]
      ] ],
      [ "The spanning driver", "mftl_mod_remeshing.html#rem_spanning", [
        [ "One pass", "mftl_mod_remeshing.html#rem_spanning_flow", null ],
        [ "The geometric guarantee", "mftl_mod_remeshing.html#rem_covering", null ],
        [ "The phase table", "mftl_mod_remeshing.html#rem_phase_table", null ],
        [ "The frozen share", "mftl_mod_remeshing.html#rem_frozen_share", null ],
        [ "\"Frozen\" is derived locally, and exactly", "mftl_mod_remeshing.html#rem_frozen", null ],
        [ "The band is measured", "mftl_mod_remeshing.html#rem_band_width", null ],
        [ "A shifted plane needs a floor", "mftl_mod_remeshing.html#rem_shift_floor", null ],
        [ "Global ids", "mftl_mod_remeshing.html#rem_ids", null ],
        [ "The convergence certificate", "mftl_mod_remeshing.html#rem_certificate", null ],
        [ "Coarsening", "mftl_mod_remeshing.html#rem_coarsen", null ]
      ] ],
      [ "The dispersed driver", "mftl_mod_remeshing.html#rem_dispersed", [
        [ "One pass", "mftl_mod_remeshing.html#rem_dispersed_flow", null ],
        [ "Load balance", "mftl_mod_remeshing.html#rem_balance", [
          [ "One rank decides each body", "mftl_mod_remeshing.html#rem_balance_local", null ],
          [ "A negotiation, not a greedy", "mftl_mod_remeshing.html#rem_balance_negotiate", null ]
        ] ],
        [ "Coarsening as a yardstick", "mftl_mod_remeshing.html#rem_yardstick", null ]
      ] ],
      [ "All the MPI is in one file", "mftl_mod_remeshing.html#rem_mpi_confined", null ],
      [ "<span class=\"tt\">parallel_phase_budget</span>", "mftl_mod_remeshing.html#rem_budget", null ],
      [ "Reading the diagnostics", "mftl_mod_remeshing.html#rem_diagnostics", null ]
    ] ],
    [ "`src/bvh/` — LBVH and contact detection", "mftl_mod_bvh.html", [
      [ "The ensemble pipeline", "mftl_mod_bvh.html#bvh_overview", null ],
      [ "Construction", "mftl_mod_bvh.html#bvh_build", [
        [ "Primitives", "mftl_mod_bvh.html#bvh_prims", null ],
        [ "Morton key", "mftl_mod_bvh.html#bvh_morton", null ],
        [ "Radix split", "mftl_mod_bvh.html#bvh_radix", null ],
        [ "Fit and refit", "mftl_mod_bvh.html#bvh_refit", null ],
        [ "Refit or rebuild", "mftl_mod_bvh.html#bvh_refitguard", null ],
        [ "Attaching a halo rebuilds", "mftl_mod_bvh.html#bvh_setphalo", null ],
        [ "Node layout", "mftl_mod_bvh.html#bvh_node", null ]
      ] ],
      [ "Periodicity is two problems", "mftl_mod_bvh.html#bvh_periodic", null ],
      [ "The contact envelope", "mftl_mod_bvh.html#bvh_envelope", null ],
      [ "The traversal", "mftl_mod_bvh.html#bvh_traverse", [
        [ "Descent", "mftl_mod_bvh.html#bvh_descent", null ],
        [ "Who reports a contact", "mftl_mod_bvh.html#bvh_ownership", null ],
        [ "The batch", "mftl_mod_bvh.html#bvh_batch", null ]
      ] ],
      [ "The narrow phase", "mftl_mod_bvh.html#bvh_narrow", [
        [ "The orientation predicate", "mftl_mod_bvh.html#bvh_orient", null ],
        [ "Guigue–Devillers", "mftl_mod_bvh.html#bvh_gd", null ],
        [ "The coplanar case", "mftl_mod_bvh.html#bvh_coplanar", null ],
        [ "Exact distance between disjoint triangles", "mftl_mod_bvh.html#bvh_distance", [
          [ "Degeneracy tests are dimensionless", "mftl_mod_bvh.html#bvh_dimensionless", null ]
        ] ],
        [ "Why only orient3d is adaptive", "mftl_mod_bvh.html#bvh_adaptive", [
          [ "The filter", "mftl_mod_bvh.html#bvh_escalation", null ],
          [ "Error-free transformations", "mftl_mod_bvh.html#bvh_eft", null ],
          [ "<span class=\"tt\">-ffp-contract=off</span> is correctness", "mftl_mod_bvh.html#bvh_fma", null ],
          [ "Cost and benefit", "mftl_mod_bvh.html#bvh_orientcost", null ]
        ] ]
      ] ],
      [ "Cost", "mftl_mod_bvh.html#bvh_cost", null ],
      [ "Open issues", "mftl_mod_bvh.html#bvh_deferred", null ]
    ] ],
    [ "`src/topology_change/` — Breakup and coalescence", "mftl_mod_topology_change.html", [
      [ "Notation", "mftl_mod_topology_change.html#topo_notation", null ],
      [ "The pipeline", "mftl_mod_topology_change.html#topo_pipeline", null ],
      [ "Detection", "mftl_mod_topology_change.html#topo_detect", null ],
      [ "The lattice", "mftl_mod_topology_change.html#topo_lattice", null ],
      [ "The signed distance", "mftl_mod_topology_change.html#topo_sdf", null ],
      [ "The bias", "mftl_mod_topology_change.html#topo_bias", null ],
      [ "Marching cubes", "mftl_mod_topology_change.html#topo_mc", null ],
      [ "Bodies from triangle soup", "mftl_mod_topology_change.html#topo_split", null ],
      [ "Rims", "mftl_mod_topology_change.html#topo_rims", null ],
      [ "After the extraction", "mftl_mod_topology_change.html#topo_after", null ],
      [ "Design alternatives", "mftl_mod_topology_change.html#topo_departures", null ],
      [ "What is tested, and how", "mftl_mod_topology_change.html#topo_tests", null ],
      [ "Costs, and what is not done", "mftl_mod_topology_change.html#topo_deferred", null ]
    ] ],
    [ "`src/io/` — Mesh output", "mftl_mod_io.html", [
      [ "Two writers, two contracts", "mftl_mod_io.html#io_contracts", null ],
      [ "Only owned entities are written", "mftl_mod_io.html#io_owned", null ],
      [ "Periodic unwrapping", "mftl_mod_io.html#io_unwrap", null ],
      [ "Encoding and layout", "mftl_mod_io.html#io_encoding", [
        [ "Placing blocks in the shared file", "mftl_mod_io.html#io_layout", null ],
        [ "Which layout is faster depends on the machine", "mftl_mod_io.html#autotoc_md36", null ]
      ] ]
    ] ]
];