from nornir import InitNornir  # importing the nornir  automation framework
from nornir_utils.plugins.functions import print_result , print_title # importing the print_result function 
from nornir_netmiko.tasks import netmiko_send_config , netmiko_send_command# importing the netmiko functions 
from nornir_jinja2.plugins.tasks import template_file # importing the jinja2 template file for creating configs
from nornir.core.filter import F # nornir filtering options 
from nornir.core.exceptions import NornirExecutionError#importing exception handling 
import json 
import yaml 
import requests
from requests import ConnectionError #Restconf exception handling
from termcolor import colored
import schedule
import threading
import os 
import time
import subprocess

from netmiko import ConnectHandler
requests.packages.urllib3.disable_warnings()


with open ("hosts.yaml", "r") as f: 
    Devices = yaml.load(f, Loader=yaml.FullLoader)


from nornir import InitNornir # initializing Nornir 
nornir = InitNornir(
        config_file="config.yaml", dry_run=True, core={"raise_on_error": True})#Setting the config file



headers = {'Content-Type': 'application/yang-data+json', #Defining the headers 
           'Accept': 'application/yang-data+json'}


def Underlay_Monitor(): #Funcţie pentru monitorizarea OSPF
    
    
    global err_list #list containing erros 
    err_list  = []
    global ospf_lst 
    ospf_lst = []
    error_handling = []
    ospf_router_ok=[]
    ospf_router_error =[]
    global ospf_int_dict
    ospf_int_dict ={}

    try:
      
        core_routers = nornir.filter(F(groups__contains="core_group")) #Filtrare device-uri folosind nornir
    #print(core_routers.inventory.hosts.keys())
    
        results = core_routers.run(netmiko_send_command, 
                                   command_string="show ip ospf neigh" ,
                                   use_textfsm=True)#trimiterea comenzii 
                                                    #către ruterele selectate 
                                                    #şi parsarea folosind textfsm
        results.raise_on_error()
        

        R = 0
        
        for key in results.keys(): #buclă for pentru fiecare cheie din rezultatul executării comenzii
            R = R +1 # Counter pentru numărul de rutere
            response = results[key].result#stocarea răspunsului de la fiecare ruter  
            print('Router'+str(R)+':')
            print(response)
            
        #print(type(response[0]))
        #print(len(response))
            print(colored('Checking OSPF on Router ' + str(R),'green') )
            nr_of_neigh = len(response)#Numărul vecinilor OSPF 
            counter_neigh = 0 
            for x in range(0,nr_of_neigh):#Loop pentru fiecare vecin 
                
                counter_neigh = counter_neigh +1 #counter pentru numărul de adiacenţe OSPF
                OSPF_STATE = response[x].get('state') #Starea fiecărei adiacenţe
                if nr_of_neigh != 3:#Verificare condiţie nr de adiacenţe
                    missing_neigh = 3 - nr_of_neigh#Numărul de adiacenţe care lipsesc
                    global one
                    one = 'Router'+str(R) + ' is missing ' + str(missing_neigh) + ' Neighbor'
                    err_list.append(one)#Adăugarea în lista cu erori a fiecărei adiacenţe care lipseşte
                    ospf_router_error.append('R'+str(R))

                    
                    break


                elif OSPF_STATE != 'FULL/  -':#Condiţie, verificarea stării FULL OSPF
                    
                    two = 'Router' + str(R) + ' Alert! the router is not in the FULL State with ' +response[x]['neighbor_id'] +' The state is ' + OSPF_STATE #Rutere care nu sunt in starea FULL
                    err_list.append(two)#Adăugarea ruterelor în lista de erori OSPF
                    ospf_router_error.append('R'+str(R))
                    if OSPF_STATE == 'FULL/BDR':#Verificarea stării FULL/BDR(toate link-urile sunt p2p)
                        three = 'Probabily there is an ospf network type missmatch....'
                        err_list.append(three)#Adăugarea mesajului in lista cu erori
                        ospf_router_error.append('R'+str(R))
                    elif OSPF_STATE == 'EXSTART/  -':#Verificarea rutelelor blocate în starea Exstart
                        four = 'Probabily there is an ospf mtu missmatch....'
                        err_list.append(four)#Adăugarea lor la lista cu erori
                        ospf_router_error.append('R'+str(R))
                    
                    elif OSPF_STATE == 'EXCHANGE/  -':# Verificarea rutelelor blocate în starea Exchange
                        five = 'Probabily there is an ospf mtu missmatch....'
                        err_list.append(five)#Adăugarea lor la lista cu erori
                        ospf_router_error.append('R'+str(R))
                    ospf_router_ok = ['R1','R2','R3','R4','R5','R6'] - ospf_router_error

    except NornirExecutionError:#Afişarea de eroare în cazul în care ruterele nu pot fi accesate
        print('cant ping')
        error_handling.append('Oops!  , some device failed...')#Adăugarea lor la lista cu erori
        for ip in range(1,6):#Găsirea echipamentelor care nu pot fi accesate
            target = '1.1.1.'+str(ip)
            response =os.system("ping -c1 "+ target+ "> /dev/null")
            if response != 0: 
                error_handling.append('Critical!!! Device with ip  '+ target + ' does not respond')#Afişarea ruterelor care nu pot fi accesate
                error_handling.append('Device management is down , fix this issue...')       
            
    if len(error_handling)==0 and len(err_list)==0:#Dacă listele de eroare sunt goale, OSPF funcţionează corect!
        
        ospf_lst.append('OSPF was monitored! Everything is great! :')#Mesaj informativ OSPF
      
        
        print(ospf_router_ok)
    else:
        print(err_list)
    nornir.close_connections() #Închiderea conexiunilor       
    return ospf_lst , err_list ,error_handling , ospf_router_error, ospf_router_ok , ospf_int_dict #Return 

