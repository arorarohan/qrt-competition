import re, numpy as np, os
HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, '..', '..', 'solution.py')).read()
m = re.search(r'W = (\[.*?\n\])', src, re.S)
W = np.array(eval(m.group(1)))
TGT = np.array([0.0287,0.0247,0.0203,0.0217,0.0216,0.0161,0.019,0.0416,0.0725,0.0968,0.1234,0.1711,0.2343,0.2871,0.3154,0.3267,0.3312,0.3316,0.3318,0.3371,0.3461,0.3525,0.3534,0.3472,0.3314,0.3085,0.2831,0.2542,0.222,0.1945,0.1738,0.1515,0.1227,0.095,0.0773,0.0686,0.0623,0.0561,0.0515,0.0479,0.0443,0.0408,0.0374,0.0335,0.0297,0.0272,0.0257,0.0241,0.0232,0.0239,0.0246])
X = (np.arange(100)+0.5)/100
T = np.arange(51)/50
def score(M):
    """predicted total hr using W as truth"""
    p = (M*W).mean(1) - 0.5*(M**2).mean(1)
    hr = np.clip(20*p/TGT, 0, 20)
    return hr.sum(), hr
