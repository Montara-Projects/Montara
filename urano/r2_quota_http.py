"""Opt-in, isolated Flask quota view. Never registered with MAIN automatically.

Integration must supply a trusted principal resolver from the existing verified
Google Owner session plus an authorized D1/SQLite quota lookup. No browser
parameter, header, or cookie field is interpreted as Google identity here.
"""
from __future__ import annotations

from collections.abc import Callable
from flask import Blueprint, jsonify, make_response

from urano.r2_pilot_quota_gate import QuotaGateError, VerifiedPrincipal
from urano.r2_pilot_status import OwnerQuotaStatus


def quota_blueprint(
    trusted_principal: Callable[[], VerifiedPrincipal | None],
    lookup: Callable[[VerifiedPrincipal], OwnerQuotaStatus],
) -> Blueprint:
    bp = Blueprint('montara_r2_pilot_quota', __name__)

    @bp.get('/api/v1/storage/quota')
    def get_quota():
        # Identity NEVER comes from request.args, JSON, headers, or client cookies.
        try:
            principal = trusted_principal()
            if not isinstance(principal, VerifiedPrincipal):
                raise QuotaGateError('no verified session')
            quota = lookup(principal)
            if not isinstance(quota, OwnerQuotaStatus):
                raise ValueError('invalid quota model')
        except QuotaGateError:
            response = jsonify({'error': 'storage_quota_unavailable'})
            response.status_code = 403
        else:
            response = jsonify(quota.as_public_json())
        response.headers['Cache-Control'] = 'no-store, private'
        response.headers['Vary'] = 'Cookie'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response

    return bp
