#!/bin/bash
set -eo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"

function log() { echo "$*" >&2 ; }

if [[ "$GITHUB_ACTIONS" == "true" ]]; then
    function start-group() { log "::group::$*" ; }
    function end-group() { log "::endgroup::" ; }
else
    function start-group() { log "=== $* ===" ; }
    function end-group() { : ; }
fi


function test_package()
{
    local pkg_dir="$1"
    local fails=""

    start-group "🧪 Testing package '$pkg_dir'"

    bash -c "cd '$pkg_dir' && uv sync" || fails+="sync "
    bash -c "cd '$pkg_dir' && uv run ruff check" || fails+="style "
    bash -c "cd '$pkg_dir' && uv run pytest -v" || fails+="tests "

    end-group

    if [[ -n "$fails" ]]; then
        log "    ❌ '$pkg_dir' - tests failed: $fails"
        return 1
    else
        log "    ✅ '$pkg_dir' - all tests passed"
    fi
}

test_package "$REPO_ROOT" || FAILED=1

if [[ $FAILED -ne 0 ]]; then
    log "Some tests failed"
    exit 1
else
    log "All tests passed successfully"
fi

