# ══════════════════════════════════════════════════════════════════════════════
#  MFTL2_Documentation -- the CMake route to the Doxygen manual
#
#  This project compiles nothing. It exists so that the manual can be built by
#  the same tool a cluster's CI already drives, and it is the second of the two
#  routes the Doxyfile template is written for:
#
#      cmake -S . -B build && cmake --build build --target docs
#      python3 build_docs.py
#
#  Both substitute the same placeholders into doxygen/Doxyfile.in, so they
#  cannot drift apart. That template carries TWO roots -- this repository and
#  the LIBRARY checkout it documents -- and finding the second is the only
#  thing this file does that a normal Doxygen project would not need.
#
#  The target is NOT attached to `all`: `cmake --build build` does nothing at
#  all, only `--target docs` runs Doxygen. It stays that way so that adding this
#  directory to a super-build cannot make anyone pay for Graphviz.
# ══════════════════════════════════════════════════════════════════════════════
cmake_minimum_required(VERSION 3.13)

project(MFTL2_Documentation LANGUAGES NONE)

option(MFTL_DOCS_WARN_AS_ERROR "Fail the 'docs' target on a Doxygen warning" OFF)
option(MFTL_DOCS_LATEX         "Also emit LaTeX sources for a PDF"           OFF)

# --- Where is the library? ---------------------------------------------------
#
# Same resolution order as mftl_paths.py, so the two routes agree about which
# checkout they are documenting: an explicit answer first, then a sibling
# directory. A wrong answer here produces an EMPTY manual rather than an error
# from Doxygen, so the tree is validated before it is accepted.
set(MFTL_SOURCE_DIR "" CACHE PATH "Path to the MFTL library checkout")

if(NOT MFTL_SOURCE_DIR AND DEFINED ENV{MFTL_SOURCE_DIR})
    set(MFTL_SOURCE_DIR "$ENV{MFTL_SOURCE_DIR}")
endif()

