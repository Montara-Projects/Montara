    const sphericalSource = params.get('source') || '';
    // Only Owner Uploads videos may request a panorama. The Engine checks
    // that the exact source is registered in the current project as well.
    const sphericalQuery = operation==='api/v1/wizard/spherical-source-frame' &&
      method==='GET' && params.size===1 && params.getAll('source').length===1 &&
      /^\/var\/lib\/private\/montara-[a-z0-9-]{1,80}\/Uploads\/[a-f0-9]{32}\/[^/\\\x00-\x1f\x7f]{1,255}\.(mp4|mov|m4v|mkv|webm|avi|insv)$/i.test(sphericalSource);
    if (operation==='api/v1/wizard/spherical-source-frame' && !sphericalQuery)
      return {kind:'blocked'};
    const spherePreview = operation==='api/v1/wizard/spherical-preview' && method==='GET' &&
      params.has('source') && params.getAll('source').length===1 &&
      /^\/var\/lib\/private\/montara-[a-z0-9-]{1,80}\/Uploads\/[a-f0-9]{32}\/[^/\\\x00-\x1f\x7f]{1,255}\.(mp4|mov|m4v|mkv|webm|avi|insv)$/i.test(sphericalSource) &&
      params.size>=2 && params.size<=9 &&
      [...params.keys()].every(k=>['source','shot','yaw','pitch','fov','roll','projection_preset','projection_control','time_sec'].includes(k)) &&
      ['yaw','pitch','fov','roll','time_sec'].every(k=>!params.has(k) ||
        /^-?[0-9]{1,6}(?:\.[0-9]{1,6})?$/.test(params.get(k)||'')) &&
      ['shot','projection_preset','projection_control'].every(k=>!params.has(k) ||
        /^[A-Za-z0-9_-]{1,32}$/.test(params.get(k)||''));
    if (operation==='api/v1/wizard/spherical-preview' && !spherePreview)
      return {kind:'blocked'};
