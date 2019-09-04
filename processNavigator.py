#! /usr/bin/env python
# A script by Kyle Dent for use with ArbitrEM SerialEM script. Updated 1 Sept 2019
# When running the script on a navigator file, please make sure that all polygons, medium magnification 
# montages and acquisition template points have been removed.
# Please make sure that the first item in the navigator is your Atlas/Specimen Grid Montage.
# Please use a hole diameter that is 20% greater than the size of the measured hole.
# Navigator parsing code borrowed from David Mastronarde's supermont.py. 
# TODO: determine navigator file name and prefix output files with this name for convenience?
# TODO: plot position of acquisition points within each acquisition template.
# TODO: output ArbitrEM script with path to settings files embedded along with other parameters
# TODO: support XML navigator files
# TODO: solve the problem where the last acquisition point is dropped.
# TODO: implement a validation that ensures the script cannot start when it is not configured for the current navigator.


from __future__ import division

import math, re, sys, argparse, os, sys, datetime

from string import Template

parser = argparse.ArgumentParser(description='ArbitrEM Python script to process a SerialEM navigator allowing acquisition points to be associated with specific view-maps. ArbitrEM session files are output by default into ./arbitrEM.')
parser.add_argument('--o', default='./arbitrEM', help='output directory for ArbitrEM files')
parser.add_argument('--d', default=None, type=float, help='the diameter of the targeting view-map in micrometers')
parser.add_argument('--nav', default=None, help='the SerialEM navigator file (not in XML format)')
parser.add_argument('--v', default='False', action='store_true',help='request verbose output for diagnositic purposes')
parser.add_argument('--s', default='True', action='store_true',help='request creation of settings files as well as SerialEM scripts with settings embedded')
parser.add_argument('--generateSettings', default='True',help='whether or not to generate the settings')
parser.add_argument('--customShiftOffset', default='0.0 0.0',help='apply a custom beam-image shift offset to systematically adjust calculated targeting X,Y shifts.')
parser.add_argument('--defocusRange', default='-1 -2.6 0.2',help='the defocus range and step, specify for example as \'-1 -2.5 0.2\'. Step must be positive.')
parser.add_argument('--earlyReturn', default='1',help=' 0 - early return ON, 1 - early return OFF i.e. SerialEM parameter values')
parser.add_argument('--scriptTemplate', default='./ArbitrEM.txt', help='location of template script into which parameters will be embedded')
parser.add_argument('--sessionBasePath', default=None, type=str, help="session base path on the SerialEM computer. e.g.: D:\session\specimen_X'")
parser.add_argument('--viewMapDefocus', default='-75',help='The defocus used for view-map acquisition.')
parser.add_argument('--viewMapExpTime', default='1',help='The exposure time used for view-map acquisition.')

args_dict = vars(parser.parse_args())

if None in args_dict.values():
    if args_dict['d'] is None:
        print('Please specify the diameter (in microns) of your view-maps and try again. Run ./processNavigator.py --help for more details.')
    elif args_dict['nav'] is None:
        print('Please specify a navigator file and try again. The format should be SerialEM and not XML. Run ./processNavigator.py --help for more details.')  
    elif args_dict['sessionBasePath'] is None:
        print('Please specify a session base path on the computer running SerialEM in quotation marks, e.g. --sessionBasePath "D:\session\specimen_X". The outputed sessions files must be placed in side this folder, e.g. D:\session\specimen_X\arbitrEM')
    parser.print_help()
    quit()

#try:
#    args_dict['v'] = eval(args_dict['v'])
#    args_dict['s'] = eval(args_dict['s'])
#
#except Exception as e:
#    print('Problem interpreting boolean variable. Please check you spelling.')

settingsFiles = {'customShift.txt':args_dict['customShiftOffset'],
                 'defocusRange.txt':args_dict['defocusRange'],
                 'earlyReturn.txt':args_dict['earlyReturn']}
                    
settingsDict = {'viewMapDiameter':args_dict['d'], 'sessionBasePath':args_dict['sessionBasePath'],
               'viewMapDefocus': args_dict['viewMapDefocus'], 'viewMapExpTime': args_dict['viewMapExpTime']}

# Navigator items have the format: [Item = LABEL]
outputDir = args_dict['o']

if os.path.isdir(outputDir) == False:
    os.makedirs(outputDir)
    
print('ArbitrEM related files are being written to: {}'.format(outputDir))

foilHoleDiameter = float(args_dict['d'])
foilHoleRadius = foilHoleDiameter / 2
navigatorFile = args_dict['nav']

indices_file = os.path.join(outputDir,'pointIndices.txt')
guide_file = os.path.join(outputDir,'indexGuide.txt')

def createSettingsFiles():
    settingsLocation=os.path.join(outputDir,'settings')
    if os.path.isdir(settingsLocation)==False:
        os.makedirs(settingsLocation)

    for file in settingsFiles:
        outputPathFileName=os.path.join(settingsLocation,file)
        if args_dict['v']:
            print('Creating {}, containing [{}]'.format(outputPathFileName,settingsFiles[file]))
        try:
            outFile = open(outputPathFileName, 'w')
            outFile.write(settingsFiles[file])
            outFile.close()
        except Exception as e:
            print(str(e))

