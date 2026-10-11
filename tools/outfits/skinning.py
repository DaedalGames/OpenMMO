"""Apply sampled joint deformation matrices to skinned vertices."""
import numpy as np


def deform(points, joints, weights, matrices):
    homogeneous = np.column_stack([points, np.ones(len(points))])
    return np.einsum('nkij,nj,nk->ni', matrices[joints], homogeneous, weights)[:, :3]


def deform_dense(points, weights, matrices):
    homogeneous = np.column_stack([points, np.ones(len(points))])
    return np.einsum('nb,bij,nj->ni', weights, matrices, homogeneous)[:, :3]
