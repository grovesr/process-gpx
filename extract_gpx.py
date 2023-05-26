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
import math
import requests


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

months = ['', 'january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december']
monthsShort = ['', 'jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
weekdays = ['monday','tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
weekdaysShort = ['mon','tues', 'wed', 'thu', 'fri', 'sat', 'sun']

class CLIError(Exception):
    '''Generic exception to raise and log different fatal errors.'''
    def __init__(self, msg):
        super(CLIError).__init__(type(self))
        self.msg = "E: %s" % msg
    def __str__(self):
        return self.msg
    def __unicode__(self):
        return self.msg
    
class GeoLocation:
    '''
    Class representing a coordinate on a sphere, most likely Earth.
    
    This class is based from the code smaple in this paper:
        http://janmatuschek.de/LatitudeLongitudeBoundingCoordinates
        
    The owner of that website, Jan Philip Matuschek, is the full owner of 
    his intellectual property. This class is simply a Python port of his very
    useful Java code. All code written by Jan Philip Matuschek and ported by Jeremy Fein (jfein) 
    (which is all of this class) is owned by Jan Philip Matuschek.
    '''
 
 
    MIN_LAT = math.radians(-90)
    MAX_LAT = math.radians(90)
    MIN_LON = math.radians(-180)
    MAX_LON = math.radians(180)
    MAX_COURSE = 2 * math.pi
    MIN_COURSE = 0
    
    EARTH_RADIUS = 6378.1  # kilometers
    
    
    @classmethod
    def from_degrees(cls, deg_lat, deg_lon, deg_course = MIN_COURSE):
        rad_lat = math.radians(deg_lat)
        rad_lon = math.radians(deg_lon)
        rad_course = math.radians(deg_course)
        return GeoLocation(rad_lat, rad_lon, deg_lat, deg_lon, rad_course, deg_course)
        
    @classmethod
    def from_radians(cls, rad_lat, rad_lon, rad_course = MIN_COURSE):
        deg_lat = math.degrees(rad_lat)
        deg_lon = math.degrees(rad_lon)
        deg_course = math.degrees(rad_course)
        return GeoLocation(rad_lat, rad_lon, deg_lat, deg_lon, rad_course, deg_course)
    
    
    def __init__(
            self,
            rad_lat,
            rad_lon,
            deg_lat,
            deg_lon,
            rad_course,
            deg_course
    ):
        self.rad_lat = float(rad_lat)
        self.rad_lon = float(rad_lon)
        self.deg_lat = float(deg_lat)
        self.deg_lon = float(deg_lon)
        self.rad_course = float(rad_course)
        self.deg_course = int(deg_course)
        self._check_bounds()
        
    def __str__(self):
        degree_sign= u'\N{DEGREE SIGN}'
        return ("({0:.4f}deg, {1:.4f}deg) = ({2:.6f}rad, {3:.6f}rad), course={4:3d}deg").format(
            self.deg_lat, self.deg_lon, self.rad_lat, self.rad_lon, int(self.deg_course))
        
    def _check_bounds(self):
        if (self.rad_lat < GeoLocation.MIN_LAT 
                or self.rad_lat > GeoLocation.MAX_LAT 
                or self.rad_lon < GeoLocation.MIN_LON 
                or self.rad_lon > GeoLocation.MAX_LON
                or self.rad_course < GeoLocation.MIN_COURSE
                or self.rad_course > GeoLocation.MAX_COURSE):
            raise Exception("Illegal arguments")
        
    def set_deg_course(self, course_in_degrees):
        self.deg_course = int(course_in_degrees)
        self.rad_course = math.radians(self.deg_course)
        self._check_bounds()
        
    def set_rad_course(self, course_in_radians):
        self.rad_course = course_in_radians
        self.deg_course = int(math.degrees(self.rad_course))
        self._check_bounds()
            
    def distance_to(self, other, radius=EARTH_RADIUS):
        '''
        Computes the great circle distance between this GeoLocation instance
        and the other.
        '''
        arg = math.sin(self.rad_lat) * math.sin(other.rad_lat) + math.cos(self.rad_lat) * math.cos(other.rad_lat) * math.cos(self.rad_lon - other.rad_lon)
        if arg < -1 or arg > 1:
            arg = round(arg)
        return radius * math.acos(arg)
            
    def bounding_locations(self, distance, radius=EARTH_RADIUS):
        '''
        Computes the bounding coordinates of all points on the surface
        of a sphere that has a great circle distance to the point represented
        by this GeoLocation instance that is less or equal to the distance argument.
        
        Param:
            distance - the distance from the point represented by this GeoLocation
                       instance. Must be measured in the same unit as the radius
                       argument (which is kilometers by default)
            
            radius   - the radius of the sphere. defaults to Earth's radius.
            
        Returns a list of two GeoLoations - the SW corner and the NE corner - that
        represents the bounding box.
        '''
        
        if radius < 0 or distance < 0:
            raise Exception("Illegal arguments")
            
        # angular distance in radians on a great circle
        rad_dist = distance / radius
        
        min_lat = self.rad_lat - rad_dist
        max_lat = self.rad_lat + rad_dist
        
        if min_lat > GeoLocation.MIN_LAT and max_lat < GeoLocation.MAX_LAT:
            delta_lon = math.asin(math.sin(rad_dist) / math.cos(self.rad_lat))
            
            min_lon = self.rad_lon - delta_lon
            if min_lon < GeoLocation.MIN_LON:
                min_lon += 2 * math.pi
                
            max_lon = self.rad_lon + delta_lon
            if max_lon > GeoLocation.MAX_LON:
                max_lon -= 2 * math.pi
        # a pole is within the distance
        else:
            min_lat = max(min_lat, GeoLocation.MIN_LAT)
            max_lat = min(max_lat, GeoLocation.MAX_LAT)
            min_lon = GeoLocation.MIN_LON
            max_lon = GeoLocation.MAX_LON
        
        return [ GeoLocation.from_radians(min_lat, min_lon) , 
            GeoLocation.from_radians(max_lat, max_lon) ]

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
    indent = len(program_name) * " "
    try:
        # Setup argument parser
        parser = ArgumentParser(description=program_license, formatter_class=RawDescriptionHelpFormatter)
        parser.add_argument("-e", "--extract", dest="extractDates", action="store_true", help="extract all dates that have tracks associated with them in input file", default=False)
        parser.add_argument("-c", "--combine", dest="combineAllTracksForDate", action="store_true", help="combine all tracks that match the datetime specified into one output file", default=False)
        parser.add_argument("-m", "--merge", dest="mergeFiles", action="store_true", help="merge tracks from one or more input file into a single output file", default=False)
        parser.add_argument("-p", "--pretty", dest="prettify", action="store_true", help="prettify the output file", default=False)
        parser.add_argument("-k", "--kml", dest="genKml", action="store_true", help="generate a KML formatted file in addition to the gpx file", default=False)
        parser.add_argument("-n", "--nopoints", dest="noKmlPoints", action="store_true", help="in generated KML file remove point Placemarks", default=False)
        parser.add_argument("-b", "--addBlogUrl", dest="addBlogUrl", action="store_true", help="In generated KML file add blog post URLs to the Placemarks", default=False)
        parser.add_argument("-t", "--thinDistance", dest="thinDistance", help="thin out track points to reduce file size by removing all points within this distance in kilometers from each other [default: %(default)s]", default=0)
        parser.add_argument("-r", "--thinOrientation", dest="thinOrientation", help="thin out track points to reduce file size by removing all points with an orientation aspect within this number of degrees of each other [default: %(default)s]", default=0)
        parser.add_argument("-d", "--date", dest="trackDatetimes", action="append", help="extract track from datetime (ISO format yyyy-mm-dd [hh:mm:ss]). Can be specified multiple times to append", default=[])
        parser.add_argument("-o", "--output", dest="outputFile", help="direct output to this destination [default: %(default)s]", default='extracted_track.gpx')
        parser.add_argument("-i", "--input", dest="inputFiles", action="append", help="source gpx file containing one or more tracks. Can be specified multiple times to search or combine multiple files", default=[])
        # Process arguments
        try:
            args = parser.parse_args()
        except Exception as e:
            raise(e)

        trackDatetimes = args.trackDatetimes
        inputFiles = args.inputFiles
        extractDates = args.extractDates
        outputFile = args.outputFile
        combineAllTracksForDate = args.combineAllTracksForDate
        mergeFiles = args.mergeFiles
        thinDistance = float(args.thinDistance)
        thinOrientation = int(args.thinOrientation)
        prettify = args.prettify
        genKml = args.genKml
        addBlogUrl = args.addBlogUrl
        noKmlPoints = args.noKmlPoints
        if thinOrientation < 0:
            sys.stderr.write(program_name + ":\n")
            sys.stderr.write(indent + "thinOrientatio must be >= 0\n")
            return 2
        if thinDistance < 0:
            sys.stderr.write(program_name + ":\n")
            sys.stderr.write(indent + "thinDistance must be >= 0\n")
            return 2
        if thinDistance > 0 and thinOrientation > 0:
            sys.stderr.write(program_name + ":\n")
            sys.stderr.write(indent + "You can't specify thinOrientation and thinDistance at the same time. Choose one or the other.\n")
            return 2
        if len(inputFiles) == 0:
            sys.stderr.write(program_name + ":\n")
            sys.stderr.write(indent + "no input file(s) specified with -i option\n")
            return 2
        if len(trackDatetimes) == 0 and not (extractDates or mergeFiles):
            sys.stderr.write(program_name + ":\n")
            sys.stderr.write(indent + "no datetime specified with -d option\n")
            return 2
        if noKmlPoints  and not genKml:
            sys.stderr.write(program_name + ":\n")
            sys.stderr.write(indent + "you asked to not generate KML Placemark points (-n) but did not ask to generate a KML file (-k)\n")
            return 2
        if addBlogUrl  and not genKml:
            sys.stderr.write(program_name + ":\n")
            sys.stderr.write(indent + "you asked to add blog URLs to Placemarks (-b) but did not ask to generate a KML file (-k)\n")
            return 2
        if mergeFiles  and (thinOrientation or thinDistance):
            sys.stderr.write(program_name + ":\n")
            sys.stderr.write(indent + "you can't merge files (-m) and thin them as well\n")
            return 2
        parsedTrackDatetimes = {}
        for trackDatetime in trackDatetimes:
            try:
                checkedDatetime = datetime.fromisoformat(trackDatetime)
            except Exception as e:
                sys.stderr.write(program_name + ":\n")
                sys.stderr.write(indent + repr(e)+"\n")
                return 2
            if len(trackDatetime.strip()) > 10:
                parsedTrackDatetimes[checkedDatetime.strftime('%Y-%m-%d %H:%M')] = checkedDatetime
            else:
                parsedTrackDatetimes[checkedDatetime.strftime('%Y-%m-%d')] = checkedDatetime
    except KeyboardInterrupt:
        ### handle keyboard interrupt ###
        return 0
    except Exception as e:
        if DEBUG or TESTRUN:
            raise(e)
        sys.stderr.write(program_name + ": " + repr(e) + "\n")
        sys.stderr.write(indent + "for help use --help\n")
        return 2
    selectedTracks = []
    tracksForDates= {}
    for inputFile in inputFiles:
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
        if gpxSoup.contents:
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
            if mergeFiles:
                trackNames = gpxSoup('name', string=re.compile('Active Log'))
                for trackName in trackNames:
                    track = trackName.find_parent('trk')
                    if prettify:
                        trackString = track.prettify()
                    else:
                        trackString = str(track)
                    selectedTracks.append(trackString)
            else:
                try:
                    tracksFound = 0
                    courseFound = True
                    combinedDates = ''
                    for trackDatetimeString, trackDatetimeObject in parsedTrackDatetimes.items():
                        if not trackDatetimeString in tracksForDates:
                            trackNames = gpxSoup.find_all('name', string=re.compile(trackDatetimeString))
                            if len(trackNames) > 0:
                                tracksForDates[trackDatetimeString] = {}
                                tracksForDates[trackDatetimeString]['datetimeObj'] = trackDatetimeObject
                                tracksForDates[trackDatetimeString]['foundTrack'] = False
                                tracksForDates[trackDatetimeString]['trackNames'] = trackNames
                                tracksForDates[trackDatetimeString]['foundTrack'] = True
                                tracksFound = tracksFound + len(tracksForDates[trackDatetimeString]['trackNames'])
                                combinedTracks = ''
                                trackDistance = 0
                                for trackName in tracksForDates[trackDatetimeString]['trackNames']:
                                    if not combineAllTracksForDate:
                                        trackDistance = 0
                                    track = trackName.find_parent('trk')
                                    if thinDistance > 0 or thinOrientation > 0 or True:
                                        trackSegs = track.find_all('trkseg')
                                        for trackSeg in trackSegs:
                                            segDistance = 0
                                            trackPoint = trackSeg.find('trkpt')
                                            if trackPoint is not None and trackPoint['lat'] is not None and trackPoint['lon'] is not None:
                                                if trackPoint.find('course') is not None:
                                                    course = int(float(trackPoint.find('course').string))
                                                else:
                                                    course = math.degrees(GeoLocation.MIN_COURSE)
                                                    courseFound = False
                                                geoLocation = GeoLocation.from_degrees(float(trackPoint['lat']), float(trackPoint['lon']), course)
                                                nextTrackPoint = trackPoint.find_next_sibling('trkpt')
                                                if nextTrackPoint is not None and nextTrackPoint['lat'] is not None and nextTrackPoint['lon'] is not None:
                                                    foundLastTrackPoint = False
                                                    while not foundLastTrackPoint:  
                                                        if nextTrackPoint.find('course') is not None:
                                                            course = int(float(nextTrackPoint.find('course').string))
                                                        else:
                                                            course = math.degrees(GeoLocation.MIN_COURSE)
                                                            courseFound = False
                                                        nextGeoLocation = GeoLocation.from_degrees(float(nextTrackPoint['lat']), float(nextTrackPoint['lon']), course)
                                                        tempTrackPoint = nextTrackPoint.find_next_sibling('trkpt')
                                                        foundLastTrackPoint = tempTrackPoint is None
                                                        if not thinDistance and not thinOrientation:
                                                            segDistance = segDistance + geoLocation.distance_to(nextGeoLocation)
                                                            geoLocation = nextGeoLocation
                                                        if thinDistance:
                                                            if geoLocation.distance_to(nextGeoLocation) > thinDistance or foundLastTrackPoint:
                                                                segDistance = segDistance + geoLocation.distance_to(nextGeoLocation)
                                                                geoLocation = nextGeoLocation
                                                            else:
                                                                nextTrackPoint.decompose()
                                                        if thinOrientation:
                                                            if not courseFound:
                                                                sys.stderr.write(program_name + ":\n")
                                                                sys.stderr.write(indent + "Some course information missing in '" + inputFile+"' unable to thinOrientation\n")
                                                                return 2 
                                                            if abs(nextGeoLocation.deg_course - geoLocation.deg_course) > thinOrientation or foundLastTrackPoint:
                                                                segDistance = segDistance + geoLocation.distance_to(nextGeoLocation)
                                                                geoLocation = nextGeoLocation
                                                            else:
                                                                nextTrackPoint.decompose()
                                                        nextTrackPoint = tempTrackPoint
                                            trackDistance = trackDistance + segDistance
                                    comment = gpxSoup.new_tag('cmt')
                                    if trackDistance > 0:
                                        comment.string = 'Miles driven: %s' % round(trackDistance*0.62)
                                    track.insert(1, comment)
                                    if combineAllTracksForDate:
                                        # remove the old name tag if combining
                                        track.find('name').decompose()
                                    if prettify:
                                        trackString = track.prettify()
                                    else:
                                        trackString = str(track)
                                    if combineAllTracksForDate:
                                        trackDate = trackDatetimeObject.strftime('%Y-%m-%d %H:%M')
                                        if trackDate not in combinedDates:
                                            combinedDates = combinedDates + trackDatetimeObject.strftime('%Y-%m-%d %H:%M') + ', '
                                        trackString = trackString.replace('<trk>', '').replace('</trk>', '')
                                    combinedTracks = combinedTracks + trackString
                                selectedTracks.append(combinedTracks)      
                    if tracksFound > 0:
                        if tracksFound > 1  and not combineAllTracksForDate:
                            sys.stderr.write(program_name + ":\n")
                            sys.stderr.write(indent + "More than one track found for '" + str(parsedTrackDatetimes.keys()) + "' in '" + inputFile+"'. To combine use -c option.\n")
                            for names in [item['trackNames'] for key, item in tracksForDates.items()]:
                                for name in names:
                                    print(name.get_text())
                            return 2
                except Exception as e:
                    sys.stderr.write(program_name + ":\n")
                    sys.stderr.write(indent + repr(e)+"\n")
                    return 2
    if len(selectedTracks) == 0:
        sys.stderr.write(indent + "No matching tracks found for '" + str(parsedTrackDatetimes.keys()) + "' in file(s) '" + str(inputFiles) + "'\n")
        return 2
        
    gpxHead = '''<?xml version="1.0" encoding="utf-8"?>
<gpx version="1.0"
 creator="extract_gpx.pl by Rob Groves"
 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
 xmlns="http://www.topografix.com/GPX/1/0"
 xmlns:gpxx="http://www.garmin.com/xmlschemas/GpxExtensions/v3" 
 xmlns:gpxtpx="http://www.garmin.com/xmlschemas/TrackPointExtension/v2" 
 xmlns:trp="http://www.garmin.com/xmlschemas/TripExtensions/v1"
 xsi:schemaLocation="http://www.topografix.com/GPX/1/0 http://www.topografix.com/GPX/1/0/gpx.xsd">
'''
    gpxTail = '''
</gpx>
    '''
    kmlHead = '''<?xml version="1.0" encoding="UTF-8"?> 
<kml 
  xmlns="http://www.opengis.net/kml/2.2" 
  xmlns:kml="http://www.opengis.net/kml/2.2">
  <Document>
    <visibility>1</visibility>
    <Style id="blue">
      <LineStyle>
        <color>C8FF7800</color>
        <width>3</width>
      </LineStyle>
    </Style>
    <Style id="red">
      <LineStyle>
        <color>C81400FF</color>
        <width>3</width>
      </LineStyle>
    </Style>
    <Style id="paddle-red-circle">
      <IconStyle>
        <color>C8FF7800</color>
        <Icon>
          <href>http://maps.google.com/mapfiles/kml/paddle/red-circle.png</href>
        </Icon>
      </IconStyle>
    </Style>
    <Folder>  
'''
    kmlTail = '''
    </Folder>
  </Document>
</kml>
'''
    combinedTracks = ''
    if combineAllTracksForDate:
        combinedTracks = combinedTracks + '<trk><name>Active Log: Combined track from %s</name>' % combinedDates.rstrip(', ')
    for selectedTrack in selectedTracks:
        combinedTracks = combinedTracks + selectedTrack.strip() + '\n'
    if combineAllTracksForDate:
        combinedTracks = combinedTracks + '</trk>'
    outString = gpxHead + combinedTracks + gpxTail
    try:
        with open(outputFile, 'w') as f:
                f.write(outString)
    except OSError as e:
        sys.stderr.write(program_name + ":\n")
        sys.stderr.write(indent + "Unable to open output file '" + outputFile+"'\n")
        sys.stderr.write(indent + " " + repr(e)+"\n")
        return 2
    if genKml:
        # make a new beautiful soup object to extract the tracks from the gpx output string
        kmlSoup = bs(outString, 'xml')
        if kmlSoup.contents:
            trackNames = kmlSoup.find_all('name', string=re.compile('Active Log'))
            selectedTracks = []
            for trackName in trackNames:
                selectedTracks.append(trackName.find_parent('trk'))
            combinedKml = ''
            for selectedTrack in selectedTracks:
                if combineAllTracksForDate:
                    timedate = datetime.fromisoformat(combinedDates.rstrip(', '))
                else:
                    date = re.findall('\d\d\d\d?-?\d?\d?-?\d?\d? ?\d?\d?:?\d?\d', selectedTrack.find('name').string)
                    timedate = datetime.fromisoformat(date[0])
                month = months[timedate.month]
                weekday = weekdays[timedate.weekday()]
                trackName = 'Our travels on %s %s %d, %d' % (weekday, month, timedate.day, timedate.year)
                comment = selectedTrack.find('cmt')
                if comment:
                    cmt = comment.string
                else:
                    cmt = ''
                blogUrl = ''
                if addBlogUrl:
                    blogUrl = 'https://36yrdream.com/'
                    weekday = weekdays[timedate.weekday()]
                    weekdayShort = weekdaysShort[timedate.weekday()]
                    month = months[timedate.month]
                    monthShort = monthsShort[timedate.month]
                    date = timedate.day
                    year = timedate.year
                    urlsToTry = [
                        '%s%s-%s-%s-%s' %(blogUrl, weekday, month, date, year),
                        '%s%s-%s-%s-%s' %(blogUrl, weekdayShort, month, date, year),
                        '%s%s-%s-%s-%s' %(blogUrl, weekday, monthShort, date, year),
                        '%s%s-%s-%s-%s' %(blogUrl, weekdayShort, monthShort, date, year),
                        '%s%s-%s-%s' %(blogUrl, weekday, month, date),
                        '%s%s-%s-%s' %(blogUrl, weekdayShort, month, date),
                        '%s%s-%s-%s' %(blogUrl, weekday, monthShort, date),
                        '%s%s-%s-%s' %(blogUrl, weekdayShort, monthShort, date)
                        ]
                    found = False
                    for url in urlsToTry:
                        response = requests.head(url, allow_redirects = True)
                        if response.status_code == 200:
                            blogUrl = url
                            found = True
                            break
                    if not found:
                        blogUrl = 'unable to find blog URL'
                description = '<![CDATA[<b>%s</b><br />%s]]>' % (cmt, blogUrl)
                trackPlacemark = '<Placemark><styleUrl>#blue</styleUrl><name>%s</name><description>%s</description><LineString><coordinates>' % (trackName, description)
                combinedKml = combinedKml + trackPlacemark
                trackSegs = selectedTrack.find_all('trkseg')
                for trackSeg in trackSegs:
                    trackPoints = trackSeg.find_all('trkpt')
                    for trackPoint in trackPoints:
                        combinedKml = combinedKml + trackPoint['lon'] + ',' + trackPoint['lat'] + ',' + trackPoint.find('ele').string + ' '
                combinedKml = combinedKml.rstrip(' ') + '</coordinates></LineString></Placemark>'
                if not noKmlPoints: 
                    combinedKml = combinedKml + '<Placemark><styleUrl>#paddle-red-circle</styleUrl><name>%s</name><description>%s</description><Point><coordinates>%s,%s,%s</coordinates></Point></Placemark>' % (trackName, description, trackPoint['lon'], trackPoint['lat'], trackPoint.find('ele').string)
            if len(selectedTracks) > 1:
                #make the final track red
                combinedKml = (combinedKml[::-1].replace('eulb#','der#', 1))[::-1]
            kmlOutString = kmlHead + combinedKml + kmlTail
            kmlOutputFile = outputFile.replace('.gpx', '.kml')
            try:
                with open(kmlOutputFile, 'w') as f:
                        f.write(kmlOutString)
            except OSError as e:
                sys.stderr.write(program_name + ":\n")
                sys.stderr.write(indent + "Unable to open output file '" + kmlOutputFile+"'\n")
                sys.stderr.write(indent + " " + repr(e)+"\n")
                return 2
        else:
            sys.stderr.write(program_name + ":\n")
            sys.stderr.write(indent + "Unable to parse the gpx output string to create the KML file\n")
            return 2
    if DEBUG:
        print("trackDatetime: " + str(parsedTrackDatetimes))
        print("inputFile: " + inputFile)
        print("outputFile: " + outputFile)
        print("Length of output file string: " + str(len(outString)))
        if genKml:
            print("kmlOutputFile: " + kmlOutputFile)
            print("Length of KML output file string: " + str(len(kmlOutString)))
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
