#!/usr/bin/env python3

# MIT License
# 
# Copyright (c) 2018 Paderborn Center for Parallel Computing
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import numpy as np
from scipy import linalg, random
from joblib import Parallel, delayed
import argparse

def build_submatrix(matrix_in, index):
    valuemask  = np.invert(matrix_in[index].mask)
    valuepos   = np.nonzero(valuemask)[0]
    submat_dim = len(valuepos)
    #print("\rBuilding submatrix no. {:4d} of dimension {:4d}".format(index, submat_dim), end="")
    submatrix  = np.zeros([submat_dim, submat_dim])
    for j in range(submat_dim):
        for k in range(submat_dim):
            if (matrix_in[valuepos[j]][valuepos[k]]):
                submatrix[j][k] = matrix_in[valuepos[j]][valuepos[k]]
    submatrix = np.ma.masked_array(submatrix, submatrix == 0)
    return submatrix, valuepos

def load_matlab_matrix_from_file(fn, dim, threshold):
    A = np.empty([dim, dim], dtype=np.float64)
    with open(fn, "r") as fh:
        for i in range(dim):
            line = fh.readline()
            vals = line.split(",")
            for j in range(dim):
                A[i][j] = float(vals[j])
    A = np.ma.masked_array(A, (np.abs(A) <= threshold))
    return A

parser = argparse.ArgumentParser()
parser.add_argument('file')
parser.add_argument('size', type=int)
parser.add_argument('density', type=int)
parser.add_argument('condition', type=int)
args = parser.parse_args()

dim = args.size
exponent = -1
#exponent = -0.5
#exponent = -1/3
A = load_matlab_matrix_from_file(args.file, dim, 0)

# depending on the BLAS library your numpy is linked against, you can increase
# the number of parallel jobs here
tmp = Parallel(n_jobs=1, max_nbytes=None)(delayed(build_submatrix)(A, i) for i in range(dim))
submatrices = [x[0] for x in tmp]
indexlist   = [x[1] for x in tmp]

processed_submatrices = Parallel(n_jobs=1, max_nbytes=None)(delayed(linalg.fractional_matrix_power)(submatrix, exponent) for submatrix in submatrices)

final_result = np.zeros([dim,dim])
for i in range(dim):
    indexes = indexlist[i]
    submatrix = processed_submatrices[i]
    for j in range(len(indexes)):
        final_result[indexes[j]][i] = submatrix[j][np.where(indexes == i)[0][0]]

approxIdent = final_result.dot(A.filled(0))
#approxIdent = final_result.dot(final_result).dot(A.filled(0)) #for exponent -0.5
#approxIdent = final_result.dot(final_result).dot(final_result).dot(A.filled(0)) #for exponent -1/3

print("{}\t{}\t{}\t{}".format(
    dim, args.density, args.condition,
    np.linalg.norm(approxIdent-np.eye(dim), 2)
))