#Underlay_Monitor()


def fix_ospf(): #Fucţie care repară erorile OSPF 
    fix_errors = []#lista care salveaza erorile 
    
    ospf = Underlay_Monitor()#Variabila care salveaza rezultatele functiei Underlay_Monitor
    if len(ospf[2])!=0:#Conditie pentru verificarea erorilor
        fix_errors.append('Cannot fix ospf, some devices are down!')
        return fix_errors
    else: #Daca sunt identificate erori se executa codul urmator


        try:#bloc try 

            
            if len(err_list) !=0: #Daca lista de erori nu este goala 
                
                for each in err_list: #Verificarea fiecarui element din lista 
                    router = each.split()[0] #Stocare nume ruter care prezinta erori 
                    print(router)
                    for index in range(1,7):#Verificarea fiecarui ruter in parte
                        
                        if router=='Router'+str(index):#Conditie pentru selectarea ruterelor care au erori  
                            ssh_fix=nornir.filter(id='iou'+str(index))#Filtrare nornir catre dispozitivele cu erori 
                            rez = ssh_fix.run(netmiko_send_command,command_string="show ip ospf interface brief",use_textfsm=True)#Trimitere comanda verificare
                            
                            response = rez['R'+str(index)].result#Stocarea rezultatelor
                            #print(response)#printing the parsed output 
                           
                            
                            adv_ospf = ssh_fix.run(netmiko_send_command,command_string="show ip ospf neigh",use_textfsm=True)
                            resp_adv  =adv_ospf['R'+str(index)].result
                            print(resp_adv)
                            print(len(response))
                            int_missed = [] # lista cu interfete 
                            for nr in range(0,len(response)):
                                #print(response[nr]['interface'])
                                int_missed.append(response[nr]['interface'])
                               
                                
                                if response[nr]['state'] == 'DOWN':#Verificarea starii interfetelor 
                                    int_affected = response[nr]['interface']#stocarea rezultatului 
                                    cmd = ['interface ' + int_affected , ' no shutdown' ]#comanda pentru rezolvarea problemelor
                                    fix = ssh_fix.run(netmiko_send_config, config_commands=cmd)
                                    #print_result(fix)
                                    fix_errors.append('OSPF Fixed! identified problem:' + 'Router R'+str(index) +' Interface '+int_affected +' was shut down ' ) 
                                    time.sleep(7)
                                elif response[nr]['area']!='0': # verificarea ariei OSPF
                                    # Rezolvarea problemelor legate de arie 
                                    int_affected=response[nr]['interface'] 
                                    cmd = ['interface '+ int_affected,'ip ospf 1 area 0']
                                    fix=ssh_fix.run(netmiko_send_config, config_commands=cmd)
                                    #print_result(fix)
                                    fix_errors.append('OSPF Fixed! identified problem:' + 'Router R'+str(index) +' Interface '+int_affected + ' was in a wrong area') 
                                    time.sleep(7)
                                elif response[nr]['state']!= 'FULL/  -':
                                    # Rezolvarea erorilor aditionale OSPF 
                                    int_affected = response[nr]['interface']
                                    print(int_affected)
                                    cmds = ['interface '+int_affected ,'ip ospf 1 area 0', 'ip ospf hello-interval 10' , 'ip ospf network point-to-point ' , 'no ip mtu ', 'clear ip ospf proc', 'yes']
                                    fix=ssh_fix.run(netmiko_send_config,config_commands=cmds)
                                    #fix_errors=err_list
                                    Router = 'Router R'+str(index)
                                    print(Router)
                                   
                                    time.sleep(3) 
                            fix_errors.append('Controller detected multiple OSPF issues on router' + str(index) + ' and fixed all of them! Check OSPF again!') 
                            print(int_missed)
                            print(ospf[5])


        #Bloc except 
        except NornirExecutionError: 
            print('Execution errors , some device did not respond')
            fix_errors.append('Execution Error!!')
            
        if len(err_list)==0:
            fix_errors.append('There are no problems ')



        nornir.close_connections()
        return fix_errors

