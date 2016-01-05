
from ij import IJ, ImagePlus, ImageStack
from ij import WindowManager as WM
from ij.process import ImageStatistics as IS
from ij.gui import GenericDialog
from fiji.util.gui import GenericDialogPlus
import os, csv
import math
from ij.gui import ProfilePlot as PP
from ij.measure import ResultsTable
from ij.gui import Plot as Plot
from ij.gui import PlotWindow as PlotWindow

def getOffset():
    """User points to the dark image, which is opened and then mean is taken for offset
    Requires getMean()
    Requires from fiji.util.gui import GenericDialogPlus"""
    gd = GenericDialogPlus('choose dark image')
    gd.addFileField('Dark image (TIF): ', None)
    gd.showDialog()
    if gd.wasCanceled():
        return
    else:
        darkpath = gd.getNextString()
    
    # make sure the selected file is a tiff
    
    root, filename = os.path.split(darkpath)
    correct = False
    while correct == False:
        if not filename.endswith(".TIF") and not filename.endswith(".tif"):
            gd = GenericDialogPlus("Error")
            gd.addMessage("Selected file is not a TIF.  Choose a new file.")
            gd.addFileField('Dark image (TIF): ', None)
            gd.showDialog()
            darkpath = gd.getNextString()
            if gd.wasCanceled():
                return
            else:
                root, filename = os.path.split(darkpath)
        else: correct = True

    
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
    
def illum(srcDir, currentDir, filename, offset, showImages):
    """
    Opens a .nd file at the indicated path, then measures the average intensity value, 
    standard deviation over time, and percent roll-off from a stack of flat field images 
    (after offset subtraction).
    
    Requires functions getMean, isFrames, stdev, and average
    
    """

    # define the path and open the stack 
    stackpath = os.path.join(currentDir, filename)
    IJ.run("Bio-Formats Importer", "open=" + stackpath + " color_mode=Grayscale view=Hyperstack stack_order=XYCZT")
    
    # subtract the offset 
    IJ.run("Subtract...", "value=" + str(offset) + " stack") # could redo this with pixel manipulation as shown here: http://fiji.sc/Jython_Scripting
    
    # grab the image and stack
    imp = IJ.getImage()
    stack = imp.getImageStack()
    
    # determine whether to loop on frames or slices using isFrames function
    if isFrames:
        size = imp.getNFrames()
    else:    
        size = imp.getNSlices()
        
    # initialize a list for the means, then loop through the stack to get the mean
    # of each slice, then append to the list 
    means = []    
    for i in xrange(1, size+1):
        #get imageprocessor for slice
        ip = stack.getProcessor(i)
        #show progress!
        IJ.showProgress(i, size+1)
        #find the mean using the getMean function, then append it to the list 
        mean = getMean(ip, imp)
        means.append(mean)
    
    #if showImages is true, do the plots
    if showImages:
        #set up the variables for plotting and then plot!    
        x = xrange(1, size + 1)
        y = means
        
        plot = Plot("Illumination intensity stability (" + os.path.basename(stackpath) + ")", "Frame", "Mean frame intensity", [], [])
        plot.setLineWidth(1)
        
        #plot.setColor(Color.BLACK)
        plot.addPoints(x, y, Plot.LINE)
        plot_window = plot.show()
        
        WM.putBehind()
        
    averageint = average(means)
    stdevint = stdev(means)
        
    
    # now, use the subtracted image to output the flat field image
 
    #average all frames
    IJ.run("Z Project...", "projection=[Average Intensity]")
    
    # plot the diagonal profile
    projimp = IJ.getImage()
    IJ.run("Line Width...", "line=3")
    IJ.makeLine(0, 0, projimp.width, projimp.height)
    IJ.run("Measure")  #this method reports the actual max and min, not averaged across 3 px...
    rt = ResultsTable.getResultsTable()
    count = rt.getCounter()
    max = rt.getValue("Max", count-1)
    min = rt.getValue("Min", count-1)
    rolloff = (min*1.0/max)*100
    
    # close the results table
    #resultswin = WM.getWindow("Results")
    #resultswin.removeNotify()
    
    # close appropriate windows without prompting to save
    titles = WM.getImageTitles()
    if showImages:
        titles = WM.getImageTitles()
        for title in titles:
            if not title.startswith("AVG"):
                if not title.startswith("Illum"):
                    win = WM.getImage(title)
                    win.changes = False
                    win.close()
            else:
                IJ.run("Fire")
            
    else:
        count = WM.getImageCount()
        win0 = WM.getImage(titles[count-1])
        win0.changes = False
        win0.close()
        win1 = WM.getImage(titles[count-2])
        win1.changes = False
        win1.close()
        
    return averageint, stdevint, rolloff
    
def CSVsetup():
    """" Sets up a file to save CSV output
    Modified from here: 
    http://cmci.embl.de/documents/120206pyip_cooking/python_imagej_cookbook#saving_csv_file_data_table
    Requires import GenericDialogPlus and import csv"""
    # set up CSV file
    savepath = IJ.getDirectory("Choose where to save the output file")
    if not savepath:
        return
    gd = GenericDialogPlus('Enter a filename for the output file')
    gd.addStringField('filename: ', None)
    gd.showDialog()
    if gd.wasCanceled():
        return
    filename = gd.getNextString()
    fullpath = os.path.join(savepath, filename)
    return fullpath
      

def run():
    """Loops through a directory and runs process() on each file.  Needs work to be further generalizable.
		Designed based on this: 
		http://fiji.sc/Scripting_toolbox#Opening.2C_processing.2C_and_saving_a_sequence_of_files_in_a_folder
		CSV saving from here: http://cmci.embl.de/documents/120206pyip_cooking/python_imagej_cookbook#saving_csv_file_data_table
		Requires import os
		Requires CSVsetup(), getOffset(), and illum() plus their dependencies"""
    offset = getOffset()
    if not offset:
        IJ.log("you clicked cancel!")
        return
    
    # set the directory with the timelapse and set extension to .nd
    srcDir = IJ.getDirectory("Input directory")
    if not srcDir:
        IJ.log("you clicked cancel!")
        return
    ext = ".nd"
    
    CSVpath = CSVsetup()
    if not CSVpath:
        IJ.log("you clicked cancel!")
        return
    
    # open the CSV file
    f = open(CSVpath, 'wb')
    
    # create CSV writer
    writer = csv.writer(f)
    
    # ask user whether they'd like to see image output vs. just the csv file
    
    gd = GenericDialog("output settings")
    gd.addMessage("Would you like to display plots and images in addition to saving the summary data?")
    gd.addCheckbox("Yes, please show me images", False)
    gd.showDialog()
    
    showImages = gd.getNextBoolean()
    
    
    # loop through the files in the input directory
    for root, directories, filenames in os.walk(srcDir):
        for filename in filenames:
            # Check for file extension
            if not filename.endswith(ext):
                continue
            averageint, stdevint, rolloff = illum(srcDir, root, filename, offset, showImages) 
            
            row = [filename, averageint, stdevint, rolloff]
            print row
            writer.writerow(row)
    f.close()
    
    if showImages:
        IJ.run("Tile")
    
run()

gd = GenericDialog("all done")
gd.addMessage("analysis finished!  (...or you clicked cancel)")
gd.showDialog()