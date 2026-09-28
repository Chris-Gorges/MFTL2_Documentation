var index =
[
    [ "Start here", "index.html#autotoc_md158", null ],
    [ "What the library does today", "index.html#autotoc_md160", null ],
    [ "The shortest complete program", "index.html#autotoc_md162", null ],
    [ "Reading order for the theory", "index.html#autotoc_md164", null ],
    [ "Measured results that contradict the design's own predictions", "index.html#autotoc_md166", null ],
    [ "Author and licence", "index.html#autotoc_md168", null ],
    [ "Architecture", "mftl_page_architecture.html", [
      [ "The one idea", "mftl_page_architecture.html#arch_one_idea", [
        [ "Both live in one allocation per entity class", "mftl_page_architecture.html#arch_one_allocation", null ]
      ] ],
      [ "Three invariants every module may assume", "mftl_page_architecture.html#arch_invariants", [
        [ "1. Half-edges are triangle-indexed", "mftl_page_architecture.html#arch_inv_implicit", null ],
        [ "2. Ownership is a prefix", "mftl_page_architecture.html#arch_inv_prefix", null ],
        [ "3. Positions live in the SoA and only there", "mftl_page_architecture.html#arch_inv_positions", null ]
      ] ],
      [ "Derived arrays and staleness", "mftl_page_architecture.html#arch_derived", null ],
      [ "Header layering", "mftl_page_architecture.html#arch_layering", null ],
      [ "Object model: Ensemble → Domain → Objects → pools", "mftl_page_architecture.html#arch_object_model", null ],
      [ "Where a geometry function lives", "mftl_page_architecture.html#arch_geometry_split", null ],
      [ "Conventions", "mftl_page_architecture.html#arch_conventions", null ]
    ] ],
    [ "Building, testing and generating this manual", "mftl_page_building.html", [
      [ "Requirements", "mftl_page_building.html#build_requirements", null ],
      [ "Building the library", "mftl_page_building.html#build_library", [
        [ "Architecture flags", "mftl_page_building.html#build_arch", null ],
        [ "CMake options", "mftl_page_building.html#build_options", null ]
      ] ],
      [ "Running the tests", "mftl_page_building.html#build_tests", [
        [ "Why a test is registered at several rank counts", "mftl_page_building.html#build_ranks", null ],
        [ "The source-level test", "mftl_page_building.html#build_source_test", null ]
      ] ],
      [ "Generating this manual", "mftl_page_building.html#build_docs", [
        [ "Just looking at it — one command", "mftl_page_building.html#build_docs_view", null ],
        [ "Finding the library", "mftl_page_building.html#build_docs_source", null ],
        [ "Standalone — nothing to configure", "mftl_page_building.html#build_docs_standalone", null ],
        [ "Through CMake", "mftl_page_building.html#build_docs_cmake", null ],
        [ "What the generated manual contains", "mftl_page_building.html#build_docs_contents", null ],
        [ "Warnings are the acceptance criterion", "mftl_page_building.html#build_docs_warnings", null ]
      ] ],
      [ "The web manual — MkDocs Material", "mftl_page_building.html#build_site", [
        [ "There is still one source per subject", "mftl_page_building.html#build_site_sources", null ],
        [ "Which manual answers which question", "mftl_page_building.html#build_site_split", null ]
      ] ],
      [ "The pre-built manual", "mftl_page_building.html#build_export", null ],
      [ "Header hygiene", "mftl_page_building.html#build_hygiene", null ]
    ] ],
    [ "The per-timestep loop", "mftl_page_timestep.html", [
      [ "Without redistribution", "mftl_page_timestep.html#ts_no_redist", null ],
      [ "With redistribution", "mftl_page_timestep.html#ts_redist", null ],
      [ "What a redistribution leaves behind", "mftl_page_timestep.html#ts_redist_leaves", null ],
      [ "Vertex normals and the vertex-complete halo", "mftl_page_timestep.html#ts_vertex_normals", null ],
      [ "Which calls are collective", "mftl_page_timestep.html#ts_collective", null ],
      [ "Adding remeshing to the loop", "mftl_page_timestep.html#ts_remeshing", null ],
      [ "Adding contact detection to the loop", "mftl_page_timestep.html#ts_contact", null ],
      [ "Adding topology changes to the loop", "mftl_page_timestep.html#ts_topology", null ]
    ] ],
    [ "Invariants worth preserving", "mftl_page_invariants.html", [
      [ "Geometry", "mftl_page_invariants.html#inv_geometry", [
        [ "A normal is always a unit vector, at every scale", "mftl_page_invariants.html#inv_unit_normal", null ],
        [ "Face normals point outward, everywhere", "mftl_page_invariants.html#inv_winding", null ],
        [ "Never compare two identical vectors with <span class=\"tt\">acos(a·b)</span>", "mftl_page_invariants.html#inv_no_acos", null ]
      ] ],
      [ "Topology", "mftl_page_invariants.html#inv_topology", [
        [ "\"No twin\" and \"mesh boundary\" are different statements", "mftl_page_invariants.html#inv_boundary", null ],
        [ "A boundary vertex has one more neighbour than incident triangles", "mftl_page_invariants.html#inv_open_fan", null ],
        [ "A half-edge's global ID is <span class=\"tt\">3 * triangle_gid + k</span>, mesh-wide", "mftl_page_invariants.html#inv_he_gid", null ],
        [ "Global IDs are a dense permutation of [0, n) per entity class", "mftl_page_invariants.html#inv_dense_gid", null ]
      ] ],
      [ "I/O", "mftl_page_invariants.html#inv_io", [
        [ "Only OWNED entities go into a <span class=\"tt\">.vtu</span>", "mftl_page_invariants.html#inv_owned_only", null ],
        [ "The periodic-wrap test has no tolerance, on purpose", "mftl_page_invariants.html#inv_wrap", null ],
        [ "MFTLWriteVtu() must never write <span class=\"tt\">tris.area</span> or <span class=\"tt\">tris.normal</span>", "mftl_page_invariants.html#inv_no_stale_fields", null ]
      ] ],
      [ "Communication", "mftl_page_invariants.html#inv_comm", [
        [ "An extent is a centre plus a half-width, never a (lo, hi) box", "mftl_page_invariants.html#inv_extent", null ],
        [ "A pre-filter must be strictly MORE permissive than the test it short-cuts", "mftl_page_invariants.html#inv_prefilter", null ],
        [ "A spatial ghost is a triangle in a SHADOW OBJECT", "mftl_page_invariants.html#inv_shadow", null ]
      ] ],
      [ "Remeshing", "mftl_page_invariants.html#inv_remesh", [
        [ "MFTL_FLAG_FROZEN means REPLICATED, not \"near a cut plane\"", "mftl_page_invariants.html#inv_frozen", null ],
        [ "A shifted cut plane needs a FLOOR, not a truncation", "mftl_page_invariants.html#inv_shifted_floor", null ],
        [ "Remeshing reaches the network through its own file", "mftl_page_invariants.html#inv_mpi_confined", null ],
        [ "A rank must not judge work it only holds as a GHOST", "mftl_page_invariants.html#inv_no_ghost_judgement", null ],
        [ "Every clause of an approval predicate is silent when removed", "mftl_page_invariants.html#inv_approval", null ],
        [ "Feature classification must describe the mesh being SMOOTHED", "mftl_page_invariants.html#inv_features_twice", null ],
        [ "Smoothing is a PROJECTION", "mftl_page_invariants.html#inv_smoothing_projection", null ],
        [ "Two feature edges make a ridge point only if the curve runs STRAIGHT", "mftl_page_invariants.html#inv_corner_angle", null ]
      ] ],
      [ "Contact detection", "mftl_page_invariants.html#inv_bvh", [
        [ "Periodicity is two problems, and they need two different fixes", "mftl_page_invariants.html#inv_bvh_periodic", null ],
        [ "The contact envelope scales with the body, not the process count", "mftl_page_invariants.html#inv_envelope", null ],
        [ "A distributed contact is reported by the A-side owner, and only that rank", "mftl_page_invariants.html#inv_a_side", null ],
        [ "MFTL_Orient3D is adaptive; nothing else in src/bvh/ is", "mftl_page_invariants.html#inv_adaptive", null ]
      ] ],
      [ "Topology changes", "mftl_page_invariants.html#inv_topology_change", [
        [ "The reconstructed surface is independent of the process count", "mftl_page_invariants.html#inv_topo_partition", null ],
        [ "An event is classified by the side its gap is on", "mftl_page_invariants.html#inv_topo_side", null ],
        [ "The size floor is taken twice", "mftl_page_invariants.html#inv_topo_floor", null ]
      ] ],
      [ "How the tests express these", "mftl_page_invariants.html#inv_test_helpers", null ]
    ] ],
    [ "The eleven modules", "mftl_page_modules.html", "mftl_page_modules" ]
];