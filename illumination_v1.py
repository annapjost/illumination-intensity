from ij import IJ, ImagePlus, ImageStack
from ij.process import ImageStatistics as IS
from ij.gui import Plot as Plot
from ij.gui import PlotWindow as PlotWindow
from ij.io import OpenDialog
#from loci.plugins.util import BFVirtualStack

# there are two ways to use the BioFormats importer: using the BioFormats API, and using the 
# IJ namespace function run() to use the standard macro language input.

# BioFormats API has more options I think, but for now the run() thing is working.  
# can I see this in git diff??

od = OpenDialog("Choose a file", None)
filename = od.getFileName()

if filename is None:
    print "You clicked cancel!"
else:
    directory = od.getDirectory()
    path = directory + filename
    print "Selected file path:", path

IJ.run("Bio-Formats Importer", "open=" + path + " color_mode=Grayscale view=Hyperstack stack_order=XYCZT use_virtual_stack");

#loading in the active ImagePlus and stack
imp = IJ.getImage()
stack = imp.getImageStack()

#how big is it?  set whether to use slices or frames for looping

def isFrames(imp):
    """Determine whether the stack has >1 slices or >1 frames"""
    NSlices = imp.getNSlices
    NFrames = imp.getNFrames
    print "number of slices:", NSlices
    print "number of frames:", NFrames
    if NSlices == 1 and NFrames != 1:
        return True
    elif NSlices != 1 and NFrames == 1:
        return False
    else:
        print "stack dimension error!"
        
if isFrames:
    print "frames > 1"

options = IS.MEAN | IS.MEDIAN | IS.MIN_MAX 


def getMean(ip, imp):
    """ Return mean for the given ImagePlus and ImageProcessor """
    global options
    stats = IS.getStatistics(ip, options, imp.getCalibration())
    return stats.mean

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
    #find the mean using the getMean function, then append it to the list and print for sanity
    mean = getMean(ip, imp)
    means.append(mean)
    print mean

IJ.showProgress(1)


#set up the variables for plotting and then plot!    
x = xrange(1, size + 1)
y = means

plot = Plot("Illumination intensity stability", "Frame", "Mean frame intensity", [], [])
plot.setLineWidth(1)

#plot.setColor(Color.BLACK)
plot.addPoints(x, y, Plot.LINE)
plot_window = plot.show()
    
    