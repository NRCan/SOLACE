# -*- coding: utf-8 -*-
"""
Created on Fri Apr 16 14:20:54 2021

@author: nsalimza  and egaucher
"""

def all_tiles(directory:str,bldg_footprint:str,shapefile:str)->None:
    """
    Thsi function outputs a complete segmentation file using all lidar files
    within the input directory using a set thresdhold and normal difference
    value. The function outputs a shapefile.

    Parameters
    ----------
    name : string
        beginning of the name of the new shapefile.
    directory : string
        the directory with all the input lidar files to segment.
    shapefile: str
        the location of the segmentation file output with file extension .tif

    """
    from WBT.whitebox_tools import WhiteboxTools
    wbt = WhiteboxTools()
    wbt.set_verbose_mode(False)
    #Rooftop Analysis
    #-i, --input	Input LiDAR file
    #--buildings	Input vector build footprint polygons file
    #-o, --output	Output vector polygon file
    #--radius	Search Radius
    #--num_iter	Number of iterations
    #--num_samples	Number of sample points on which to build the model
    #--threshold	Threshold used to determine inlier points (in elevation units)
    #--model_size	Acceptable model size, in points
    #--max_slope	Maximum planar slope, in degrees
    #--norm_diff	Maximum difference in normal vectors, in degrees
    #--azimuth	Illumination source azimuth, in degrees
    #--altitude	Illumination source altitude in degrees

    wbt.set_working_dir (directory)
    
    thresh=0.4
    normdi=5
    wbt.lidar_rooftop_analysis(
        bldg_footprint,
        shapefile,
        
        
        radius=2.0, 
        num_iter=50, 
        num_samples=10, 
        threshold=thresh, 
        model_size=15, 
        max_slope=60.0, 
        norm_diff=normdi, 
        azimuth=180.0, 
        altitude=30.0)

def one_tile(input_file:str,bldg_footprint:str,shapefile:str)->None:
    """
    Thsi function outputs a complete segmentation file using one lidar file
    (defined by the user) using a set thresdhold and normal difference
    value. The function outputs a shapefile.

    Parameters
    ----------
    name_indicator : string
        beginning of the name of the new shapefile.
    input_file : string
        input filename and location.
    shapefile: str
        the location of the segmentation file output with file extension .tif

    """
    from WBT.whitebox_tools import WhiteboxTools
    wbt = WhiteboxTools()
    wbt.set_verbose_mode(False)
    #Rooftop Analysis
    #-i, --input	Input LiDAR file
    #--buildings	Input vector build footprint polygons file
    #-o, --output	Output vector polygon file
    #--radius	Search Radius
    #--num_iter	Number of iterations
    #--num_samples	Number of sample points on which to build the model
    #--threshold	Threshold used to determine inlier points (in elevation units)
    #--model_size	Acceptable model size, in points
    #--max_slope	Maximum planar slope, in degrees
    #--norm_diff	Maximum difference in normal vectors, in degrees
    #--azimuth	Illumination source azimuth, in degrees
    #--altitude	Illumination source altitude in degrees
    
    thresh=0.4
    normdi =5
    wbt.lidar_rooftop_analysis(
        bldg_footprint,
        shapefile,
        input_file,
        
        radius=2.0, 
        num_iter=50, 
        num_samples=10, 
        threshold=thresh, 
        model_size=15, 
        max_slope=60.0, 
        norm_diff=normdi, 
        azimuth=180.0, 
        altitude=30.0)