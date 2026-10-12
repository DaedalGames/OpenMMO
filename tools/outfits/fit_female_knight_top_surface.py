import sys
from pathlib import Path

import numpy as np
from scipy.sparse import coo_matrix, diags
from scipy.sparse.linalg import factorized

source = Path(sys.argv[1])
data = np.load(source)
points, faces = data['points'], data['faces']
_, first, inverse = np.unique(np.round(points, 7), axis=0, return_index=True, return_inverse=True)
inverse = inverse.ravel()
p = points[first]
f = inverse[faces]
edges = np.sort(np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]]), axis=1)
edges = np.unique(edges, axis=0)
a, b = edges.T
valid = a != b
a, b = a[valid], b[valid]
length = np.linalg.norm(p[a] - p[b], axis=1)
w = 1 / np.maximum(length, .002)
color = data['colors'][first].max(1)
stiffness = np.where(color > .25, 3.0, .5)
w *= np.sqrt(stiffness[a] * stiffness[b])
heads, tails = np.r_[a, b], np.r_[b, a]
all_w = np.r_[w, w]
degree = np.bincount(heads, weights=all_w, minlength=len(p))
L = diags(degree) - coo_matrix((all_w, (heads, tails)), shape=(len(p), len(p))).tocsr()
fixed = data['fixed'][first].astype(bool)
targets = data['targets'][first]
free = np.flatnonzero(~fixed)
locked = np.flatnonzero(fixed)
solve = factorized(L[free][:, free].tocsc())
q = targets.copy()
p_delta = p[a] - p[b]
R = np.tile(np.eye(3), (len(p), 1, 1))
errors = []
for iteration in range(60):
    q_delta = q[a] - q[b]
    product = w[:, None, None] * q_delta[:, :, None] * p_delta[:, None, :]
    covariance = np.zeros((len(p), 3, 3))
    np.add.at(covariance, a, product)
    np.add.at(covariance, b, product)
    U, _, Vh = np.linalg.svd(covariance)
    correction = np.ones((len(p), 3))
    correction[:, 2] = np.linalg.det(U @ Vh)
    R = (U * correction[:, None, :]) @ Vh
    rhs = np.zeros_like(p)
    edge = np.einsum('nij,nj->ni', (R[a] + R[b]) / 2, p_delta) * w[:, None]
    np.add.at(rhs, a, edge)
    np.add.at(rhs, b, -edge)
    value = rhs[free] - L[free][:, locked] @ targets[locked]
    previous = q.copy()
    for axis in range(3):
        q[free, axis] = solve(value[:, axis])
    q[locked] = targets[locked]
    errors.append(float(np.linalg.norm(q - previous, axis=1).max()))
    if errors[-1] < 1e-6:
        break
assert np.isfinite(q).all()
np.savez(source.with_name('arap-result.npz'), points=q[inverse], rotations=R[inverse], iterations=len(errors), residual=errors[-1])
print('ARAP', len(p), 'vertices', len(errors), 'iterations', errors[-1], flush=True)
