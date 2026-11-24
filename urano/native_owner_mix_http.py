"""Strict Owner-only routes for the original Chema per-song mixer.

A verified Google Owner/CSRF/generation and broker FD select the dynamic
private worker. Job IDs are worker-local; source paths in POST bodies are
validated by that worker's resolve_mix_sources under the Owner data root.
No generic proxy, arbitrary job path, owner selector or filesystem lookup.
"""
from __future__ import annotations
import re
from urllib.parse import parse_qs, quote, urlencode, unquote
from urano.native_owner_stage_http import NativeStageTarget

_JOB=re.compile(r"[a-f0-9]{12}\Z")
_MAX_QUERY=256

def _filename(segment: str) -> bool:
    try:
        value=unquote(segment, encoding="utf-8", errors="strict")
    except (ValueError,UnicodeError):
        return False
    return (1 <= len(value) <= 180 and value not in (".","..") and
            all(c not in ("/","\\","\0","\r","\n") and c.isprintable()
                for c in value) and ".." not in value and
            value[0] not in ("."," ") and value[-1]!=" ")

def _query(query: str, allowed: set[str]) -> dict[str,str] | None:
    if not query:
        return {}
    try:
        data=parse_qs(query,keep_blank_values=True,strict_parsing=True,
                      max_num_fields=len(allowed))
    except ValueError:
        return None
    if not data or set(data)-allowed or any(len(v)!=1 for v in data.values()):
        return None
    return {k:v[0] for k,v in data.items()}

def native_mix_target(method: str, path: str, query: str="") -> NativeStageTarget | None:
    if not all(isinstance(v,str) for v in (method,path,query)) or len(query)>_MAX_QUERY:
        return None
    if path=="/montara/mix":
        return NativeStageTarget(path,"json") if method=="POST" and not query else None
    head="/montara/mix/"
    if not path.startswith(head):
        return None
    remain=path[len(head):]
    job,sep,suffix=remain.partition("/")
    if not _JOB.fullmatch(job):
        return None
    if not sep:
        return NativeStageTarget(path,"json") if method=="GET" and not query else None
    if suffix=="render" and method=="POST" and not query:
        return NativeStageTarget(path,"json")
    if suffix=="reference/link" and method in ("GET","POST") and not query:
        return NativeStageTarget(path,"json")
    if method!="GET":
        return None
    if suffix=="result":
        args=_query(query,{"download_name"})
        if args is None:return None
        if args and (not _filename(args["download_name"]) or
                     len(args["download_name"])>80):
            return None
        normalized=path + ("?"+urlencode(args) if args else "")
        return NativeStageTarget(normalized,"mix-media")
    if suffix.startswith("track/"):
        encoded=suffix[len("track/"):]
        if not _filename(encoded):return None
        args=_query(query,{"format"})
        if args is None or (args and args.get("format")!="wav"):return None
        # Flask unquotes the public URL before handing the path to us.
        # Encode this *one trusted path segment* again for http.client; raw
        # spaces, '#' and non-ASCII make its request target invalid (503).
        # This changes no Owner, job, MIME or filesystem permissions.
        upstream=head+job+"/track/"+quote(encoded,safe="")
        return NativeStageTarget(upstream + ("?format=wav" if args else ""),"mix-media")
    if suffix.startswith("fx/"):
        value=suffix[len("fx/"):]
        effect,sep,encoded=value.partition("/")
        if sep and effect in ("delay","reverb") and _filename(encoded) and not query:
            upstream=head+job+"/fx/"+effect+"/"+quote(encoded,safe="")
            return NativeStageTarget(upstream,"mix-media")
    return None
