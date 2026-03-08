#!/usr/bin/env python3
'''
'''

from pathlib import Path

import numpy as np
from scipy import sparse
from scipy.sparse import linalg
import numpy as np
from numpy.linalg import norm
from scipy import sparse
from scipy.sparse.linalg import spsolve

def main():
    import matplotlib.pyplot as plt
    from qq.spectrum.spectrum import Spectrum
    
    s = Spectrum(Path(__file__).parent.joinpath("RMP00146.jdx"))
    
    
    s.plot()
    x = s.x
    y = s.y
    
    y1 = baseline_correction(y)
    plt.plot(x,y1,label="baseline_correction")
    
    y2 = baseline_arPLS(y)
    plt.plot(x,y2)

    s.baseline_removal()
    s.plot()

    plt.legend()
    plt.show()
    
    
    
    print(f"{Path(__file__).resolve()} finished")
    
    
    
    
    


def baseline_correction(y, niter=10, lam=2e7, p=0.005):

    # ~ from scipy.optimize import curve_fit
    
   
    L = len(y)
    D = sparse.diags([1,-2,1],[0,-1,-2], shape=(L,L-2))
    w = np.ones(L)
    
    for i in range(niter):
        W = sparse.spdiags(w, 0, L, L)
        Z = W + lam * D.dot(D.transpose())
        z = spsolve(Z, w*y)
        w = p * (y > z) + (1-p) * (y < z)

    corr = y - z
    if np.isnan(corr).all():
        print("baseline correction failed")
        return
    
    #%% Plot spectrum, baseline and corrected spectrum
    # ~ plt.clf()
    # ~ plt.plot(y)
    # ~ plt.plot(z)
    # ~ plt.plot(corr)
    # ~ plt.gca().invert_xaxis()
    # ~ plt.show()
    
    return corr



def baseline_arPLS(y, ratio=1e-6, lam=100, niter=10, full_output=False):
    '''
    https://stackoverflow.com/questions/29156532/python-baseline-correction-library
    '''
    

    
    
    
    L = len(y)

    diag = np.ones(L - 2)
    D = sparse.spdiags([diag, -2*diag, diag], [0, -1, -2], L, L - 2)

    H = lam * D.dot(D.T)  # The transposes are flipped w.r.t the Algorithm on pg. 252

    w = np.ones(L)
    W = sparse.spdiags(w, 0, L, L)

    crit = 1
    count = 0

    while crit > ratio:
        z = linalg.spsolve(W + H, W * y)
        d = y - z
        dn = d[d < 0]

        m = np.mean(dn)
        s = np.std(dn)

        w_new = 1 / (1 + np.exp(2 * (d - (2*s - m))/s))

        crit = norm(w_new - w) / norm(w)

        w = w_new
        W.setdiag(w)  # Do not create a new matrix, just update diagonal values

        count += 1

        if count > niter:
            print('Maximum number of iterations exceeded')
            break

    if full_output:
        info = {'num_iter': count, 'stop_criterion': crit}
        return z, d, info
    else:
        return z



def arpls(y, lam=1e4, ratio=0.05, itermax=100):
    r"""
    Baseline correction using asymmetrically
    reweighted penalized least squares smoothing
    Sung-June Baek, Aaron Park, Young-Jin Ahna and Jaebum Choo,
    Analyst, 2015, 140, 250 (2015)
    """
    from scipy.linalg import cholesky
    
    N = len(y)
    D = sparse.eye(N, format='csc')
    D = D[1:] - D[:-1]  # numpy.diff( ,2) does not work with sparse matrix. This is a workaround.
    D = D[1:] - D[:-1]
    H = lam * D.T * D
    w = np.ones(N)
    for i in range(itermax):
        W = sparse.diags(w, 0, shape=(N, N))
        WH = sparse.csc_matrix(W + H)
        C = sparse.csc_matrix(cholesky(WH.todense()))
        z = spsolve(C, spsolve(C.T, w * y))
        d = y - z
        dn = d[d < 0]
        m = np.mean(dn)
        s = np.std(dn)
        wt = 1. / (1 + np.exp(2 * (d - (2 * s - m)) / s))
        if np.linalg.norm(w - wt) / np.linalg.norm(w) < ratio:
            break
        w = wt
    return z    




    
        
if __name__ == "__main__":
    main()
