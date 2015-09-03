"""this script will take the mean of a dark image"""

from ij import IJ
from ij.process import ImageStatistics as IS

options = IS.MEAN | IS.MEDIAN | IS.MIN_MAX 

def getMean(imp):
    """ Return mean for the given ImagePlus """
    global options
    ip = imp.getProcessor()
    stats = IS.getStatistics(ip, options, imp.getCalibration())
    return stats.mean

imp = IJ.getImage()

print getMean(imp)