if(NOT MFTL_SOURCE_DIR AND EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/mftl-source.txt")
    file(READ "${CMAKE_CURRENT_SOURCE_DIR}/mftl-source.txt" _mftl_configured)
    string(REGEX REPLACE "#[^\n]*" "" _mftl_configured "${_mftl_configured}")
    string(STRIP "${_mftl_configured}" MFTL_SOURCE_DIR)
endif()

if(NOT MFTL_SOURCE_DIR)
    foreach(_candidate MFTL2 MFTL)
        if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/../${_candidate}/include/mftl_core.h")
            get_filename_component(MFTL_SOURCE_DIR
                                   "${CMAKE_CURRENT_SOURCE_DIR}/../${_candidate}" ABSOLUTE)
            break()
        endif()
    endforeach()
endif()

if(NOT MFTL_SOURCE_DIR OR NOT EXISTS "${MFTL_SOURCE_DIR}/include/mftl_core.h")
    message(FATAL_ERROR
        "Could not find the MFTL library sources.\n"
        "  This repository documents a checkout of MFTL that lives elsewhere.\n"
        "  Point it at one with:\n"
        "    cmake -S . -B build -DMFTL_SOURCE_DIR=/path/to/MFTL2\n"
        "  or export MFTL_SOURCE_DIR, or write the path into mftl-source.txt.")
endif()

get_filename_component(MFTL_SOURCE_DIR "${MFTL_SOURCE_DIR}" ABSOLUTE)

# The version is read from the library, not repeated here, so the two
# repositories cannot report different numbers for the same manual.
file(READ "${MFTL_SOURCE_DIR}/CMakeLists.txt" _mftl_cmakelists)
if(_mftl_cmakelists MATCHES "project[ \t]*\\([^)]*VERSION[ \t]+([0-9][0-9.]*)")
    set(MFTL_VERSION "${CMAKE_MATCH_1}")
else()
    set(MFTL_VERSION "2.0")
endif()

# --- Doxygen -----------------------------------------------------------------
find_package(Doxygen REQUIRED)

# Graphviz is optional. Without it the manual is complete except for the call,
# caller, include and directory graphs.
if(DOXYGEN_DOT_FOUND)
    set(MFTL_DOCS_HAVE_DOT "YES")
    get_filename_component(MFTL_DOCS_DOT_PATH "${DOXYGEN_DOT_EXECUTABLE}" DIRECTORY)
else()
    set(MFTL_DOCS_HAVE_DOT "NO")
    set(MFTL_DOCS_DOT_PATH "")
    message(STATUS "Graphviz 'dot' not found -- documentation graphs disabled.")
endif()

# The measurement document is optional -- MFTL2 keeps docs/ out of its
# repository -- and without it the Analysis page that introduces it is left out
# too. Same rule as mftl_paths.measurement_substitutions().
if(EXISTS "${MFTL_SOURCE_DIR}/docs/analysis.md" AND NOT "$ENV{MFTL_DOCS_MEASUREMENTS}" STREQUAL "0")
    set(MFTL_DOCS_MEASUREMENTS_INPUT   "${MFTL_SOURCE_DIR}/docs/analysis.md")
    set(MFTL_DOCS_MEASUREMENTS_EXCLUDE "")
else()
    set(MFTL_DOCS_MEASUREMENTS_INPUT   "")
    set(MFTL_DOCS_MEASUREMENTS_EXCLUDE "${CMAKE_CURRENT_SOURCE_DIR}/pages/analysis.md")
    message(STATUS "No docs/analysis.md in the library -- the Analysis section is left out.")
endif()

set(MFTL_DOCS_SOURCE_DIR "${MFTL_SOURCE_DIR}")
set(MFTL_DOCS_DIR        "${CMAKE_CURRENT_SOURCE_DIR}")
set(MFTL_DOCS_OUTPUT_DIR "${CMAKE_BINARY_DIR}/docs")

set(MFTL_DOXYFILE_IN  "${CMAKE_CURRENT_SOURCE_DIR}/doxygen/Doxyfile.in")
set(MFTL_DOXYFILE_OUT "${MFTL_DOCS_OUTPUT_DIR}/Doxyfile")

# @ONLY: the template contains shell and Doxygen syntax that uses ${...}, which
# must survive untouched. Only @PLACEHOLDER@ is substituted.
configure_file("${MFTL_DOXYFILE_IN}" "${MFTL_DOXYFILE_OUT}" @ONLY)

if(MFTL_DOCS_LATEX)
    file(READ "${MFTL_DOXYFILE_OUT}" _doxyfile)
    string(REPLACE "GENERATE_LATEX         = NO" "GENERATE_LATEX         = YES"
                   _doxyfile "${_doxyfile}")
    file(WRITE "${MFTL_DOXYFILE_OUT}" "${_doxyfile}")
endif()

set(MFTL_DOCS_STAMP "${MFTL_DOCS_OUTPUT_DIR}/html/index.html")

# The manual is regenerated when a source, a page or the configuration changes
# -- not on every build of the target. Both trees are watched, because a doc
# comment and a guide page are equally able to change the output.
file(GLOB_RECURSE MFTL_DOCS_DEPENDS CONFIGURE_DEPENDS
     "${MFTL_SOURCE_DIR}/include/*.h"
     "${MFTL_SOURCE_DIR}/src/*.c"
     "${MFTL_SOURCE_DIR}/src/*.h"
     "${MFTL_SOURCE_DIR}/src/*.md"
     "${MFTL_SOURCE_DIR}/docs/*.md"
     "${CMAKE_CURRENT_SOURCE_DIR}/pages/*.md"
     "${CMAKE_CURRENT_SOURCE_DIR}/doxygen/*")

add_custom_command(
    OUTPUT  "${MFTL_DOCS_STAMP}"
    COMMAND ${DOXYGEN_EXECUTABLE} "${MFTL_DOXYFILE_OUT}"
    DEPENDS "${MFTL_DOXYFILE_OUT}" ${MFTL_DOCS_DEPENDS}
    WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
    COMMENT "Generating the MFTL manual with Doxygen"
    VERBATIM)

add_custom_target(docs DEPENDS "${MFTL_DOCS_STAMP}")

# Doxygen exits 0 even when it emits warnings, so "warnings are the acceptance
# criterion" has to be enforced on the log rather than on the exit code.
if(MFTL_DOCS_WARN_AS_ERROR)
    add_custom_command(TARGET docs POST_BUILD
        COMMAND ${CMAKE_COMMAND}
                -DLOG=${MFTL_DOCS_OUTPUT_DIR}/doxygen-warnings.log
                -P ${CMAKE_CURRENT_SOURCE_DIR}/doxygen/check_warnings.cmake
        VERBATIM)
endif()

add_custom_command(TARGET docs POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E echo "MFTL manual: ${MFTL_DOCS_STAMP}"
    VERBATIM)

message(STATUS "-------------------------------------------------")
message(STATUS "MFTL Documentation Configuration")
message(STATUS "-------------------------------------------------")
message(STATUS "Library sources  : ${MFTL_SOURCE_DIR}")
message(STATUS "Library version  : ${MFTL_VERSION}")
message(STATUS "Documentation    : ${MFTL_DOCS_DIR}")
message(STATUS "Doxygen          : ${DOXYGEN_EXECUTABLE}")
message(STATUS "Graphviz (dot)   : ${MFTL_DOCS_HAVE_DOT}")
message(STATUS "Warnings fatal   : ${MFTL_DOCS_WARN_AS_ERROR}")
message(STATUS "Output Directory : ${MFTL_DOCS_OUTPUT_DIR}")
message(STATUS "-------------------------------------------------")
message(STATUS "Build it with: cmake --build ${CMAKE_BINARY_DIR} --target docs")
message(STATUS "The web manual (MkDocs Material) is: python3 build_mkdocs.py")