#fix_ospf()

def BGP_Configuration():#Fucţie care configurează BGP
    
    rezultat = [] #Lista pentru salvarea mesajelor valide BGP
    error = []#Listă pentru stocarea mesajelor de eroare
    try:



        def config(task):# definirea funcţiei de configurare cu parametrul task
            r = task.run(task=template_file,   #Definirea task-ului 
                        name="BGP configuration",#numele task-ului
                        template="bgp_peerings.j2",#Template-ul jinja2 pentru config
                        path=f"Jinja2/{task.host['protocol']}")#calea către template

                    
            

            task.host["config"] =r.result.splitlines() #Iniţiarea task-ului pt host-uri

            
            task.run(task=netmiko_send_config, # definirea task-ului
                    name = "BGP peerings  configuration", #numele task-ului
                    config_commands=task.host["config"])#Comenzile trimise 

        nornir.data.dry_run = False
        print_title("Performing some cool network automation !!!")

            
        result = nornir.run(task=config)#Salvarea rezultatelor
        print_result(result)
        
        rezultat.append('BGP configartion was succesful')#salvarea mesajului in listă

        
    except:  # Excepţii care pot apărea
        NornirExecutionError
 
        error.append('Cannot execute this , some device failed...')
        for ip in range(1,6):# Descoperirea ruterelor care sunt down
            target = '1.1.1.'+str(ip)
            response =os.system("ping -c1 "+ target+ "> /dev/null")
            if response != 0: 
                error.append('Failed '+ target)
                error.append('Fix connection to this devices and try again ')
    nornir.close_connections()#inchiderea conexiunilor
    return rezultat ,error # Returnarea celor 2 liste
 
#BGP_Configuration()

