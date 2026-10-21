#!/bin/bash
# Apply the workstation playbooks on the Vanilla OS host.
#   ./run.sh                 everything: system (one pkexec prompt), user, apx containers
#   ./run.sh user|system|containers   one play
#   ./run.sh ... --check --diff       extra args go to ansible-playbook
#
# The host is immutable and has no sudo, pip or git, so Ansible lives in a repo-local venv made
# with a pinned uv (which brings its own Python). Root work runs as one pkexec'd play.
# Works from inside an apx container too: it re-runs itself on the host through host-spawn.
set -euo pipefail

UV_VERSION=0.13.1
PYTHON_VERSION=3.13
repo=$(cd "$(dirname "$0")" && pwd)
cache=$repo/.cache
venv=$repo/.venv
export ANSIBLE_CONFIG=$repo/ansible.cfg
export ANSIBLE_COLLECTIONS_PATH=$repo/.cache/collections
export UV_PYTHON_INSTALL_DIR=$cache/python UV_CACHE_DIR=$cache/uv-cache

# Run on the host. apx-vso-native has its own session bus where host-spawn exits 127, so use
# the host's bus explicitly (same as __twingate_host in bash_aliases).
if [[ -n ${CONTAINER_ID-} ]]; then
    bus=/run/host/run/user/$UID/bus
    [[ -S $bus ]] && export DBUS_SESSION_BUS_ADDRESS=unix:path=$bus
    exec host-spawn "$repo/run.sh" "$@"
fi

[[ -f $repo/vars/vars.yml ]] || {
    echo "Copy vars/vars.example.yml to vars/vars.yml and fill it in first" >&2
    exit 1
}

# Bootstrap: uv -> venv -> ansible-core + collections. Re-runs are no-ops.
if [[ ! -x $cache/uv/uv ]]; then
    mkdir -p "$cache/uv"
    curl -fsSL "https://github.com/astral-sh/uv/releases/download/$UV_VERSION/uv-x86_64-unknown-linux-musl.tar.gz" |
        tar -xz -C "$cache/uv" --strip-components=1
fi
if [[ ! -x $venv/bin/ansible-playbook ]]; then
    "$cache/uv/uv" venv --quiet --python "$PYTHON_VERSION" --python-preference only-managed "$venv"
    # psutil: community.general.dconf
    VIRTUAL_ENV=$venv "$cache/uv/uv" pip install --quiet 'ansible-core>=2.19,<2.21' psutil
fi
"$venv/bin/ansible-galaxy" collection install -r "$repo/requirements.yml" -p "$ANSIBLE_COLLECTIONS_PATH" >/dev/null

play() { "$venv/bin/ansible-playbook" -i "$repo/inventory" "$repo/$1.yml" "${@:2}"; }

system() {
    # pkexec drops the environment, so pass what the playbook needs explicitly
    pkexec env ANSIBLE_CONFIG="$ANSIBLE_CONFIG" ANSIBLE_COLLECTIONS_PATH="$ANSIBLE_COLLECTIONS_PATH" \
        ANSIBLE_LOCAL_TEMP=/tmp/.ansible-root ANSIBLE_REMOTE_TEMP=/tmp/.ansible-root \
        "$venv/bin/ansible-playbook" -i "$repo/inventory" "$repo/system.yml" "$@"
}

case ${1-} in
    system) shift; system "$@" ;;
    user) shift; play user "$@" ;;
    containers) shift; play containers "$@" ;;
    *)
        system "$@"
        play user "$@"
        play containers "$@"
        ;;
esac
