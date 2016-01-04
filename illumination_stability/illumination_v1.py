from ij import IJ, ImagePlus, ImageStack
from ij import WindowManager as WM
from ij.process import ImageStatistics as IS
from ij.gui import Plot as Plot
from ij.gui import PlotWindow as PlotWindow
from ij.io import OpenDialog
from fiji.util.gui import GenericDialogPlus
from os import path
import math
from ij.gui import ProfilePlot as PP
from ij.measure import ResultsTable


def getPaths():
    """Dialog box for user to select illumination intensity and dark image files.
    Illumination intensity file should be a .nd file pointing to the timelapse tifs, 
    and dark image file should be a single tif"""
    gd = GenericDialogPlus('File selection')
    gd.addFileField('Illumination stability timelapse (.nd file): ', None)
    gd.addFileField('Dark image (TIF): ', None)

    gd.showDialog()

    stackpath = gd.getNextString()
    darkpath = gd.getNextString()
    
    return stackpath, darkpath

options = IS.MEAN | IS.MEDIAN | IS.MIN_MAX 

def getMean(ip, imp):
    """ Return mean for the given ImagePlus and ImageProcessor """
    global options
    stats = IS.getStatistics(ip, options, imp.getCalibration())
    return stats.mean

    
stackpath, darkpath = getPaths()
# hard coded paths for testing purposes:
# stackpath = "/Users/annajost/Documents/scope_inspections/station_8_dec2015/illuminationstability1//illumination_stability.nd"
# darkpath = "/Users/annajost/Documents/scope_inspections/station_8_dec2015/dark_images//dark1.tif"    
    
#open the dark image
IJ.run("Bio-Formats Importer", "open=" + darkpath + " color_mode=Grayscale view=Hyperstack stack_order=XYCZT")


# grab the dark image and take the mean to find the offset for subtraction

darkimp = WM.getImage(path.basename(darkpath))  #this only works if you load the TIF!  if you load the .nd the image name is different
#darkimp = IJ.getImage()
darkip = darkimp.getProcessor()
offset = getMean(darkip, darkimp)

# once I have the offset, close the dark image to avoid confusion
# might also want to close all here?
darkimp.close()


# picking up the stack.  need to open it separately from the dark image
# because the .nd file generates a different window name than stackpath.
# could try to deal with this later but it is very tricky with the .nd output!
# the other alternative would be to import as image sequence.

IJ.run("Bio-Formats Importer", "open=" + stackpath + " color_mode=Grayscale view=Hyperstack stack_order=XYCZT")
#imp = IJ.getImage()
#stack = imp.getImageStack()

# subtract offset

IJ.run("Subtract...", "value=" + str(offset) + " stack") # could redo this with pixel manipulation as shown here: http://fiji.sc/Jython_Scripting


imp = IJ.getImage()
stack = imp.getImageStack()

#how big is it?  set whether to use slices or frames for looping
def isFrames(imp):
    """Determine whether the stack has >1 slices or >1 frames"""
    NSlices = imp.getNSlices
    NFrames = imp.getNFrames
    #print "number of slices:", NSlices
    #print "number of frames:", NFrames
    if NSlices == 1 and NFrames != 1:
        return True
    elif NSlices != 1 and NFrames == 1:
        return False
    else:
        IJ.log("stack dimension error!")
        

#next step: measure the mean of each frame
means = []

if isFrames:
    size = imp.getNFrames()
else:    
    size = imp.getNSlices()
    
for i in xrange(1, size+1):
    #get imageprocessor for slice
    ip = stack.getProcessor(i)
    #show progress!
    IJ.showProgress(i, size+1)
    #find the mean using the getMean function, then append it to the list 
    mean = getMean(ip, imp)
    means.append(mean)

IJ.showProgress(1)

IJ.resetMinAndMax()

#set up the variables for plotting and then plot!    
x = xrange(1, size + 1)
y = means

plot = Plot("Illumination intensity stability (" + path.basename(stackpath) + ")", "Frame", "Mean frame intensity", [], [])
plot.setLineWidth(1)

#plot.setColor(Color.BLACK)
plot.addPoints(x, y, Plot.LINE)
plot_window = plot.show()

def stdev(s):
    avg = sum(s)*1.0/len(s)
    variance = map(lambda x: (x-avg)**2, s)
    return math.sqrt(average(variance))
    
def average(x):
    average = sum(x)*1.0/len(x)
    return average

IJ.log("Results for " + path.basename(stackpath) + ":")    
IJ.log("Average intensity: " + str(average(means))) 
IJ.log("Standard deviation: " + str(stdev(means)))

# now, use the subtracted image to output the flat field image and plot

# get the plot out of the way to bring back the stack
WM.putBehind()
#average all frames
IJ.run("Z Project...", "projection=[Average Intensity]")

# plot the diagonal profile
imp = IJ.getImage()
IJ.run("Line Width...", "line=3")
IJ.makeLine(0, 0, imp.width, imp.height)
IJ.run("Plot Profile")

# bring back the projection, run Measure to get max and min
WM.putBehind()
IJ.run("Measure")  #this method reports the actual max and min, not averaged across 3 px...
rt = ResultsTable.getResultsTable()
max = rt.getValue("Max", 0)
min = rt.getValue("Min", 0)
rolloff = (min*1.0/max)*100

IJ.run("Fire")

IJ.log("Percent illumination roll-off: " + str(rolloff))

# close the annoying results window
resultswin = WM.getWindow("Results")
resultswin.removeNotify()

# tile windows so you can see all the beautiful output better
IJ.run("Tile")



