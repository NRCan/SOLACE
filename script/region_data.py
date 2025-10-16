import Lidar
import Segmentation
from pandas import Series

class location:
    """
    Contains location specific data inlcuding file locations for the different cities,
    latitude/longitude, timezone, etc.

    """
    def __init__(self,file_name:str='',mode:str='',scaling_option:bool=True,cap_coefficient_shade:list=[],elec_coefficient_shade:list=[],*args:any):
        self.cap_coefficient_shade=cap_coefficient_shade
        self.elec_coefficient_shade=elec_coefficient_shade   
        self.file_path='batch_inputs'
        self.mosaic=''
        self.raster_file=''
        self.shapefile=''
        if mode=='Technical':
            self.technical_potential(file_name,args)
        elif mode=='Market':
            self.market_potential(file_name,args)
        elif mode=='grid' and scaling_option:
            self.grid_scale(file_name,args)
        elif mode=='grid':
            self.grid(file_name,args)
        else:
            raise Exception("Not a valid mode of operation. Options include: Technical, Market, or grid")

    def technical_potential(self,file_name:str='',*args:any)->None:
        """
        Lists the inputs for a region. The variables included in this are the:
        Building footprint file, lidar files, raster (rasterized shapefile) and shapefiles,
        weather file, latitude, longitude, electricity cost for the the lifetime of the PV,
        the timezone (UTC offset), altitude, and unique name of the set of files for that region

        Parameters
        ----------
        file_name: str
            name of the file with the inputs for this mode of operation
        args: any
            only used if the user wants to use only one region. This is where the user will list the location of the region's datafiles and location specifications.
            order should be: 
                1. building footprint file location and name, (ex. r'Calgary\\building_footprint\\Calgary.shp')
                2. lidar data folder location, (ex. 'Calgary\\LAS files')
                3. the location to put the mosaic file and name of the file, (ex. 'Calgary\\Inputs\\mosaic_calgary.tif')
                4. the location to put the rasterized vector file and name of the file (ex. Calgary\\Inputs\\shape_calgary.tif)
                5. Location to generate the shapefile after segmentation (ex. Calgary\\Inputs\\shape_calgary.shp)
                6. location of the weather file in file format SAM CSV from NSRDB PSM3 weather files (ex. Calgary\\Inputs\\weather_calgary.csv)
                7. region's latitude (ex. 51.0447)
                8. region's longitude (ex. -114.0719)
                9. UTC offset as a string (ex. "-07:00")
                10. region's altitude (ex. 1045)
                11. file classifier, what region to add to each of the outputted files (ex. 'calgary')
        """
        if len(args[0])==0:
            try:
                with open(self.file_path+'\\Technical\\'+file_name+'.txt', 'r') as file:
                    lines = file.readlines()
                    self.bldg_footprint=lines[0].split('=')[1].replace('\n','').strip()
                    self.lidar=lines[1].split('=')[1].replace('\n','').strip()
                    self.weather_file=lines[2].split('=')[1].replace('\n','').strip()
                    self.latitude=float(lines[3].split('=')[1].replace('\n','').strip())
                    self.longitude=float(lines[4].split('=')[1].replace('\n','').strip())
                    self.UTC_offset=lines[5].split('=')[1].replace('\n','').strip()
                    self.altitude=float(lines[6].split('=')[1].replace('\n','').strip())
                    self.file_classifier=lines[7].split('=')[1].replace('\n','').strip()
            except FileNotFoundError:
                print(f"Error: The file '{file_name}' was not found.")
            except Exception as e:
                print(f"An error occurred: {e}")
        else:
            self.bldg_footprint=args[0]
            self.lidar=args[1]
            self.mosaic=args[2]
            self.raster_file=args[3]
            self.shapefile=args[4]
            self.weather_file=args[5]
            self.latitude=args[6]
            self.longitude=args[7]
            self.UTC_offset=args[8]
            self.altitude=args[9]
            self.file_classifier=args[10]
        
        offset_int = int(self.UTC_offset[:3])
        # Convert dtype to fixed offset instead of UTC
        if offset_int > 0:
            self.timezone = f"Etc/GMT{ int(-offset_int) }" 
        elif offset_int<0:
            self.timezone = f"Etc/GMT+{ int(-offset_int) }"
        else:
            self.timezone ="Etc/GMT"

        self.construct_files=Lidar.DSM_files()
    
    def market_potential(self,file_name:str='',*args: any) -> None:
        """
        Lists the inputs for a region. The variables included in this are the:
        Building footprint file, lidar files, raster (rasterized shapefile) and shapefiles,
        weather file, latitude, longitude, electricity cost for the the lifetime of the PV,
        the timezone (UTC offset), altitude, and unique name of the set of files for that region

        Parameters
        ----------
        file_name: str
            name of the file with the inputs for this mode of operation
        args: any
            only used if the user wants to use a region/ not listed in the file. This is where the user will list the location of the region's datafiles and location specifications.
            order should be: 
                1. Residential ground floor area in km2
                2. Commercial and institutional ground floor area in km2 
                3. Population weighted, mean daily insolation in kWh/m2 
                4. Historical capacity for the region in MW
        """            
            
        if len(args[0])==0:
            try:
                with open(self.file_path+'\\Market\\'+file_name+'.txt', 'r') as file:
                    lines = file.readlines()
                    self.ground_floor_res=float(lines[0].split('=')[1].replace('\n','').strip())
                    self.ground_floor_com=float(lines[1].split('=')[1].replace('\n','').strip())
                    self.daily_insolation=float(lines[2].split('=')[1].replace('\n','').strip())
                    self.historical_capacity=float(lines[3].split('=')[1].replace('\n','').strip())/1000
            except FileNotFoundError:
                print(f"Error: The file '{file_name}' was not found.")
            except Exception as e:
                print(f"An error occurred: {e}")
        else:
            self.ground_floor_res=args[0]
            self.ground_floor_com=args[1]
            self.daily_insolation=args[2]
            self.historical_capacity=args[3]/1000
            

    def grid_scale(self,file_name:str='',*args:any)->None:
        """
        Lists the inputs for a region. The variables included in this are the:
        Building footprint file, lidar files, raster (rasterized shapefile) and shapefiles,
        weather file, latitude, longitude, electricity cost for the the lifetime of the PV,
        the timezone (UTC offset), altitude, and unique name of the set of files for that region

        Parameters
        ----------
        file_name: str
            name of the file with the inputs for this mode of operation
        args: any
            only used if the user wants to use a region not listed in the file. This is where the user will list the location of the region's datafiles and location specifications.
            order should be: 
                1. building footprint file location and name, (ex. 'Calgary\\building_footprint\\Calgary.shp')
                2. lidar data folder location, (ex. 'Calgary\\LAS files')
                3. the location to put the mosaic file and name of the file, (ex. 'Calgary\\Inputs\\mosaic_calgary.tif')
                4. the location to put the rasterized vector file and name of the file (ex. 'Calgary\\Inputs\\shape_calgary.tif')
                5. Location to generate the shapefile after segmentation (ex. 'Calgary\\Inputs\\shape_calgary.shp')
                6. location of the weather file in file format SAM CSV from NSRDB PSM3 weather files (ex. 'Calgary\\Inputs\\weather_calgary.csv')
                7. region's latitude (ex. 51.0447)
                8. region's longitude (ex. -114.0719)
                9. UTC offset as a string (ex. "-07:00")
                10. region's altitude (ex. 1045)
                11. file classifier, what region to add to each of the outputted files (ex. 'calgary')
                12. Historical capacity for the region in MW
                13. Population weighted, mean daily insolation in kWh/m2 
                14. Residential ground floor area in km2
                15. Commercial and institutional ground floor area in km2 

        """

        if len(args[0])==0:
            try:
                with open(self.file_path+'\\Grid_scale\\'+file_name+'.txt', 'r') as file:
                    lines = file.readlines()
                    self.bldg_footprint=lines[0].split('=')[1].replace('\n','').strip()
                    self.lidar=lines[1].split('=')[1].replace('\n','').strip()
                    self.weather_file=lines[2].split('=')[1].replace('\n','').strip()
                    self.latitude=float(lines[3].split('=')[1].replace('\n','').strip())
                    self.longitude=float(lines[4].split('=')[1].replace('\n','').strip())
                    self.UTC_offset=lines[5].split('=')[1].replace('\n','').strip()
                    self.altitude=float(lines[6].split('=')[1].replace('\n','').strip())
                    self.file_classifier=lines[7].split('=')[1].replace('\n','').strip()
                    self.daily_insolation=float(lines[9].split('=')[1].replace('\n','').strip())
                    self.historical_capacity=float(lines[8].split('=')[1].replace('\n','').strip())/1000
                    self.ground_floor_res=float(lines[10].split('=')[1].replace('\n','').strip())
                    self.ground_floor_com=float(lines[11].split('=')[1].replace('\n','').strip())
            except FileNotFoundError:
                print(f"Error: The file '{file_name}' was not found.")
            except Exception as e:
                print(f"An error occurred: {e}")
        else:
            self.bldg_footprint=args[0]
            self.lidar=args[1]
            self.mosaic=args[2]
            self.raster_file=args[3]
            self.shapefile=args[4]
            self.weather_file=args[5]
            self.latitude=args[6]
            self.longitude=args[7]
            
            self.UTC_offset=args[8]
            self.altitude=args[9]
            self.file_classifier=args[10]
            self.ground_floor_res=args[13]
            self.ground_floor_com=args[14]
            self.daily_insolation=args[12]   
            self.historical_capacity=args[11]

        offset_int = int(self.UTC_offset[:3])
        # Convert dtype to fixed offset instead of UTC
        if offset_int > 0:
            self.timezone = f"Etc/GMT{ int(-offset_int) }" 
        elif offset_int<0:
            self.timezone = f"Etc/GMT+{ int(-offset_int) }"
        else:
            self.timezone ="Etc/GMT"
        self.construct_files=Lidar.DSM_files()
    
    def grid(self,file_name:str='',*args:any)->None:
        """
        Lists the inputs for a region. The variables included in this are the:
        Building footprint file, lidar files, raster (rasterized shapefile) and shapefiles,
        weather file, latitude, longitude, electricity cost for the the lifetime of the PV,
        the timezone (UTC offset), altitude, and unique name of the set of files for that region

        Parameters
        ----------
        file_name: str
            name of the file with the inputs for this mode of operation
        args: any
            only used if the user wants to use a region not listed in the file. This is where the user will list the location of the region's datafiles and location specifications.
            order should be: 
                1. building footprint file location and name, (ex. 'Calgary\\building_footprint\\Calgary.shp')
                2. lidar data folder location, (ex. 'Calgary\\LAS files')
                3. the location to put the mosaic file and name of the file, (ex. 'Calgary\\Inputs\\mosaic_calgary.tif')
                4. the location to put the rasterized vector file and name of the file (ex. 'Calgary\\Inputs\\shape_calgary.tif')
                5. Location to generate the shapefile after segmentation (ex. 'Calgary\\Inputs\\shape_calgary.shp')
                6. location of the weather file in file format SAM CSV from NSRDB PSM3 weather files (ex. 'Calgary\\Inputs\\weather_calgary.csv')
                7. region's latitude (ex. 51.0447)
                8. region's longitude (ex. -114.0719)
                9. UTC offset as a string (ex. "-07:00")
                10. region's altitude (ex. 1045)
                11. file classifier, what region to add to each of the outputted files (ex. 'calgary')
                12. Historical capacity for the region in MW
                13. Population weighted, mean daily insolation in kWh/m2 
                14. Ratio of the residential buildings within the region

        """
        if len(args[0])==0:
            try:
                with open(self.file_path+'\\Grid\\'+file_name+'.txt', 'r') as file:
                    lines = file.readlines()
                    self.bldg_footprint=lines[0].split('=')[1].replace('\n','').strip()
                    self.lidar=lines[1].split('=')[1].replace('\n','').strip()
                    self.weather_file=lines[2].split('=')[1].replace('\n','').strip()
                    self.latitude=float(lines[3].split('=')[1].replace('\n','').strip())
                    self.longitude=float(lines[4].split('=')[1].replace('\n','').strip())
                    self.UTC_offset=lines[5].split('=')[1].replace('\n','').strip()
                    self.altitude=float(lines[6].split('=')[1].replace('\n','').strip())
                    self.file_classifier=lines[7].split('=')[1].replace('\n','').strip()
                    self.daily_insolation=float(lines[9].split('=')[1].replace('\n','').strip())
                    self.historical_capacity=float(lines[8].split('=')[1].replace('\n','').strip())/1000
                    self.division_res_bldgs=float(lines[10].split('=')[1].replace('\n','').strip())

            except FileNotFoundError:
                print(f"Error: The file '{file_name}' was not found.")
            except Exception as e:
                print(f"An error occurred: {e}")
        else:
            self.bldg_footprint=args[0]
            self.lidar=args[1]
            self.mosaic=args[2]
            self.raster_file=args[3]
            self.shapefile=args[4]
            self.weather_file=args[5]
            self.latitude=args[6]
            self.longitude=args[7]
            
            self.UTC_offset=args[8]
            self.altitude=args[9]
            self.file_classifier=args[10]
            self.division_res_bldgs=args[13]
            self.daily_insolation=args[12]   
            self.historical_capacity=args[11]
        
        offset_int = int(self.UTC_offset[:3])
        # Convert dtype to fixed offset instead of UTC
        if offset_int > 0:
            self.timezone = f"Etc/GMT{ int(-offset_int) }" 
        elif offset_int<0:
            self.timezone = f"Etc/GMT+{ int(-offset_int) }"
        else:
            self.timezone ="Etc/GMT"
        self.construct_files=Lidar.DSM_files()

    def run_lidar(self,resolution: float|int=1,onefile:bool=False,file=None,out=None)->None:
        """
        Function used to create the digital surface models (DSM) files from las files
        either from only one file or all files within a folder.

        Parameters
        ----------
        resolution : float or int
            Resolution of the output DSM files
        onefile: bool
            Check if only one file is needed to be converted. Default is False.
        file: string
            file location for the output DSM files. File location is required if onefile is True or if the
            required folder is not the same as definied for the location.
        """
        
        if onefile:
            self.construct_files.DSM_one(file,resolution,out)
        else:
            file = self.lidar
            self.construct_files.DSM(file,resolution)
            
    def run_seg(self,onefile:bool=False,input_file:bool=False)->None:
            """
            
            Function used to create the rooftop segmentation files for either a folder of .tif files or
            only one file

            Parameters
            ----------

            onefile: bool
                Check if only one file is needed to be converted. Default is False.
            input_file: string
                file location for the output files. File location is required if onefile is True or if the
                required folder is not the same as definied for the location.
            """
            bldg_footprint=self.bldg_footprint
            shapefile=self.shapefile
            if onefile:
                Segmentation.one_tile(input_file,bldg_footprint,shapefile)
            else:
                directory= self.lidar
                Segmentation.all_tiles(directory,bldg_footprint,shapefile)

    def run_mosaic(self)->None:
        """
        Combines all raster files (.tif) into one file, creating a "mosaic" file of the different tiles.
        """
        directory= self.lidar
        output_file=self.mosaic
        self.construct_files.mosaic(directory,output_file)
    
    def run_lidar_thin(self,resolution_thin:float|int=1/5)->None:
        """
        Reduce the resolution of the lidar files (.las) within a grid pattern.
        """
        self.construct_files.modify_lidar_density(resolution_thin,self.lidar)
        # file=''.join([self.lidar,'/Point_Cloud_Density'])
        # self.construct_files.DSM(file,resolution)
    
    def rooftop_capacity(self,eff:list,building_type:str)->None:
        """
        This function calculates the intial rooftop capacity (technical potential)
        
        Parameters
        ----------
        eff: list
            list of the module efficiencies by year
        building_type:str
            type of building, residential or commercial in GW
        
        """
        if building_type=='res' or building_type=='residential':
            self.cap_res=[self.cap_coefficient_shade[0]*self.ground_floor_res*eff[i] for i in range(0,len(eff))]
        elif building_type=='com' or building_type=='commercial':
            self.cap_com=[self.cap_coefficient_shade[0]*self.ground_floor_com*eff[i] for i in range(0,len(eff))]

    def rooftop_generation(self,PR:list,building_type:str)->None:
        """
        This function calculates the intial rooftop generation (technical potential)

        Parameters
        ----------
        PR: list
            list of the performance ratios by year based on the efficiency
        building_type:str
            type of building, residential or commercial
        
        """
        if building_type=='res' or building_type=='residential':
            self.elec_res=[self.cap_res[i]*PR[i]*self.daily_insolation*1000*self.elec_coefficient_shade[0]*365 for i in range(0,len(self.cap_res))]
        elif building_type=='com' or building_type=='commercial':
            self.elec_com=[self.cap_com[i]*PR[i]*self.daily_insolation*1000*self.elec_coefficient_shade[0]*365 for i in range(0,len(self.cap_res))]

    def set_capacity(self,capacity:list|Series)->None:
        """
        This function divides the intial rooftop capacity (technical potential) into residential and commercial building types,
        using the results from the detailed analysis with lidar data and the inputted ratio of residential buildings
        
        Parameters
        ----------
        capacity: list|Series
            total capacity
        
        """
        self.cap_res=capacity*self.division_res_bldgs
        self.cap_com=capacity*(1-self.division_res_bldgs)

    def set_electricity(self,electricity:list|Series)->None:
        """
        This function divides the intial rooftop capacity (technical potential) into residential and commercial building types,
        using the results from the detailed analysis with lidar data and the inputted ratio of residential buildings
        
        Parameters
        ----------
        electricity: list|Series
            total electricity
        
        """
        self.elec_res=electricity*self.division_res_bldgs
        self.elec_com=electricity*(1-self.division_res_bldgs)
        