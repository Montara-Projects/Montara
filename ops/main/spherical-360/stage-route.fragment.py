    if path=="/api/v1/wizard/spherical-source-frame":
        if method!="GET" or not query:
            return None
        try:
            params=parse_qs(query,strict_parsing=True,max_num_fields=1)
        except ValueError:
            return None
        if (set(params)!={"source"} or len(params["source"])!=1 or
                not _SPHERICAL_UPLOAD.fullmatch(params["source"][0])):
            return None
        return NativeStageTarget(
            path+"?"+urlencode({"source":params["source"][0]}),"review-media")
    if path=="/api/v1/wizard/spherical-preview":
        if method!="GET" or not query:
            return None
        try:
            params=parse_qs(query,strict_parsing=True,max_num_fields=9)
        except ValueError:
            return None
        allowed={"source","shot","yaw","pitch","fov","roll",
                 "projection_preset","projection_control","time_sec"}
        if (not 2<=len(params)<=9 or set(params)-allowed or "source" not in params or
                any(len(vals)!=1 for vals in params.values()) or
                not _SPHERICAL_UPLOAD.fullmatch(params["source"][0])):
            return None
        for key in ("yaw","pitch","fov","roll","time_sec"):
            if key in params and not re.fullmatch(r"-?[0-9]{1,6}(?:\.[0-9]{1,6})?",params[key][0]):
                return None
        for key in ("shot","projection_preset","projection_control"):
            if key in params and not re.fullmatch(r"[A-Za-z0-9_-]{1,32}",params[key][0]):
                return None
        return NativeStageTarget(path+"?"+urlencode({key:vals[0] for key,vals in params.items()}),"review-media")