def Monitor_BGP_Peerings_Core():#Funcţie care monitorizează sesiunile iBGP
    alert = [] # Listă pentru mesaje de alertă
    up_peers = []#Listă pentru stocarea vecinilor BGP
  
    core_routers = nornir.filter(F(id="iou1")) #Filtrare nornir 
    result = core_routers.run(netmiko_send_command,command_string="show bgp summ" , use_textfsm=True)#stocarea rezultatului în variabila result
    rr_routers = nornir.filter(F(role="RR"))
    rr_result = rr_routers.run(netmiko_send_command,command_string="show ip bgp summ", use_textfsm=True)
    neigh = []

    

     
                 
    for key in result.keys():
        
        response = result[key].result
        new = response.strip()
    
        if new == '% BGP not active':
            
            no_active = 'BGP is not active'
            alert.insert(0,no_active)


            
        else:
            for key in rr_result.keys():
                response = rr_result[key].result
             
        
                for each in response:
                    print(each)
                    if each['router_id']=='1.1.1.5':
                        print(each) 
                        neigh.append('csr5')
                    elif each['router_id']=='1.1.1.6':
                        print(each)
                        neigh.append('csr6')

            print(neigh)
            if neigh.count('csr5')!=5:
                
                alert.append(' Device with ID 5 (CSR5) is missing ' + str(5-neigh.count('csr5')) + ' neighbors')
                print(' Device with ID 5 (CSR5) is missing ' + str(5-neigh.count('csr5')) + ' neighbors')
            if neigh.count('csr6')!=5:
                alert.append(' Device with ID 6 (CSR6) is missing ' + str(5-neigh.count('csr6')) + ' neighbors')

            
            #print(colored('*if no alerts are diplayed it means that all peers are up !','blue'))           
            for ip in range (5,7):  # Selecting the Core devices based on their IP address 

                url_CSR_RR = "https://"+ str(Devices['R'+str(ip)]['hostname'])+":443/restconf/data/Cisco-IOS-XE-bgp-oper:bgp-state-data/neighbors/neighbor" # Connecting using restconf to devices

                try:
                    response = requests.get(url_CSR_RR, auth = (Devices['R'+str(ip)]['username'],Devices['R'+str(ip)]['password']),headers=headers,verify=False)#storing the response  of Get operation
                except requests.ConnectionError:
                    err = 'Unable to connect to address https://1.1.1.'+str(ip)
                    alert.append(err)
                    print(alert)
                if response.status_code != 200:# checking the response codes 
                    alert.append('Login request failed. Status code is {}'.format(response.status_code))
                else:        
                    up_peers.append('Rest API communication with Router'+str(ip) + ' was sucessful status code is '+str(response.status_code) + ' OK!')

                bgp_data =response.json() # Storing the respinse and display it in a json data format 
         
                if ip == 5: #Selecting the first device 
                    for index in bgp_data['Cisco-IOS-XE-bgp-oper:neighbor']: #checking the peering status 
                        CSR5_peers = index['neighbor-id']
                        Csr5_state = index['connection']['state']
                        notif_sent = index['bgp-neighbor-counters']['sent']['notifications']
                        notif_rec  = index['bgp-neighbor-counters']['received']['notifications']
                        connection_fail = index['connection']['reset-reason']
                        report = 'Router CSR5 is peering with ' +CSR5_peers + ' and the state is '+ Csr5_state # Checking to see if the peers are UP !! 
                        
                        if not 'established' in report: # If not an allert will pop up 
                            alert1='CSR5 ALERT!: '+' peer ' +  CSR5_peers + ' is DOWN and the status code is ' + Csr5_state + '\n' + 'the reason of failure is '+ connection_fail 
                            alert.append(alert1)
                        else:
                            peers = 'CSR5 is peering with ' + CSR5_peers + ' for about ' + index['up-time'] + ' h/m/s'
                            up_peers.append(peers)
                        if notif_sent != 0 : 
                            notif1 = 'This device has sent ' + str(notif_sent) + ' notifications , please investigate furhter...'
                            alert.append(notif1)
                        elif notif_rec != 0: 
                            notif2 = 'This device has received ' + str(notif_rec) +' notifications , please investigate furhter'
                            alert.append(notif2)
                            
                if ip == 6: #doing the same thing for our second core device 
                    for index in bgp_data['Cisco-IOS-XE-bgp-oper:neighbor']:
                        CSR6_peers = index['neighbor-id']
                        Csr6_state = index['connection']['state']
                        notif_sent = index['bgp-neighbor-counters']['sent']['notifications']
                        notif_rec  = index['bgp-neighbor-counters']['received']['notifications']
                        connection_fail = index['connection']['reset-reason']
                        #peers_csr5 = bgp_data['Cisco-IOS-XE-bgp-oper:neighbor'][index]['neighbor-id']               
                        report = 'Router CSR6 is peering with ' +CSR6_peers + ' and the state is '+ Csr6_state
                        if not 'established' in report: 
                            alert2 = 'CSR6 ALERT!: '+' peer ' +  CSR6_peers + ' is DOWN and the status code is ' + Csr6_state + '\n' + 'the reason of failure is '+ connection_fail 
                            alert.append(alert2)
                            
                        else:
                            peers2 = 'CSR6 is peering with ' + CSR6_peers + ' for about ' + index['up-time'] + ' h/m/s'
                            up_peers.append(peers2)
                        if notif_sent != 0 : 
                            notif3 = 'This device has sent ' + str(notif_sent) + ' notifications , please investigate furhter...'
                            alert.append(notif3)
                        elif notif_rec != 0: 
                            notif4  = 'This device has received ' + str(notif_rec) +' notifications , please investigate furhter' 
                            alert.append(notif4)
    
    nornir.close_connections()
    return up_peers,alert
        
