# Exact reviewed Owner Uploads path; the Worker independently verifies
# that this source belongs to the currently open project.
_SPHERICAL_UPLOAD = re.compile(
    r"/var/lib/private/montara-[a-z0-9-]{1,80}/Uploads/[a-f0-9]{32}/"
    r"[^/\\\x00-\x1f\x7f]{1,255}\.(?:mp4|mov|m4v|mkv|webm|avi|insv)\Z",
    re.IGNORECASE,
)
