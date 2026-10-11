"""Measure the first mesh intersection on rays around a cross-section axis."""
import numpy as np


def section_basis(axis):
    basis = np.cross(axis, [0, 0, 1])
    basis /= np.linalg.norm(basis)
    return basis, np.cross(axis, basis)


def clearance(garment, body, center, axis, limit=.35, samples=64, angles=None):
    outer = radii(garment, center, axis, limit, samples)
    inner = radii(body, center, axis, limit, samples)
    if angles:
        theta = np.arange(samples) * 2 * np.pi / samples
        selected = (theta > angles[0]) & (theta < angles[1])
        outer, inner = outer[selected], inner[selected]
    common = np.isfinite(outer) & np.isfinite(inner)
    gap = outer[common] - inner[common]
    return dict(common_rays=int(common.sum()), missing_garment_rays=int((~np.isfinite(outer)).sum()),
        missing_body_rays=int((~np.isfinite(inner)).sum()),
        minimum_clearance_m=float(gap.min()) if len(gap) else None,
        negative_rays=int((gap < 0).sum()))


def radii(triangles, center, axis, limit=.35, samples=64, return_faces=False):
    distances = (triangles - center) @ axis
    selected = np.flatnonzero((distances.min(1) <= 1e-8) & (distances.max(1) >= -1e-8))
    triangles = triangles[selected]
    if not len(triangles):
        result = np.full(samples, np.inf)
        return (result, np.full(samples, -1)) if return_faces else result
    basis, second = section_basis(axis)
    theta = np.linspace(0, 2 * np.pi, samples, endpoint=False)
    directions = np.cos(theta)[:, None] * basis + np.sin(theta)[:, None] * second
    a, b, c = triangles[:, 0], triangles[:, 1], triangles[:, 2]
    e1, e2 = b - a, c - a
    h = np.cross(directions[:, None], e2)
    det = np.sum(e1 * h, axis=2)
    inv = np.divide(1, det, out=np.zeros_like(det), where=abs(det) > 1e-10)
    delta = center - a
    u = np.sum(delta * h, axis=2) * inv
    q = np.cross(delta, e1)
    v = (directions @ q.T) * inv
    distance = np.sum(e2 * q, axis=1)[None] * inv
    valid = (abs(det) > 1e-10) & (u >= 0) & (v >= 0) & (u + v <= 1) & (distance > 0) & (distance < limit)
    distances = np.where(valid, distance, np.inf)
    result = distances.min(1)
    indices = selected[distances.argmin(1)]
    indices[~np.isfinite(result)] = -1
    return (result, indices) if return_faces else result
