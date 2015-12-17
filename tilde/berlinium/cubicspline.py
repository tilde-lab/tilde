
# http://www.bruunisejs.dk/PythonHacks/rstFiles/200%20PythonHacks.html
'''Cubic splines are used as yield curves.

Most textbooks, eg [Ralston]_ and [Press & all]_ on numerical mathematics talks 
about the natural splines.
The following code is inspired by [Kiusalaas]_ allthough the coding follow my
my own derivation.

One of the interesting things about [Kiusalaas]_ is that he uses numpy in his
examples. And so did I.

The code below is converted to use class functions, ie classes and the methods 
__init__ and __call__.
The benefit is that the class function is set with some starting values before use.

Further the decorator uFuncConverter is added to the __call__ such that the cubic 
spline behaves like a numpy universal function.
'''
from numpy import zeros, ones, float64, array, linspace, asarray, ndarray
from decimal import Decimal

def uFuncConverter(variableIndex):
    '''A decorator to convert python functions to numpy universal functions

    A standard function of 1 variable is extended by a decorator to handle
    all values in a list, tuple or numpy array

    :param variableIndex: Specifies index for args to use as variable.
        This way the function can be used in classes as well as functions
    :type variableIndex: An positive integer

    **How to use:**

    In the example below uFuncConverter is used on the first parameter x:
    
    >>> @uFuncConverter(0)
    ... def test(x, y = 2):
    ...     return x+y
    ... 
    >>> x0 = 4
    >>> x1 = (1, 2, 3)
    >>> x2 = [2, 3, 4]
    >>> x3 = asarray(x1) + 2
    >>> print test(x0)
    6
    >>> print test(x1)
    [3 4 5]
    >>> print test(x2)
    [4 5 6]
    >>> print test(x3)
    [5 6 7]

    '''
    def wrap(func):
        '''Function to wrap around methods and functions
        '''
        def npWrapFunc(*args):
            '''Function specifying what the wrapping should do
            '''
            if len(args) >= variableIndex:
                before = list(args[:variableIndex])
                arguments = args[variableIndex]
                after = list(args[variableIndex + 1:])
                if isinstance(arguments, (int, float, Decimal)):
                    if variableIndex:
                        return func(*args)
                    else:
                        return func(args[0])
                elif isinstance(arguments, (list, tuple, ndarray)):
                    if variableIndex:
                        return asarray([func(*(before + [x] + after)) for x in arguments])
                    else:
                        return asarray([func(x) for x in arguments])
            raise Exception('Error! Arguments (%s) not of proper format' % str(arguments))
        return npWrapFunc
    return wrap

class LUdecomp3:
    '''Function class to solve triagonal matrix equations

    **At instatiation:**

    :param c: Lower diagonal in the tridiagonal matrix
    :type c: (n-1)-dimensional numpy array
    :param d: The diagonal in the tridiagonal matrix
    :type d: non-zero n-dimensional numpy array
    :param e: Upper diagonal in the tridiagonal matrix
    :type e: A (n-1)-dimensional numpy array
    :return: The LU decomposed matrix of and triagonal matrix [c/d/e]

    **When called as function:**

    :param b: b in the equation: [c, d, e]x = b
    :type b: A n-dimensional numpy array
    :return: The solution, x, to the equation: [c, d, e]x = b

    **How to use:**

    [Kiusalaas]_ p. 66, example 2.11

    >>> c = ones(4)*(-1.)
    >>> d = ones(5)*2.
    >>> e = c.copy()
    >>> # Instantiation
    >>> f = LUdecomp3(c, d, e)
    >>> # f is just called as a function
    >>> print f([5., -5., 4., -5., 5.])
    [2.0, -1.0, 1.0, -1.0, 2.0]
    
    **Reference:**

    [Kiusalaas]_ p. 59
    
    '''
    def __init__(self, c, d, e):
        n = len(d)
        for k in range(1, n):
            lam = c[k-1]/d[k-1] # d must be non-zero
            d[k] = d[k] - lam * e[k-1]
            c[k-1] = lam
        self.c = c
        self.d = d
        self.e = e
    def __call__(self, b):
        n = len(self.d)
        for k in range(1, n):
            b[k] = b[k] - self.c[k-1] * b[k-1]
        b[n-1] = b[n-1] / self.d[n-1]
        for k in range(n-2, -1, -1):
            b[k] = (b[k] - self.e[k]*b[k+1]) / self.d[k]
        return b

