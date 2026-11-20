"""Operator-only entrypoint for native Chema in an EXISTING systemd Owner unit.

This program replaces the old pilot worker script *only after* a root broker
has reserved (owner_id, workspace_id, generation), launched a DynamicUser unit
with the pinned read-only JM/Engine binds, and verified a 0700 StateDirectory.
It never creates/opens a synthetic Editor project. Browser and Owner HTTP
callers must never choose this script or its arguments.

The existing private Socket/Stage transport modules are deliberately reused
from the reviewed integration branch: no second web server or privileged
broker is introduced.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import os
import re
import secrets
import signal
import sys
import threading
from pathlib import Path

from urano.h4_instance import H4Instance, UNIT as _UNIT
_WORKSPACE = re.compile(
    r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}\Z")
# Operator-pinned read-only Engine. Must match the reviewed Engine gitlink
# of this release; mismatch silently mislabels native workers.
_H4_ENGINE_REVISION = "9af275b18535005e36bd289a68ceb4a1d2f6c506"
_REQUIRED_SITE = (
    "numpy", "scipy", "numba", "librosa", "soundfile",
    "pyloudnorm", "matchering",
)


class NativeSystemdOwnerError(ValueError):
    """Operator or persistent runtime is not a verified Owner worker."""


def trusted_native_worker_args(argv: list[str], *,
                               state_directory: str,
                               runtime_root: Path,
                               runtime_base: Path = Path("/run"),
                               systemd_state_parent: Path = Path("/var/lib"),
                               systemd_link_uid: int = 0):
    """Strict existing systemd argv; never accept paths, IDs from HTTP."""
    if (len(argv) not in (6, 8) or
            argv[4:6] != ["--jm-bundle", "/opt/montara-jm"] or
            not _UNIT.fullmatch(argv[1]) or
            not _WORKSPACE.fullmatch(argv[2]) or
            not re.fullmatch(r"[1-9][0-9]*", argv[3]) or
            argv[0] != "/opt/montara-engine"):
        raise NativeSystemdOwnerError("Untrusted pinned worker invocation")
    limit = 256
    if len(argv) == 8:
        if (argv[6] != "--private-proxy-limit-mib" or
                not re.fullmatch(r"(?:[0-9]{3,4})", argv[7])):
            raise NativeSystemdOwnerError("Untrusted proxy quota")
        limit = int(argv[7])
        if not 256 <= limit <= 4096:
            raise NativeSystemdOwnerError("Untrusted proxy quota")
    unit, workspace, generation = argv[1], argv[2], int(argv[3])
    if (not isinstance(state_directory, str) or ":" in state_directory
            or not state_directory or not isinstance(runtime_root, Path)):
        raise NativeSystemdOwnerError("One private StateDirectory is required")
    state = Path(state_directory)
    if (not state.is_dir() or not re.fullmatch(H4Instance.from_unit(unit).state_prefix + r"[a-f0-9]{40}", state.name)
            or state.stat().st_mode & 0o077 or not state.is_absolute()):
        raise NativeSystemdOwnerError("Unverified persistent Owner state")
    # systemd DynamicUser uses a ROOT-OWNED /var/lib/<name> symlink into
    # /var/lib/private/<name>. The already-running beta has this layout.
    # Accept *only* that precise systemd-created link, not arbitrary links.
    if state.is_symlink():
        if (state.parent != systemd_state_parent
                or state.readlink() != Path("private") / state.name
                or state.lstat().st_uid != systemd_link_uid
                or state.resolve(strict=True)
                    != (systemd_state_parent / "private" / state.name)
                        .resolve(strict=True)):
            raise NativeSystemdOwnerError("Untrusted StateDirectory symlink")
    runtime = Path(runtime_root)
    if (runtime.is_symlink() or not runtime.is_dir() or
            runtime.stat().st_mode & 0o077 or
            runtime != runtime_base / unit):
        raise NativeSystemdOwnerError("Unverified systemd runtime")
    return state.resolve(strict=True), runtime.resolve(strict=True), workspace, generation, limit


def vendor_site_for_native_worker(engine_root: Path) -> str:
    """Exact immutable wheel site used by Chema's Python child processes."""
    site = (Path(engine_root) / "site").resolve(strict=True)
    if not site.is_dir() or not all(
        (site / name).is_dir() or (site / (name + ".py")).is_file()
        for name in _REQUIRED_SITE
    ):
        raise NativeSystemdOwnerError("Pinned JM mixer dependencies unavailable")
    return str(site)


