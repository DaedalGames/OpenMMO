import numpy as np


def welded_islands(points, faces):
    _, first, welded = np.unique(np.round(points, 6), axis=0, return_index=True, return_inverse=True)
    welded = welded.ravel()
    parent = np.arange(len(first))

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for face in welded[faces]:
        a = root(face[0])
        for b in face[1:]:
            parent[root(b)] = a
    return first, welded, np.array([root(i) for i in welded])
