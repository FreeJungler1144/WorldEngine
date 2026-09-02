# check_source_rules.cmake — the two rules that were prose and nothing else.
#
# Run as part of the build, not the test suite, so it cannot be skipped by
# not running the tests. Invoked with -DINOP_SRC_ROOT=<repo>/src.
#
# Rule 1 (DESIGN section 1): inop.hpp and inop.cpp may only ever contain a
# rotor machine. Enforced as an include allowlist plus a scan for the
# symbols a modern primitive would arrive under.
#
# Rule 2: the deliberate refusal to fall back to rand() or
# std::random_device. Enforced over the logic, settings and interface
# layers.
#
# Both report the file, the line number and the line itself, and name the
# rule they are enforcing. A violation fails the build.

if(NOT DEFINED INOP_SRC_ROOT)
  message(FATAL_ERROR "check_source_rules.cmake needs -DINOP_SRC_ROOT=<path to src>")
endif()

set(_violations "")

# Comment lines are skipped by both scans. rng.cpp and generator.cpp both
# explain in prose why they do not use rand(), and a checker that cannot
# tell an explanation from a call would force those comments to be
# deleted -- exactly the wrong outcome for a rule that exists to be
# understood.
function(inop_is_comment line out)
  string(REGEX MATCH "^[ \t]*(//|\\*|/\\*)" _m "${line}")
  if(_m)
    set(${out} TRUE PARENT_SCOPE)
  else()
    set(${out} FALSE PARENT_SCOPE)
  endif()
endfunction()

function(inop_scan file patterns rule)
  if(NOT EXISTS "${file}")
    return()
  endif()
  file(STRINGS "${file}" _lines)
  set(_n 0)
  set(_found "")
  foreach(_line IN LISTS _lines)
    math(EXPR _n "${_n}+1")
    inop_is_comment("${_line}" _is_comment)
    if(_is_comment)
      continue()
    endif()
    string(TOLOWER "${_line}" _low)
    foreach(_pat IN LISTS patterns)
      string(REGEX MATCH "${_pat}" _m "${_low}")
      if(_m)
        list(APPEND _found "  ${file}:${_n}: ${_line}")
        break()
      endif()
    endforeach()
  endforeach()
  if(_found)
    set(_msg "${rule}\n")
    foreach(_f IN LISTS _found)
      string(APPEND _msg "${_f}\n")
    endforeach()
    set(_violations "${_violations}${_msg}" PARENT_SCOPE)
  endif()
endfunction()

# -- rule 1a: the cipher core include allowlist --------------------------
#
# Everything the rotor machine legitimately needs, and nothing that could
# bring a primitive with it. <random> is absent on purpose: the core must
# not generate anything, and a wheel is handed to it already wired.
set(INOP_CORE_ALLOWED_INCLUDES
  "inop.hpp" "cassert" "cstdint" "stdexcept" "string" "vector" "algorithm")

foreach(_f "${INOP_SRC_ROOT}/logic/inop.hpp" "${INOP_SRC_ROOT}/logic/inop.cpp")
  if(NOT EXISTS "${_f}")
    message(FATAL_ERROR "core purity check: ${_f} does not exist")
  endif()
  file(STRINGS "${_f}" _lines)
  set(_n 0)
  foreach(_line IN LISTS _lines)
    math(EXPR _n "${_n}+1")
    string(REGEX MATCH "^[ \t]*#[ \t]*include[ \t]*[<\"]([^>\"]+)[>\"]" _m "${_line}")
    if(_m)
      set(_hdr "${CMAKE_MATCH_1}")
      list(FIND INOP_CORE_ALLOWED_INCLUDES "${_hdr}" _idx)
      if(_idx EQUAL -1)
        string(APPEND _violations
          "DESIGN section 1: inop.hpp/inop.cpp may only ever contain a rotor machine.\n"
          "  <${_hdr}> is not on the allowlist for the cipher core.\n"
          "  ${_f}:${_n}: ${_line}\n"
          "  Allowed: ${INOP_CORE_ALLOWED_INCLUDES}\n"
          "  If this header is genuinely needed by a rotor machine, add it here\n"
          "  deliberately. Do not add it to route around the rule.\n")
      endif()
    endif()
  endforeach()
endforeach()

# -- rule 1b: the cipher core symbol scan --------------------------------
set(INOP_CORE_BANNED
  "(^|[^a-z0-9_])(sha1|sha256|sha512|sha3|md5|aes|hmac|openssl|sodium|blake2|chacha|poly1305)([^a-z0-9_]|$)"
  "(^|[^a-z0-9_])evp_"
  "std::hash"
  "#[ \t]*include[ \t]*<random>")

inop_scan("${INOP_SRC_ROOT}/logic/inop.hpp" "${INOP_CORE_BANNED}"
  "DESIGN section 1: the cipher core carries a modern primitive.")
inop_scan("${INOP_SRC_ROOT}/logic/inop.cpp" "${INOP_CORE_BANNED}"
  "DESIGN section 1: the cipher core carries a modern primitive.")

# -- rule 2: no weak randomness ------------------------------------------
#
# src/benchmark-debug is exempt and the exemption is the load-bearing part
# of this rule, so it is stated rather than hidden: benchmark_main.cpp
# seeds a std::mt19937 to manufacture message TEXT, never key material.
# Every wheel, notch, ring and key it uses comes from random_settings(),
# which draws from the OS source like everything else. The exemption is by
# directory, so an mt19937 appearing in logic/, settings/ or interface/
# still fails the build.
set(INOP_RNG_BANNED
  "(^|[^a-z0-9_])s?rand[ \t]*\\("
  "(^|[^a-z0-9_])(mt19937|random_device|default_random_engine|minstd_rand|ranlux)"
  "#[ \t]*include[ \t]*<random>")

foreach(_dir "logic" "settings" "interface")
  file(GLOB_RECURSE _srcs "${INOP_SRC_ROOT}/${_dir}/*.cpp" "${INOP_SRC_ROOT}/${_dir}/*.hpp")
  foreach(_f IN LISTS _srcs)
    inop_scan("${_f}" "${INOP_RNG_BANNED}"
      "RNG purity: no fallback to rand() or std::random_device. All randomness comes from rng.cpp and the OS source, because all of it is key material.")
  endforeach()
endforeach()

if(_violations)
  message(FATAL_ERROR
    "\n"
    "================================================================\n"
    " INOP source rule violation -- build refused\n"
    "================================================================\n"
    "${_violations}"
    "================================================================\n")
endif()

message(STATUS "INOP source rules: core purity and RNG purity both pass")
