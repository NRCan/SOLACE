
####################################################
#Provide user input here
####################################################

ground_floor_res=1000 #km2
ground_floor_com=800 #km2

cap_coefficient_shade=[0.811]
# cap_coefficient_shade=[0.811057181818182,0.810270545454545,0.806866454545455,0.795339909090909,
                                # 0.766200545454546,0.704058090909091,0.585788818181818,0.444060636363636,
                                # 0.280134272727273,0.0521188181818182] # Canada average by resource bin
elec_coefficient_shade=[0.697]
# elec_coefficient_shade=[0.696808455,0.697416909,0.699658909,0.706008364,0.719245636,0.742224909,
                                #     0.779868909,0.821071909,0.861555455,0.923374000]# Canada average by resource bin 

daily_insolation=3.5 #kWh/m2

file_location=r'C:\Users\user_name\Documents' #indicate that this is a pre-existing folder where outputs will be stored

#PV specifications
performance_ratio=0.75
module_efficiency=0.225

####################################################
cap_res=sum([cap_coefficient_shade[i]*ground_floor_res*module_efficiency*1000 for i in range(0,len(cap_coefficient_shade))])
cap_com=sum([cap_coefficient_shade[i]*ground_floor_com*module_efficiency*1000 for i in range(0,len(cap_coefficient_shade))])

elec_res=sum([cap_res*performance_ratio*daily_insolation*365/1000*elec_coefficient_shade[i] for i in range(0,len(elec_coefficient_shade))])
elec_com=sum([cap_com*performance_ratio*daily_insolation*365/1000*elec_coefficient_shade[i] for i in range(0,len(elec_coefficient_shade))])

with open(file_location+r'\output_tech_coeff.txt','w') as file:
        file.write('Residential rooftop PV capacity (MW):\t'+str(round(cap_res,2))+'\n')
        file.write('Residential rooftop PV energy (GWh):\t'+str(round(elec_res,2))+'\n')
        file.write('Commercial and institutional rooftop PV capacity (MW):\t'+str(round(cap_com,2))+'\n')
        file.write('Commercial and institutional rooftop PV energy (GWh):\t'+str(round(elec_com,2))+'\n')
        file.write('Total rooftop PV capacity (MW):\t'+str(round(cap_com+cap_res,2))+'\n')
        file.write('Total rooftop PV energy (GWh):\t'+str(round(elec_com+elec_res,2))+'\n')
