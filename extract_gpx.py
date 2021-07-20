#!/usr/bin/python3
# encoding: utf-8
'''
extract_gpx -- extract a gpx track from a fle given a date

extract_gpx is a CLI program that extracts a single gpx track from a gpx file containing an arbitrary number of tracks

It defines classes_and_methods

@author:     Rob Groves

@copyright:  2021 organization_name. All rights reserved.

@license:    license

@contact:    36yrdream@gmail.com
@deffield    updated: Updated
'''

import sys
import os
import re


from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
from datetime import datetime
from bs4 import BeautifulSoup as bs

__all__ = []
__version__ = 0.1
__date__ = '2021-07-13'
__updated__ = '2021-07-13'

DEBUG = 1
TESTRUN = 0
PROFILE = 0

class CLIError(Exception):
    '''Generic exception to raise and log different fatal errors.'''
    def __init__(self, msg):
        super(CLIError).__init__(type(self))
        self.msg = "E: %s" % msg
    def __str__(self):
        return self.msg
    def __unicode__(self):
        return self.msg

def main(argv=None): # IGNORE:C0111
    '''Command line options.'''

    if argv is None:
        argv = sys.argv
    else:
        sys.argv.extend(argv)

    program_name = os.path.basename(sys.argv[0])
    program_version = "v%s" % __version__
    program_build_date = str(__updated__)
    program_version_message = '%%(prog)s %s (%s)' % (program_version, program_build_date)
    program_shortdesc = __import__('__main__').__doc__.split("\n")[1]
    program_license = '''%s

  Created by Rob Groves on %s.
  Copyright 2021 organization_name. All rights reserved.

  Licensed under the Apache License 2.0
  http://www.apache.org/licenses/LICENSE-2.0

  Distributed on an "AS IS" basis without warranties
  or conditions of any kind, either express or implied.

USAGE
''' % (program_shortdesc, str(__date__))
    today = datetime.today().strftime('%Y-%m-%d')
    indent = len(program_name) * " "
    try:
        # Setup argument parser
        parser = ArgumentParser(description=program_license, formatter_class=RawDescriptionHelpFormatter)
        parser.add_argument("-e", "--extract", dest="extractDates", action="store_true", help="extract all dates that have tracks associated with them in input file", default=False)
        parser.add_argument("-c", "--combine", dest="combineAllTracksForDate", action="store_true", help="combine all tracks that match the datetime specified into one output file", default=False)
        parser.add_argument("-d", "--date", dest="trackDatetimes", action="append", help="extract track from datetime (ISO format yyyy-mm-dd [hh:mm:ss]). Can be specified multiple times to append.", default=[])
        parser.add_argument("-o", "--output", dest="outputFile", help="direct output to this destination [default: %(default)s]", default='extracted_track.gpx')
        parser.add_argument("-i", "--input", dest="inputFile", help="source gpx file containing one or more tracks [default: %(default)s]", default='Current.gpx')
        # Process arguments
        try:
            args = parser.parse_args()
        except Exception as e:
            raise(e)

        trackDatetimes = args.trackDatetimes
        extractDates = args.extractDates
        if len(trackDatetimes) == 0 and not extractDates:
            sys.stderr.write(program_name + ":\n")
            sys.stderr.write(indent + "no datetime specified with -d option")
            return 2
        parsedTrackDatetimes = []
        for trackDatetime in trackDatetimes:
            try:
                checkedDatetime = datetime.fromisoformat(trackDatetime)
            except Exception as e:
                sys.stderr.write(program_name + ":\n")
                sys.stderr.write(indent + repr(e)+"\n")
                return 2
            if len(trackDatetime.strip()) > 10:
                parsedTrackDatetimes.append(checkedDatetime.strftime('%Y-%m-%d %H:%M'))
            else:
                parsedTrackDatetimes.append(checkedDatetime.strftime('%Y-%m-%d'))
        inputFile = args.inputFile
        outputFile = args.outputFile
        combineAllTracksForDate = args.combineAllTracksForDate
        try:
            with open(inputFile) as f:
                gpxSoup = bs(f,'xml')
        except OSError as e:
            sys.stderr.write(program_name + ":\n")
            sys.stderr.write(indent + "Unable to open input file '" + inputFile+"'\n")
            sys.stderr.write(indent + " " + repr(e)+"\n")
            return 2
        except Exception as e:
            sys.stderr.write(program_name + ":\n")
            sys.stderr.write(indent + repr(e)+"\n")
            return 2
    except KeyboardInterrupt:
        ### handle keyboard interrupt ###
        return 0
    except Exception as e:
        if DEBUG or TESTRUN:
            raise(e)
        sys.stderr.write(program_name + ": " + repr(e) + "\n")
        sys.stderr.write(indent + "for help use --help\n")
        return 2
    if not gpxSoup.contents:
        sys.stderr.write(program_name + ":\n")
        sys.stderr.write(indent + "No matching track found in '" + inputFile+"'\n")
        return 2
    if extractDates:
        try:
            trackNames = gpxSoup('name', string=re.compile('Active Log'))
            if trackNames is not None:
                for name in trackNames:
                    print(name.get_text())
            else:
                sys.stderr.write(program_name + ":\n")
                sys.stderr.write(indent + "No Active Log tracks found in '" + inputFile+"'\n")
                return 2 
        except Exception as e:
            sys.stderr.write(program_name + ":\n")
            sys.stderr.write(indent + repr(e)+"\n")
            return 2
        return 0
    try:
        selectedTracks = []
        for trackDatetime in parsedTrackDatetimes:
            trackNames = gpxSoup.find_all('name', string=re.compile(trackDatetime))
            if len(trackNames) > 0:
                if len(trackNames) > 1  and not combineAllTracksForDate:
                    sys.stderr.write(program_name + ":\n")
                    sys.stderr.write(indent + "More than one track found for that date in '" + inputFile+"'\n")
                    for name in trackNames:
                        print(name.get_text())
                    return 2
                else:
                    for trackName in trackNames:
                        selectedTracks.append(str(trackName.find_parent('trk')))
            else:
                sys.stderr.write(program_name + ":\n")
                sys.stderr.write(indent + "No matching track for datetime '" + trackDatetime + "' found in '" + inputFile+"'\n")
                return 2 
    except Exception as e:
        sys.stderr.write(program_name + ":\n")
        sys.stderr.write(indent + repr(e)+"\n")
        return 2
    gpxHead = '''<?xml version="1.0" encoding="utf-8"?>
<gpx version="1.0"
 creator="extract_gpx.pl by Rob Groves"
 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
 xmlns="http://www.topografix.com/GPX/1/0"
 xsi:schemaLocation="http://www.topografix.com/GPX/1/0 http://www.topografix.com/GPX/1/0/gpx.xsd">
'''
    gpxTail = '''
</gpx>
    '''
    combinedTracks = ''
    for selectedTrack in selectedTracks:
        combinedTracks = combinedTracks + selectedTrack.strip() + '\n'
    outString = gpxHead + combinedTracks + gpxTail
    try:
        with open(outputFile, 'w') as f:
                f.write(outString)
    except OSError as e:
        sys.stderr.write(program_name + ":\n")
        sys.stderr.write(indent + "Unable to open output file '" + outputFile+"'\n")
        sys.stderr.write(indent + " " + repr(e)+"\n")
        return 2
    if DEBUG:
        print("trackDatetime: " + str(parsedTrackDatetimes))
        print("inputFile: " + inputFile)
        print("outputFile: " + outputFile)
        print("Length of output file string: " + str(len(outString)))
    print("outputFile: " + outputFile)
    return 0

if __name__ == "__main__":
    if TESTRUN:
        import doctest
        doctest.testmod()
    if PROFILE:
        import cProfile
        import pstats
        profile_filename = 'extract_gpx_profile.txt'
        cProfile.run('main()', profile_filename)
        statsfile = open("profile_stats.txt", "wb")
        p = pstats.Stats(profile_filename, stream=statsfile)
        stats = p.strip_dirs().sort_stats('cumulative')
        stats.print_stats()
        statsfile.close()
        sys.exit(0)
    sys.exit(main())