def prepare_native_owner_runtime(*, engine_root: Path, jm_root: Path,
                                 proxy_limit_mib: int) -> None:
    """Preserve current production JM pins, mixer path and proxy quota rules."""
    engine = Path(engine_root).resolve(strict=True)
    if Path(jm_root).is_symlink():
        raise NativeSystemdOwnerError("Untrusted JM/Engine bundle relationship")
    jm = Path(jm_root).resolve(strict=True)
    # Two read-only systemd binds may expose one immutable Engine directory
    # under different absolute paths. Compare the underlying inode, not the
    # spelling of the mountpoint (resolve() gives different path strings).
    if (jm.is_symlink() or not (jm / "app.py").is_file()
            or not (jm / "engine").samefile(engine / "engine")
            or not 256 <= proxy_limit_mib <= 4096):
        raise NativeSystemdOwnerError("Untrusted JM/Engine bundle relationship")

    from urano.jm_private_proxy_overlay import private_proxy_limit_mib
    private_proxy_limit_mib(proxy_limit_mib)
    if proxy_limit_mib > 256:
        source = (jm / "resumable_upload.py").read_text(encoding="utf-8")
        if ("max_original_file_bytes=limit" not in source or
                "MONTARA_PRIVATE_PROXY_LIMIT_MIB" not in source):
            raise NativeSystemdOwnerError("Reviewed private proxy quota missing")
        os.environ["MONTARA_PRIVATE_PROXY_LIMIT_MIB"] = str(proxy_limit_mib)
    else:
        os.environ.pop("MONTARA_PRIVATE_PROXY_LIMIT_MIB", None)

    pinned_site = vendor_site_for_native_worker(engine)
    # Same import precedence as the existing production worker: original JM
    # modules first, then pinned vendor packages and the exact Engine bundle.
    sys.path[:0] = [
        str(jm), pinned_site, str(engine / "app"), str(engine / "engine"),
    ]
    os.environ["PYTHONPATH"] = pinned_site
    os.environ["MONTARA_SESSION_TOKEN"] = secrets.token_hex(32)


def install_reviewed_main_mix_source_access(
        overlay_root: Path = Path("/opt/montara/broker-h4-main-native/main-mix-overlay-20261120")
) -> None:
    """MAIN worker-only, exact-hash source fix for Owner Session WAV previews.

    The immutable JM bundle remains pinned. Only its mixer source validator
    is overridden, using a root-owned reviewed source module. Import before
    the Flask app or any mixer source-access module is loaded; fail closed.
    """
    package = overlay_root / "mixer_adapter"
    module = package / "source_access.py"
    if (overlay_root.is_symlink() or not overlay_root.is_dir() or
            overlay_root.stat().st_uid != 0 or
            overlay_root.stat().st_mode & 0o022 or
            package.is_symlink() or not package.is_dir() or
            package.stat().st_uid != 0 or package.stat().st_mode & 0o022 or
            module.is_symlink() or not module.is_file() or
            module.stat().st_uid != 0 or
            module.stat().st_mode & 0o022 or
            (package / "__init__.py").exists()):
        raise NativeSystemdOwnerError("Untrusted MAIN-only Mixer source overlay")
    if hashlib.sha256(module.read_bytes()).hexdigest() != "d7a3f4416d9f91fe2a314ac178c4835607c1635fe39ef84d00267436a2fc1564":
        raise NativeSystemdOwnerError("MAIN Mixer source digest mismatch")
    if "mixer_adapter.source_access" in sys.modules:
        raise NativeSystemdOwnerError("Mixer source already imported before trusted override")
    sys.path.insert(0, str(overlay_root))
    imported = importlib.import_module("mixer_adapter.source_access")
    if Path(imported.__file__).resolve(strict=True) != module.resolve(strict=True):
        raise NativeSystemdOwnerError("MAIN Mixer source override failed")


def install_reviewed_main_song_transition_source(
        overlay_root: Path = Path("/opt/montara/broker-h4-main-native/main-mixer-channel-overlay-20261120")
) -> None:
    """MAIN-only verified Owner module overlay; original bundles untouched."""
    manifest = {
        "mixer_adapter/session.py": "affffdd2721576f679e0f8848f72b4938336d4fe41e41b500a1c2ea3c30b39fd",
        "full_session.py": "b48ec8f0e2d0a75b53979bf8d7622ceb7b60e4333881c8ee22282efe1f1c695e",
        "track_types.py": "1946f21b048dc7b50c8cb8a8dedc9c49c898942e3a6a5e463076777717fd2200",
    }
    if (overlay_root.is_symlink() or not overlay_root.is_dir() or
            overlay_root.stat().st_uid != 0 or overlay_root.stat().st_mode & 0o022):
        raise NativeSystemdOwnerError("Untrusted MAIN song transition source root")
    for name, expected in manifest.items():
        path = overlay_root / name
        if (path.is_symlink() or not path.is_file() or
                path.stat().st_uid != 0 or path.stat().st_mode & 0o022 or
                hashlib.sha256(path.read_bytes()).hexdigest() != expected):
            raise NativeSystemdOwnerError("MAIN song transition source digest mismatch")
    package = overlay_root / "mixer_adapter"
    if (package.is_symlink() or package.stat().st_uid != 0 or
            package.stat().st_mode & 0o022 or (package / "__init__.py").exists()):
        raise NativeSystemdOwnerError("Invalid reviewed MAIN session module package")
    for module_name in ("mixer_adapter.session", "full_session", "track_types"):
        if module_name in sys.modules:
            raise NativeSystemdOwnerError("Song boundary module imported before verified MAIN overlay")
    sys.path.insert(0, str(overlay_root))
    os.environ["MONTARA_VERIFIED_JM_ROOT"] = "/opt/montara-jm"
    os.environ["PYTHONPATH"] = str(overlay_root) + os.pathsep + os.environ.get("PYTHONPATH", "")
    for name, location in (("track_types", "track_types.py"),
                           ("mixer_adapter.session", "mixer_adapter/session.py"),
                           ("full_session", "full_session.py")):
        imported = importlib.import_module(name)
        if Path(imported.__file__).resolve(strict=True) != (overlay_root / location).resolve(strict=True):
            raise NativeSystemdOwnerError("Failed to load reviewed MAIN song boundary module")