class NaturalCubicSpline:
    '''Function class for doing natural cubic spline interpolation.
    A linear extrapolation is used outside the interval of the x-values.

    **At instantiation:**

    :param xData: Array of x-coordinates
    :type xData: A n-dimensional numpy array of float or decimal
    :param yData: Array of y-coordinates
    :type yData: A n-dimensional numpy array of float or decimal

    At instantion the class function is prepared to calculate y-values for x-values
    according to the natural cubic spline.
    
    Extrapolation is linear from the endpoints with the slope like the one at 
    the endpoint.
    
    **When called as a function:**

    :param x: The value to interpolate from
    :type x: A real number
    :param degree: What kind of value to return for x
    :type degree: 0 (y-value), 1 (slope), 2 (curvature)
    :return: The corresponding y-value for x value according
      to the natural cubic spline and the points from instatiation

    **How to use:**

    [Kiusalaas]_ p. 119
    
    >>> xData = array([1, 2, 3, 4, 5], float64)
    >>> yData = array([0, 1, 0, 1, 0], float64)
    >>> # Instantiation
    >>> f = NaturalCubicSpline(xData, yData)
    >>> # f is just called as a function

    >>> print f(1.5), f(4.5)
    0.767857142857 0.767857142857
    >>> print f(1.5, 1), f(4.5, 1)
    1.17857142857 -1.17857142857
    >>> print f(1.5, 2), f(4.5, 2)
    -2.14285714286 -2.14285714286
    
    Call the function with a tuple, list or an array
    
    >>> print f([1.5, 4.5])
    [ 0.76785714  0.76785714]
    >>> print f([1.5, 4.5], 1)
    [ 1.17857143 -1.17857143]
    >>> print f([1.5, 4.5], 2)
    [-2.14285714 -2.14285714]
    
    **Reference:**
    
    [Kiusalaas]_ p. 118, p. 191
    
    '''
    def __init__(self, xData, yData):
        n = len(xData)
        c = zeros(n-1, float64)
        d = ones(n, float64)
        e = zeros(n-1, float64)
        k = zeros(n, float64)
        dx = xData[1:] - xData[0:-1]  # length = n-1
        dy = yData[1:] - yData[0:-1]  # length = n-1
        c[0:n-2] = dx[0:-1]                     # Lower diagonal, c[n-1] = 0
        d[1:n-1] = 2.0 * (dx[1:] + dx[0:-1])    # Diagonal, d[0] = d[n] = 1
        e[1:n-1] = dx[1:n-1]                    # Upper diagonal, e[0] = 0
        k[1:n-1] = 6.0 * (dy[1:] / dx[1:] - dy[0:-1] / dx[0:-1])    # k[0] = k[n] = 0
        self.xData = xData
        self.yData = yData 
        lu = LUdecomp3(c, d, e)
        self.k = lu(k)

    @uFuncConverter(1)
    def __call__(self, x, degree = 0):
        if self.xData[0] <= x <= self.xData[-1]:
            return self._interpolate(x, degree)
        elif x > self.xData[-1]:
            x0, y0 = self.xData[-1], self.yData[-1]
            slope = self._interpolate(x0, 1)
        else:
            x0, y0 = self.xData[0], self.yData[0]
            slope = self._interpolate(x0, 1)
        if degree == 1:
            return slope
        elif degree == 2:
            return 0
        else:
            return slope * (x - x0) + y0            

    def _interpolate(self, x, degree = 0):
        i = self._findSegment(x)
        xl, xu = self.xData[i], self.xData[i+1]
        yl, yu = self.yData[i], self.yData[i+1]
        kl, ku = self.k[i], self.k[i+1]
        h = xu - xl
        if degree == 1:
            return (ku * (x - xl)**2 - kl * (xu - x)**2) / (2 * h) + (yu - yl) / h - h / 6 * (ku - kl)
        elif degree == 2:
            return (ku * (x - xl) + kl * (xu - x)) / h
        else:        
            return (ku * (x - xl)**3 + kl * (xu - x)**3) / (6 * h) \
                   + (yl / h - h * kl / 6) * (xu - x) \
                   + (yu / h - h * ku / 6) * (x - xl)
                
    def _findSegment(self, x):
        '''
        :param x: x value to place in segment defined by the xData (instantiation)
        :return: The lower index in the segment
        '''
        iLeft = 0
        iRight = len(self.xData) - 1
        while True:
            if iRight - iLeft <= 1:
                return iLeft
            i = (iRight + iLeft) / 2
            if x < self.xData[i]:
                iRight = i
            else:
                iLeft = i