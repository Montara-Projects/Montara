"""Private Audio-project API mounted inside an already verified Owner worker.

No public auth bypass: deployment gate is the Owner broker's CSRF and worker FD.
"""
from __future__ import annotations
import os
from pathlib import Path
from flask import jsonify,request
from audio_project_store import AudioProjects, AudioProjectError, AudioProjectConflict


def register_audio_project_api(app,data_root:Path,fixtures:Path,*,remote:bool):
    # Audio projects are Owner-private metadata. This store is not a second
    # upload root: every source is rechecked through the existing Owner-scoped
    # source resolver on saving and reopening. No browser selects an Owner.
    audio_projects = AudioProjects(data_root)

    @app.get("/montara/mix/projects")
    def audio_projects_list():
        return jsonify({"projects": audio_projects.list()})

    @app.get("/montara/mix/projects/<project_id>")
    def audio_projects_get(project_id: str):
        try:
            project = audio_projects.get(project_id)
            from mixer_adapter.source_access import resolve_mix_sources
            resolve_mix_sources(project["sources"], data_root, fixtures,
                                remote=remote)
        except AudioProjectError as exc:
            return jsonify({"error": {"message": str(exc)}}), 404
        except ValueError:
            return jsonify({"error": {"message": "Some audio sources are missing or no longer permitted. Restore them before reopening this project."}}), 409
        return jsonify(project)

    @app.post("/montara/mix/projects")
    def audio_projects_save():
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or (request.content_length or 0) > 256*1024:
            return jsonify({"error": {"message": "Invalid audio project"}}), 400
        from mixer_adapter.source_access import resolve_mix_sources
        try:
            paths = resolve_mix_sources(body.get("sources"), data_root, fixtures,
                                        remote=remote)
            # The source resolver performs Owner boundary checks. The persisted
            # manifest never includes an arbitrary browser-provided filesystem root.
            master_path=body.get('master_path')
            if master_path is not None and (not isinstance(master_path,str) or
                not Path(master_path).resolve().is_relative_to(data_root)):
                raise AudioProjectError('Master must belong to this workspace')
            project = audio_projects.save(name=body.get("name"),
                sources=[str(p) for p in paths], controls=body.get("controls"),
                track_types=__import__('track_types').validate(body.get("track_types")),
                project_id=body.get("project_id"), revision=body.get("revision"),
                master_path=master_path)
        except AudioProjectConflict as exc:
            return jsonify({"error": {"message": str(exc)}}), 409
        except (AudioProjectError, ValueError, TypeError) as exc:
            return jsonify({"error": {"message": str(exc)}}), 400
        return jsonify({key:project[key] for key in ('id','name','kind','revision','updated_at')}), 200

    @app.post("/montara/mix/projects/<project_id>/delete")
    def audio_projects_delete(project_id: str):
        body = request.get_json(silent=True) or {}
        if not isinstance(body, dict) or body.get('keep_exports') is not True:
            return jsonify({"error": {"message": "Explicit confirmation to keep exports is required"}}), 400
        try:
            return jsonify(audio_projects.delete(project_id,revision=body.get('revision')))
        except AudioProjectConflict as exc:
            return jsonify({"error": {"message": str(exc)}}), 409
        except AudioProjectError as exc:
            return jsonify({"error": {"message": str(exc)}}), 404

