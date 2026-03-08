import numpy as np
import matplotlib.pyplot as plt
from scipy import interpolate
from scipy.misc import derivative
vo2 = [1.673925,1.9015125,1.981775,2.112875,2.1112625,2.086375,2.13475,2.1777,2.176975,2.1857125,2.258925,2.2718375,2.3381,2.3330875,2.353725,2.4879625,2.448275,2.4829875,2.5084375,2.511275,2.5511,2.5678375,2.5844625,2.6101875,2.6457375,2.6602125,2.6939875,2.7210625,2.720475,2.767025,2.751375,2.7771875,2.776025,2.7319875,2.564,2.3977625,2.4459125,2.42965,2.401275,2.387175,2.3544375]

ve = [ 3.93125,7.1975,9.04375,14.06125,14.11875,13.24375,14.6625,15.3625,15.2,15.035,17.7625,17.955,19.2675,19.875,21.1575,22.9825,23.75625,23.30875,25.9925,25.6775,27.33875,27.7775,27.9625,29.35,31.86125,32.2425,33.7575,34.69125,36.20125,38.6325,39.4425,42.085,45.17,47.18,42.295,37.5125,38.84375,37.4775,34.20375,33.18,32.67708333]
x = np.array(sorted(vo2))[:-5]
y = np.array(sorted(ve))[:-5]
assert len(x) == len(y)



fig, axes = plt.subplots(5)

axes[0].plot(x, y, '.', label = 'data')



from scipy.interpolate import UnivariateSpline, SmoothBivariateSpline
from scipy.interpolate import splrep, splev

# Get a function that evaluates the linear spline at any x
f = UnivariateSpline(x, y, s=15)
dfdx = f.derivative()
dydx = dfdx(x)
axes[1].plot(x, dydx, label = 'data')

ddfdx = f.derivative(2)
ddydx = ddfdx(x)
axes[2].plot(x, ddydx, label = 'data')

f = splrep(x,y,k=2,s=1)
axes[0].plot(x, splev(x,f), label="fitted")
axes[3].plot(x, splev(x,f,der=1), label="1st derivative")
axes[4].plot(x, splev(x,f,der=2), label="2st derivative")

# ~ dev_2 = interpolate.splev(x, tck, der=2)

# ~ turning_point_mask = (dev_2 == np.amax(dev_2))



# ~ print(turning_point_mask, x[turning_point_mask], dev_2[turning_point_mask])
# ~ turn_idx = np.argmax(dev_2)


plt.show()