#Monitor_BGP_Peerings_Core()
def Monitor_eBGP():#Funcţie care monitorizează sesiunile eBGP
    peers = []
    alert = []

    print('#######Checking the status of eBGP peers in Core network......########')
    print('#######eBGP routers in AS100 are Router Iou1 and Router Iou4:#########')
    print('*******If eBGP peers are down an alert message should pop up .....******')

    try:
        #peers.append(status)
    
        iou1 = nornir.filter(id= "iou1")
        results = iou1.run(netmiko_send_command, command_string="show ip bgp summary" , use_textfsm=True)
        for key in results.keys():
            response = results[key].result # saving the result as a variable 
            for info in range (0,len(response)):
                if response[info]['neigh_as'] == str(Devices['R1']['data']['remote-asn']):
                    print('checking the eBGP peering...')
                    if response[info]['state_pfxrcd'] == '0':
                        
                        alerta = 'ALERT!'+ ' eBGP session have problems the state is ' + response[info]['state_pfxrcd']
                        alert.append(alerta)
                 
                    else:
                        peers.append('The eBGP session with our Customer(1) is UP')  
        print(colored('Checking IOU4 eBGP Router...','yellow'))

        
        iou4 = nornir.filter(id= "iou4")
        
        results = iou4.run(netmiko_send_command, command_string="show ip bgp summary" , use_textfsm=True)
        for key in results.keys():
            response = results[key].result # saving the result as a variable 
            for info in range (0,len(response)):
                if response[info]['neigh_as'] == str(Devices['R4']['data']['remote-asn']):
                    print('checking the eBGP peering...')
                    if response[info]['state_pfxrcd'] == '0':
                        
                        alert.append('ALERT!'+ ' eBGP session have problems the state is ' + response[info]['state_pfxrcd'])
                    else:
                        peers.append('The eBGP session with our Customer(2) is UP')

        for rtr in range(7,9):
            url_CSR = "https://"+ str(Devices['R'+str(rtr)]['hostname'])+":443/restconf/data/Cisco-IOS-XE-bgp-oper:bgp-state-data/neighbors/neighbor" # Connecting using restconf to devices
            peers.append('Connected to CSR'+str(rtr) + ' checking BGP.. Permission granted')

            response = requests.get(url_CSR, auth = (Devices['R'+str(rtr)]['username'],Devices['R'+str(rtr)]['password']),headers=headers,verify=False)#storing the response  of Get operation
            time.sleep(5) # Allowing 5 sec in order to detect any changes
            if response.status_code != 200:# checking the response codes 
                alert.append('Login request failed. Status code is {}'.format(response.status_code))
            else:        
                peers.append('Connected to Router CSR'+str(rtr) + ' Rest API Status code is '+str(response.status_code) + ' OK!')
            bgp_data =response.json() # Storing the respinse and display it in a json data format 
            for index in bgp_data['Cisco-IOS-XE-bgp-oper:neighbor']: #checking the peering status 
                CSR7_peers = index['neighbor-id']
                Csr7_state = index['connection']['state']
                report = 'Router CSR7 is peering with ' +CSR7_peers + ' and the state is '+ Csr7_state # Checking to see if the peers are UP !! 
                    
                if not 'established' in report: # If not an allert will pop up 
                    alert1 = 'CSR7 ALERT!:'+' peer ' +  CSR7_peers + ' is DOWN and the status code is ' + Csr7_state
                    alert.append(alert1)
                else:
                    peer = 'CSR'+str(rtr) + ' is peering with ' + CSR7_peers + ' for about ' + index['up-time'] + ' h/m/s'
                    peers.append(peer)
    except:
        NornirExecutionError
        alert.append('Something went wrong!...')
    nornir.close_connections()       
    return peers, alert
#Monitor_eBGP()

def Connectivity_Test():#Funcţie care testează conectivitatea
    print("Conducting a full ping test....:")
    print("\n")

    device = []
    err = []
    err_handl = []


    try: 
        core_routers = nornir.filter(F(asn=100))
        for x in range (1,9):
            
            ping = core_routers.run(netmiko_send_command ,command_string='ping 1.1.1.'+str(x), use_textfsm=True)
            #print_result(ping)

            for sth in ping.keys():
                #print(sth)
                response = ping[sth].result
                #print(response)
                if not '!!!' in response:
                    failed = '1.1.1.'+str(x)
                    
                    fail = sth + ' cannot ping ' + failed
                    err.append(fail)
                    print(fail)
     
                else:
                    
                    print(sth + ' OK ping works!')

    except:
        NornirExecutionError
        alert = 'I cannot connect to all devices'
        err_handl.append(alert)

    if len(err)==0 and len(err_handl)==0:
        device.append('Connectivity test passed!')
    nornir.close_connections()
    return device, err, err_handl
    
#Connectivity_Test()

