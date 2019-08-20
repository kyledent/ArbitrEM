#! /usr/bin/env python
# A script by Kyle Dent for use with ArbitrEM SerialEM script. Updated 27 July 2019
# When running the script on a navigator file, please make sure that all polygons, medium magnification 
# montages and acquisition template points have been removed.
# Please make sure that the first item in the navigator is your Atlas/Specimen Grid Montage.
# Please use a hole diameter that is 20% greater than the size of the measured hole.
# Navigator parsing code borrowed from David Mastronarde's supermont.py. 
# TODO: determine navigator file name and prefix output files with this name for convenience?
# TODO: plot position of acquisition points within each acquisition template.
# TODO: output ArbitrEM script with path to settings files imbedded along with other parameters

from __future__ import division

import math, re, sys, argparse, os, sys

parser = argparse.ArgumentParser(description='ArbitrEM script to process a SerialEM navigator file to associate acquisition points with specific acquisition templates')
parser.add_argument('--o', default='./arbitrEM', help='output directory for ArbitrEM files')
parser.add_argument('--d', default=None, type=float, help='the diameter of the targetting-map in micrometers')
parser.add_argument('--nav', default=None, help='the SerialEM navigator file (not in XML format)')
parser.add_argument('--v', default='False',help='Request verbose output for diagnositic purposes')
parser.add_argument('--s', default='True',help='set to "True" to request verbose output for diagnositic purposes')
parser.add_argument('--customShiftOffset', default='0.0 0.0',help='apply a custom beam-image shift offset')
parser.add_argument('--defocusRange', default='-1 -2.6 0.2',help='the defocus range and step')
parser.add_argument('--earlyReturn', default='1',help=' 0 - early return ON, 1 - early return OFF i.e. SerialEM parameter values')

args_dict = vars(parser.parse_args())

try:
    args_dict['v'] = eval(args_dict['v'])
    args_dict['s'] = eval(args_dict['s'])

except Exception as e:
    print('Problem interpreting boolean variable. Please check you spelling.')
if None in args_dict.values():
    print('Please check input parameters and try again.')
    quit()

settingsFiles = {'customShift.txt':args_dict['customShiftOffset'],
                 'defocusRange.txt':args_dict['defocusRange'],
                 'earlyReturn.txt':args_dict['earlyReturn']}

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

print('Finished.')