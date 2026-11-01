#!/bin/sh
set -eu

source_path=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
clients='codex claude'
bank_path=''
python_runtime='3.12'
semantic=0
while [ "$#" -gt 0 ]; do
    case "$1" in
        --help|-h)
            printf '%s\n' 'Install Maverick Bank: --source PATH_OR_WHEEL --clients codex claude [--bank PATH] [--python 3.12] [--semantic]'
            exit 0 ;;
        --source|--bank|--python)
            option=$1
            shift
            [ "$#" -gt 0 ] || { printf '%s\n' "Missing value for $option" >&2; exit 2; }
            case "$option" in --source) source_path=$1 ;; --bank) bank_path=$1 ;; --python) python_runtime=$1 ;; esac
            shift ;;
        --clients)
            shift
            clients=''
            while [ "$#" -gt 0 ]; do
                case "$1" in --*) break ;; codex|claude) clients="$clients $1" ;; *) printf '%s\n' "Unknown client: $1" >&2; exit 2 ;; esac
                shift
            done
            [ -n "$clients" ] || { printf '%s\n' 'Select codex, claude, or both.' >&2; exit 2; } ;;
        --semantic) semantic=1; shift ;;
        *) printf '%s\n' "Unknown option: $1" >&2; exit 2 ;;
    esac
done
command -v git >/dev/null 2>&1 || { printf '%s\n' 'Git is required for local history. Install Git and retry.' >&2; exit 2; }
if command -v uv >/dev/null 2>&1; then
    uv_executable=$(command -v uv)
else
    uv_directory=${UV_UNMANAGED_INSTALL:-"$HOME/.local/bin"}
    mkdir -p "$uv_directory"
    uv_installer=$(mktemp "$uv_directory/uv-install.XXXXXX")
    trap 'rm -f -- "$uv_installer"' EXIT HUP INT TERM
    printf '%s\n' 'Installing uv from the official Astral distribution...'
    if command -v curl >/dev/null 2>&1; then
        curl -LsSf 'https://astral.sh/uv/0.12.23/install.sh' -o "$uv_installer"
    elif command -v wget >/dev/null 2>&1; then
        wget -q 'https://astral.sh/uv/0.12.23/install.sh' -O "$uv_installer"
    else
        printf '%s\n' 'Install curl or wget to provision uv.' >&2
        exit 2
    fi
    UV_UNMANAGED_INSTALL="$uv_directory" sh "$uv_installer"
    uv_executable="$uv_directory/uv"
fi
printf '%s\n' 'Installing the isolated Maverick Bank runtime...'
if [ "$semantic" -eq 1 ]; then
    "$uv_executable" tool install --python "$python_runtime" --force --with 'fastembed>=0.7,<1' "$source_path"
else
    "$uv_executable" tool install --python "$python_runtime" --force "$source_path"
fi
bin_directory=$("$uv_executable" tool dir --bin)
application="$bin_directory/maverick-bank"
[ -x "$application" ] || { printf '%s\n' "Installed executable missing: $application" >&2; exit 2; }
if [ -n "$bank_path" ]; then
    "$application" init --bank "$bank_path"
    # $clients contains only the two validated literal client names; splitting is intentional.
    # shellcheck disable=SC2086
    "$application" install --bank "$bank_path" --clients $clients --scope user
    if [ "$semantic" -eq 1 ]; then "$application" semantic install --bank "$bank_path"; fi
    "$application" doctor --bank "$bank_path" --mcp
else
    "$application" init
    # shellcheck disable=SC2086
    "$application" install --clients $clients --scope user
    if [ "$semantic" -eq 1 ]; then "$application" semantic install; fi
    "$application" doctor --mcp
fi
printf '%s\n' "Installed: $application" 'Start a new Claude Code or Codex session and follow the README first-memory check.'
