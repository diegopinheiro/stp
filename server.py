#!/usr/bin/env python
"""Mosaicking routine."""

import os

import config
import ee
import jinja2
import webapp2
import datetime
import maskingTools

anos=[2013,2014,2015]
cloudThresh=0.15
zShadowThresh=-0.5
  
jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)))


class MainPage(webapp2.RequestHandler):

  def get(self):                             # pylint: disable=g-bad-name
    """Request an image from Earth Engine and render it to a web page."""
    ee.Initialize(config.EE_CREDENTIALS)

    def computeMosaicId(year,cloudThresh,zShadowThresh):
      start = datetime.date(year,1,1).isoformat()
      end = datetime.date(year,12,1).isoformat()

      # A mapping from a common name to the sensor-specific bands.
      LC8_BANDS = ['B2',   'B3',    'B4',  'B5',  'B6',    'B7',    'B10']
      STD_NAMES = ['blue', 'green', 'red', 'nir', 'swir1', 'swir2', 'temp']


      area1=ee.Geometry.Polygon(
                  [[[8.173828125, 1.867345112921926],
                    [6.0369873046875, 1.8618548574369724],
                    [5.99853515625, -0.29113644247137116],
                    [8.1793212890625, -0.29113644247137116]]]);
      #Compute a cloud score.  This expects the input image to have the common
      #band names: ["red", "blue", etc], so it can work across sensors.

      def addCloudThreshold (img):
        return img.addBands(ee.Image(cloudThresh).select([0],['cloudThresh']))
      def addShadowThreshold (img):
        return img.addBands(ee.Image(zShadowThresh).select([0],['zShadowThresh']))

      #Filter the TOA collection to a time-range and area, add the cloud threshold band and filter clouds
      collection = ee.ImageCollection('LC8_L1T_TOA').select(LC8_BANDS, STD_NAMES).\
        filterDate(start,end).\
        map(addCloudThreshold).\
        map(addShadowThreshold).\
        map(maskingTools.maskCloudsAndSuch)

      collection_masked_shadows=maskingTools.maskShadows(collection)
      img=collection_masked_shadows.median().select(['swir1','nir','red'])
      #compute last value (can be useful for monitoring once SR imagens are available)
      #col_sorted = collection_masked_shadows.select(['swir1','nir','red']).sort('system:time_start', False)    #Order adquisition by date
      #img1= col_sorted.mosaic()
  
      mapid=img.getMapId({'min':0.0,'max': 0.5})
      
      return mapid
    
    mapids=[]
    tokens=[]
    for ano in anos:
      tmp=computeMosaicId(ano,cloudThresh,zShadowThresh)
      mapids.append(str(tmp['mapid'])) #str functions avoid having 
      tokens.append(str(tmp['token'])) # ugly 'u' before strings    
    template_values={'anos':anos}
    template_values.update({'mapids': mapids})
    template_values.update({'tokens': tokens})
 
    template = jinja_environment.get_template('index.html')
    self.response.out.write(template.render(template_values))

app = webapp2.WSGIApplication([('/', MainPage)], debug=True)
