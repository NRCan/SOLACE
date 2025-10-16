# -*- coding: utf-8 -*-
"""
Created on Thu Jan 26 15:10:27 2023

@author: egaucher
"""
from osgeo import gdal
from osgeo import osr
from osgeo import ogr
from numpy import full
from  geopandas import clip
import geopandas as gpd
from rasterio import open as open_rasterio, uint8
from rasterio.features import rasterize
from pandas import DataFrame

class spatial_toolset:
    def crop_vector(self,input_file: DataFrame, clipping_file: DataFrame,output_file:str)->None:
        """
        Crops the input vector file data to match the boundaries of the clipping_file
        Writes the cropped vector file

        Parameters
        ----------
        input_file : Dataframe
            The imported data (as a Dataframe) for the vector file to be cropped.
        clipping_file : Dataframe
            The imported data (as a Dataframe) for the vector file used to clip the input file.
            This file must have the boundary conditions wanted for the output cropped file
        output_file : string
            Name of the output file and location for the new shapefile.

        """
        points_clip =clip(input_file, clipping_file)

        points_clip.to_file(output_file)

    def crop_raster(self,cropped_file:str,input_file:str,boundary:list)->None:
        """
        Croppes the input file to fit within the boundary set. 
        Used only with raster files (tif)

        Parameters
        ----------
        cropped_file : string
            output file that is cropped.
        input_file : string
            input file to be cropped.
        boundary : list or array of length 4
            coordinates (EPSG2950) of the boundary for the cropped area (all 4 corners).

        """
        
        upper_left_x=boundary[0]
        lower_right_x=boundary[1]
        lower_right_y =boundary[2]
        upper_left_y=boundary[3]
        window = (upper_left_x,upper_left_y,lower_right_x,lower_right_y)
        gdal.Translate(cropped_file, input_file, projWin = window)
        
    def get_srs(self,dataset):
        """
        Get the spatial reference of any gdal.Dataset
        :param dataset: osgeo.gdal.Dataset (raster)
        :output: osr.SpatialReference
        """

        sr = osr.SpatialReference()
        sr.ImportFromEPSG(2950)
        # dataset.SetProjection(sr.ExportToWkt())
        # auto-detect epsg
        auto_detect = sr.AutoIdentifyEPSG()
        if auto_detect != 0:
            sr = sr.FindMatches()[0][0]  # Find matches returns list of tuple of SpatialReferences
            sr.AutoIdentifyEPSG()
        # assign input SpatialReference
        sr.ImportFromEPSG(int(sr.GetAuthorityCode(None)))
        return sr

    def rasterize_polygon(self,dsm:str,shp:str,out_raster_file_name:str,pixel_size:float)->None:
        """
        Rasterize the input shapefile (Vector to Ratser conversion)
        

        Parameters
        ----------
        dsm : string
            input dsm file of the same location (get the boundaries to match in both files).
        shp : string
            input shapefile name and file location to rasterize.
        out_raster_file_name : string
            name of the output file and location after converting to a tif file.

        pixel_size : float
            Resolution of the output raster file

        """
        source_ds = ogr.Open(shp)
        extent=open_rasterio(dsm)

        source_lyr = source_ds.GetLayer()
        rdtype=gdal.GDT_Int32
        no_data_value=-999
        # read extent
        x_min, y_min, x_max, y_max = extent.bounds

        # get x and y resolution
        x_res = int(round((x_max - x_min) / pixel_size,0))
        y_res = int(round((y_max - y_min) / pixel_size,0))

        # create destination data source (GeoTIff raster)
        target_ds = gdal.GetDriverByName('GTiff').Create(out_raster_file_name, x_res, y_res, 1, eType=rdtype)
        target_ds.SetGeoTransform((x_min, pixel_size, 0, y_max, 0, -pixel_size))
        band = target_ds.GetRasterBand(1)
        band.Fill(no_data_value)
        band.SetNoDataValue(no_data_value)
        field_name="FID"

        NullArr = full((y_res, x_res), no_data_value) 
        band.WriteArray(NullArr) 
        gdal.RasterizeLayer(target_ds, [1], source_lyr, None, None, burn_values=[0],
                            options=["ALL_TOUCHED=TRUE", "ATTRIBUTE=" + field_name])
        

        # release raster band
        band.FlushCache()

    def run_spatial_toolset(self,mosaic_path,shapefile_path,raster_shp_path,pixel_size):
        dsm=mosaic_path
        shp=shapefile_path
        out_raster_file_name=raster_shp_path
        
        self.rasterize_polygon(dsm,shp,out_raster_file_name,pixel_size)
        print("Done")