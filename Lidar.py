# -*- coding: utf-8 -*-
"""
Created on Mon Jan 25 12:52:14 2021

@author: nsalimza and egaucher
"""
import glob
from WBT.whitebox_tools import WhiteboxTools
class DSM_files:
    def __init__(self)->None:
        self.wbt = WhiteboxTools()
        self.wbt.set_verbose_mode(False)
        
    def DSM(self,file:str,resolution:float|int)->None:
        """
        This function creates a digital surface model (DSM) 
        from the input .las and .laz files (LiDAR files)

        Parameters
        ----------
        file : string
            input file directory path.
        resolution : int
            the resolution required for creating the DSM.

        """
        
        
        # Digital surface model
        #-i, --input	Input LiDAR file (including extension)
        #-o, --output	Output raster file (including extension)
        #--resolution	Output raster's grid resolution
        #--radius	Search Radius
        #--minz	Optional minimum elevation for inclusion in interpolation
        #--maxz	Optional maximum elevation for inclusion in interpolation
        #--max_triangle_edge_length	Optional maximum triangle edge length; triangles larger than this size will not be gridded
        
        
        self.wbt.set_working_dir (file)
        
        self.wbt.lidar_digital_surface_model(
            i= None, 
            output= None,
            resolution=resolution, 
            radius=0.5, 
            minz=None, 
            maxz=None, 
            max_triangle_edge_length=None, 
            #callback=default_callback
        )
        
    def DSM_one(self,file:str,resolution:float|int,output_file:str)->None:
        """
        This function creates a digital surface model (DSM) 
        from the input .las and .laz files (LiDAR files)

        Parameters
        ----------
        file : string
            input lidar filename and path (.las file)
        resolution : int
            the resolution required for creating the DSM.
        output_file : string
            the output filename and path for the tif file

        """
        
        # Digital surface model
        #-i, --input	Input LiDAR file (including extension)
        #-o, --output	Output raster file (including extension)
        #--resolution	Output raster's grid resolution
        #--radius	Search Radius
        #--minz	Optional minimum elevation for inclusion in interpolation
        #--maxz	Optional maximum elevation for inclusion in interpolation
        #--max_triangle_edge_length	Optional maximum triangle edge length; triangles larger than this size will not be gridded

        
        self.wbt.lidar_digital_surface_model(
            i= file, 
            output= output_file,
            resolution=resolution, 
            radius=0.5, 
            minz=None, 
            maxz=None, 
            max_triangle_edge_length=None, 
            #callback=default_callback
        )
        
    def modify_lidar_density(self,resolution:float|int,directory:str)->None:
        """
        This function artifically thins the point cloud density of the input 
        lidar files from a set folder. The new resolution of the output files
        is based on the user inputted resolution parameter.

        Parameters
        ----------
        resolution : int or float
            the resolution of the desired output lidar files. 

        """

        # LidarThin
        # Thins a LiDAR point cloud, reducing point density.
        # NOTES: This tool thins a LiDAR point cloud such that no more than one point exists within each grid cell of a
        # superimposed grid of a user-specified resolution. When a cell contains more than one point in the input
        # data set, the remaining point can be selected as the lowest, highest, first, last, or nearest the centre.
        # This tools provides similar functionality to the ESRI Thin LAS (2D) and LasTools lasthin tools. If there is
        # high variability in point density, consider using the LidarThinHighDesnity tool instead.
        
        #-i, --input	Input LiDAR file (including extension)
        #-o, --output	Output raster file (including extension)
        #--resolution	Output raster's grid resolution. The size of the square area used to evaluate nearby points in the LiDAR data
        #--method      Point selection method; options are 'first', 'last', 'lowest' (default), 'highest', 'nearest'
        #--save_filtered Save filtered points to separate file?
        name='_res'+str(int(1/resolution))+'.las'
        # wbt.set_working_dir (r'\\w-var-a106532\D\scidata\REN1\Varennes_PV_potential_buildings\LiDAR_and_DSM_Varennes\Point_Cloud_Density')
        for file in glob.glob(directory+'/*.las',recursive=True):
            d=file.split('\\')[-1].split('.')[0]
            self.wbt.lidar_thin(
                file,
                ''.join([directory,'/Point_Cloud_Density/',d,name]),
                resolution=resolution, 
                method="highest", #nearest
            )
    def mosaic(self,directory: str, output_file: str) -> None:
        """
        Merge all tif files into one file.

        Parameters
        ----------
        directory : string
            the directory with all the input DSM files to merge.
        shapefile: str
            the location of the mosaic file output with file extension .tif
        """
        
        #Mosaic
        #-i, --inputs	Input raster files
        #-o, --output	Output raster file
        #--method	Resampling method; options include 'nn' (nearest neighbour), 'bilinear', and 'cc' (cubic convolution)
        
        self.wbt.set_working_dir(directory)
        self.wbt.mosaic(
            output_file, 
            inputs=None, 
            method="nn", 
        )