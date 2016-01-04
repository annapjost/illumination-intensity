
from ij import IJ, ImagePlus, ImageStack
from ij import WindowManager as WM
from ij.process import ImageStatistics as IS
from ij.gui import Plot as Plot
from ij.gui import PlotWindow as PlotWindow
from ij.io import OpenDialog
from fiji.util.gui import GenericDialogPlus
import os, csv
import math
from ij.gui import ProfilePlot as PP
from ij.measure import ResultsTable

def getOffset():
    """User points to the dark image, which is opened and then mean is taken for offset
    Requires getMean()
    Requires from fiji.util.gui import GenericDialogPlus"""
    gd = GenericDialogPlus('choose dark image')
    gd.addFileField('Dark image (TIF): ', None)

    gd.showDialog()

    darkpath = gd.getNextString()
    #open the dark image
    IJ.run("Bio-Formats Importer", "open=" + darkpath + " color_mode=Grayscale view=Hyperstack stack_order=XYCZT")
    # grab the dark image and take the mean to find the offset for subtraction
    darkimp = WM.getImage(os.path.basename(darkpath))  #this only works if you load the TIF!  if you load the .nd the image name is different
    darkip = darkimp.getProcessor()
    offset = getMean(darkip, darkimp)
    darkimp.close()
    return offset

def getMean(ip, imp):
    """ Return mean for the given ImagePlus and ImageProcessor
    Requires from ij.process import ImageStatistics as IS """
    options = IS.MEAN | IS.MEDIAN | IS.MIN_MAX
    stats = IS.getStatistics(ip, options, imp.getCalibration())
    return stats.mean

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

def stdev(s):
    avg = sum(s)*1.0/len(s)
    variance = map(lambda x: (x-avg)**2, s)
    return math.sqrt(average(variance))
    
def average(x):
    average = sum(x)*1.0/len(x)
    return average
    
def illum(srcDir, currentDir, filename, offset):

    stackpath = os.path.join(currentDir, filename)

    IJ.run("Bio-Formats Importer", "open=" + stackpath + " color_mode=Grayscale view=Hyperstack stack_order=XYCZT")
    
    # subtract offset
    IJ.run("Subtract...", "value=" + str(offset) + " stack") # could redo this with pixel manipulation as shown here: http://fiji.sc/Jython_Scripting
    
    
    imp = IJ.getImage()
    stack = imp.getImageStack()
    
    #how big is it?  set whether to use slices or frames for looping
    
    
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
    
    #set up the variables for plotting and then plot!    
    #x = xrange(1, size + 1)
    #y = means
    
    #plot = Plot("Illumination intensity stability (" + path.basename(stackpath) + ")", "Frame", "Mean frame intensity", [], [])
    #plot.setLineWidth(1)
    #
    ##plot.setColor(Color.BLACK)
    #plot.addPoints(x, y, Plot.LINE)
    #plot_window = plot.show()
    
    averageint = average(means)
    stdevint = stdev(means)
    
    
    #IJ.log("Results for " + path.basename(stackpath) + ":")    
    #IJ.log("Average intensity: " + str(average(means))) 
    #IJ.log("Standard deviation: " + str(stdev(means)))
    
    # now, use the subtracted image to output the flat field image and plot
    
    # get the plot out of the way to bring back the stack
    #WM.putBehind()
    #average all frames
    IJ.run("Z Project...", "projection=[Average Intensity]")
    
    # plot the diagonal profile
    projimp = IJ.getImage()
    IJ.run("Line Width...", "line=3")
    IJ.makeLine(0, 0, projimp.width, projimp.height)
    IJ.run("Measure")  #this method reports the actual max and min, not averaged across 3 px...
    rt = ResultsTable.getResultsTable()
    max = rt.getValue("Max", 0)
    min = rt.getValue("Min", 0)
    rolloff = (min*1.0/max)*100
    
    # close the results table
    resultswin = WM.getWindow("Results")
    resultswin.removeNotify()
    
    # close the projection window, then close the stack (removing save notification)
    #projimp.close()
    #win = WM.getActiveWindow()
    #print win
    #win.removeNotify()
    #imp.removeNotify()
    
    titles = WM.getImageTitles()
    win0 = WM.getWindow(titles[0])
    win0.removeNotify()
    #win0.close()
    win1 = WM.getWindow(titles[1])
    win1.removeNotify()
    #win1.close()
        
    return averageint, stdevint, rolloff
    
def CSVsetup():
    """" Sets up a file to save CSV output
    Modified from here: 
    http://cmci.embl.de/documents/120206pyip_cooking/python_imagej_cookbook#saving_csv_file_data_table
    Requires import GenericDialogPlus and import csv"""
    # set up CSV file
    savepath = IJ.getDirectory("Choose where to save the output file")
    gd = GenericDialogPlus('Enter a filename for the output file')
    gd.addStringField('filename: ', None)
    gd.showDialog()
    filename = gd.getNextString()
    fullpath = os.path.join(savepath, filename)
    return fullpath
      

def run():
    """Loops through a directory and runs process() on each file.  Needs work to be further generalizable.
		Designed based on this: 
		http://fiji.sc/Scripting_toolbox#Opening.2C_processing.2C_and_saving_a_sequence_of_files_in_a_folder
		CSV saving from here: http://cmci.embl.de/documents/120206pyip_cooking/python_imagej_cookbook#saving_csv_file_data_table
		Requires import os"""
    offset = getOffset()
    print offset
    srcDir = IJ.getDirectory("Input_directory")
    if not srcDir:
        return
    ext = ".nd"
    
    CSVpath = CSVsetup()
    
    # open the CSV file
    f = open(CSVpath, 'wb')
    
    # create CSV writer
    writer = csv.writer(f)
    
    # loop through the files in the input directory
    for root, directories, filenames in os.walk(srcDir):
        for filename in filenames:
            # Check for file extension
            if not filename.endswith(ext):
                continue
            averageint, stdevint, rolloff = illum(srcDir, root, filename, offset) 
            
            row = [filename, averageint, stdevint, rolloff]
            writer.writerow(row)
    
    f.close
    
run()