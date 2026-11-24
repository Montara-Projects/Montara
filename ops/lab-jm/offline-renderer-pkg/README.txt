LAB JM private Intel macOS renderer updater v2 (2026-11-20)

The first offline .pkg (0.6.10.92) failed on macOS Installer because a
nested privilege-changing command in its postinstall smoke test timed out.
The separately loaded renderer was verified to import in 1.3 seconds, and
the existing Mac Companion remained intact after that failure.

v2 removes the nested privilege command and instead drops to the signed-in
Mac user's UID/GID directly from the privileged macOS Installer process.
It also increases the offline probe allowance to 90 seconds, removes only
its own temporary extraction directory, and restores only the specific files
moved by a partial installation.

Build one offline Installer package with native pkgbuild --nopayload from
the fully verified, locally cached pinned Engine 92c7bc33 and its venv:
- Identifier website.montara.jmlab.renderer.intel
- Version 0.6.10.93
- File Montara-LAB-JM-Renderer-92c7bc33-Intel-v2.pkg
- Size 203760247 bytes
- SHA256 30aa1ed523d19d42e6bf1535bddb9a5aafd6e43d40ff5ba067546206cff4e631

Only publish v2 in the root-owned, Owner-session-protected JM route.
The original Mac Companion, CORS configuration, data, projects, and
FER/MAIN/Work environments remain untouched until macOS Installer is
explicitly approved and reports a successful version match.
This package is not signed or notarized and is for the private Intel beta;
do not distribute it as a production release or publish binary archives to Git.

Required E2E gate: execute v2 through macOS Installer with explicit user
approval, verify the Companion /health Engine is 92c7bc33, and export a
project end to end. Static/simulated tests are not substitutes for that gate.