def writeArbitrEMScript(inputFile,settingsDict,outputFile):
    with open(inputFile,'r') as fileHandle:
        fileContents=''.join(fileHandle.readlines())
        stringTemplate = Template(str(fileContents))
        fileHandle.close()
    
    print('Creating {} script with {} specified as the SerialEM session base-path'.format(outputFile,args_dict['sessionBasePath']))
    submitScriptString = stringTemplate.safe_substitute(settingsDict)
    
    scriptHandle=open(outputFile,'w')
    scriptHandle.write(submitScriptString)
    scriptHandle.close()

def calculateDistance(anchor_item, point_item):
    distance_calc = 0
    xDiff = float(point_item['StageXYZ'].split(' ')[0]) - float(anchor_item['StageXYZ'].split(' ')[0])
    yDiff = float(point_item['StageXYZ'].split(' ')[1]) - float(anchor_item['StageXYZ'].split(' ')[1])
    xDiff_sqd = xDiff ** 2
    yDiff_sqd = yDiff ** 2
    distance_calc = math.sqrt(xDiff_sqd + yDiff_sqd)
    return distance_calc

def IdentifyAcquisitionPoints(anchor_index, navigator):
    acqNavIndices = []
    anchor_item = navigator_items[anchor_index]  # this is the hole image

    for nav_index in range(0, len(navigator)):
        nav_item = navigator_items[nav_index]
        # if Navigator item is a Point (i.e. = 0), proceed...
        if nav_item['Type'] == '0':  # and nav_item['Label'] != 1:
            distance_calc = calculateDistance(anchor_item, nav_item)
            if distance_calc <= foilHoleRadius:
                acqNavIndices.append(nav_index)
    return acqNavIndices

def readNavInfo(filename):
    ### Read navigator into a series of items, return list of item dictionaries. Borrowed from David Mastronarde's supermont.py
    navitems = []
    gotItem = 0

    try:
        infile = open(filename)
    except IOError:
        print("Error opening {}: {}".format(filename, sys.exc_info()[1]))
        sys.exit(1)

    itemMatch = re.compile('^\[(\S+)\s*=\s*(.*\S)\s*\]')
    keyMatch = re.compile('^(\S+)\s*=\s*(.*\S)\s*$')

    for line in infile.readlines():
        line = re.sub('[\r\n]', '', line)
        if re.search(itemMatch, line):
            if gotItem == 0:
                gotItem = 1
                current_dict = {}
                item = re.sub(itemMatch, '\\1', line)
                value = re.sub(itemMatch, '\\2', line).strip()
            elif gotItem == 1:
                navitems.append(current_dict)
                gotItem = 1
                current_dict = {}
                item = re.sub(itemMatch, '\\1', line)
                value = re.sub(itemMatch, '\\2', line).strip()

        elif re.match(keyMatch, line):
            key = re.sub(keyMatch, '\\1', line)
            value = re.sub(keyMatch, '\\2', line).strip()
            if gotItem:
                current_dict[key] = value
    return navitems

navigator_items = readNavInfo(navigatorFile)

if args_dict['v']:
    print("{} navigator items have been identified...".format(len(navigator_items)))

numNavItems = len(navigator_items)

indices_list = []
numMapAcquire = 0
numAcqPoints = 0
indices_file = open(indices_file, 'w')
guide_file = open(guide_file, 'w')

for nav_index in range(0, numNavItems):
    nav_item = navigator_items[nav_index]

    if 'Acquire' in navigator_items[nav_index].keys():
        if nav_item['Acquire'] == '1':  # and nav_item['Type'] == '2': # this should also check whether the navigator item is a map.
            numMapAcquire += 1
            point_str = ''
            # Navigator items set to acquire represent hole maps, and serve as anchors.
            points = IdentifyAcquisitionPoints(nav_index, navigator_items)
            if args_dict['v']:
                print('Navigator index {} is an acquisition template and contains {} points.'.format(nav_index,
                                                                                                     len(points)))
            if len(points) >= 1:
                numAcqPoints += len(points)
                for point in points:
                    point_str = point_str + ' ' + str((int(point) + 1))
                    indices_list.append(str((int(point) + 1)))
            indices_file.write(point_str + '\n')
    guide_file.write(str(len(indices_list)) + '\n')

indices_file.close()
guide_file.close()

if numMapAcquire == 0:
    print("There don't appear to be any view-maps set for acquisitions (A). Please check this and try again.")
    quit()

pointsPerMap = round(numAcqPoints / numMapAcquire, 2)
                    
print("Processed navigigator file {}.\n{} hole/area maps are set to acquire, and {} points for high-magnification acquisition were processed.\nThere are {} points per map. Please check that this makes sense by referring to information listed in the SerialEM navigator panel.".format(
        args_dict['nav'], numMapAcquire, numAcqPoints, pointsPerMap))

if args_dict['s']:
    createSettingsFiles()
    scriptOutputPath=os.path.join(args_dict['o'],'runArbitrEM.txt')
    writeArbitrEMScript(args_dict['scriptTemplate'], settingsDict, scriptOutputPath)  
             
print('Finished.')