def main(argv: list[str] | None = None):
    # This entrypoint is a replacement script selected solely by the operator
    # in the existing root broker's fixed systemd launch, not a public flag.
    args = sys.argv[1:] if argv is None else argv
    if not isinstance(args, list) or any(not isinstance(a, str) for a in args):
        raise NativeSystemdOwnerError("Expected trusted systemd argv")
    # Never create data directories until the required cgroup/StateDirectory
    # arguments have been validated; preserve current persistent originals.
    if len(args) < 2 or not _UNIT.fullmatch(args[1]):
        raise NativeSystemdOwnerError("Unverified Owner unit")
    state, runtime, workspace, generation, quota = trusted_native_worker_args(
        args, state_directory=os.environ.get("STATE_DIRECTORY", ""),
        runtime_root=Path("/run") / args[1])
    bundle = Path("/opt/montara-engine")
    jm = Path("/opt/montara-jm")
    # The pinned read-only Librosa wheel is not writable by systemd
    # DynamicUser. Numba must cache into this worker's private RuntimeDirectory,
    # not the shared immutable Engine bundle or another Owner's HOME.
    cache_dir = runtime / "numba-cache"
    if cache_dir.is_symlink():
        raise NativeSystemdOwnerError("Unsafe private Numba cache")
    cache_dir.mkdir(mode=0o700, exist_ok=True)
    if not cache_dir.is_dir() or cache_dir.stat().st_mode & 0o077:
        raise NativeSystemdOwnerError("Unsafe private Numba cache permissions")
    os.environ["NUMBA_CACHE_DIR"] = str(cache_dir)
    # The DynamicUser must not inspect a root-owned Git repository during a
    # user render. The immutable operator-pinned Engine identity is already
    # established by the H4 broker's exact BindReadOnlyPaths mount.
    os.environ["MONTARA_ENGINE_SHA"] = _H4_ENGINE_REVISION
    prepare_native_owner_runtime(
        engine_root=bundle, jm_root=jm, proxy_limit_mib=quota)
    install_reviewed_main_mix_source_access()
    install_reviewed_main_song_transition_source()

    # The actual image already supplies the reviewed private Unix transport
    # modules and pins their code behind the root broker. Use those unchanged.
    from app import create_montara_app
    from urano.private_jm_wsgi_socket import create_private_jm_wsgi_server
    from urano.private_stage_unix_transport import serve_stage_socket
    from urano.native_owner_worker_service import serve_native_owner_workspace

    def ready():
        marker = runtime / "ready.json"
        if marker.is_symlink() or marker.exists():
            raise NativeSystemdOwnerError("Stale ready marker")
        tmp = runtime / "ready.tmp"
        if tmp.is_symlink() or tmp.exists():
            raise NativeSystemdOwnerError("Stale ready staging file")
        # The broker relies on the existing {ready,uid,folder} schema.
        tmp.write_text(json.dumps({
            "ready": True, "uid": os.getuid(), "folder": workspace}))
        tmp.replace(marker)

    shutdown_event = threading.Event()
    # SIGTERM requests a graceful stop; do not interrupt in-flight writes.
    signal.signal(signal.SIGTERM, lambda signum, frame: shutdown_event.set())
    serve_native_owner_workspace(
        app_factory=create_montara_app, data_root=state,
        runtime_root=runtime, workspace_id=workspace,
        generation=generation, on_ready=ready,
        make_private_server=create_private_jm_wsgi_server,
        serve_stage_socket=serve_stage_socket, shutdown_event=shutdown_event,
    )


if __name__ == "__main__":
    main()
