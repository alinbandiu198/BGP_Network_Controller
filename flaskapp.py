from flask import Flask , render_template , redirect, url_for,request ,render_template_string
from BGP_Automation import *
import sys
import yaml
import os 
import threading
import time

app=Flask(__name__ )
app.static_folder = 'static'

with open ("hosts.yaml", "r") as f: 
    Devices = yaml.load(f, Loader=yaml.FullLoader)

  
@app.route('/', methods=['GET','POST'])
def login():
    error=None
    if request.method=='POST':
        if request.form['username'] != 'admin' or request.form['password']!='admin':
            error='Invalid Credentials!'
        else:
            return redirect(url_for('index'))
    return render_template('/login.html', error=error)

    return render_template('/login.html')

@app.route('/dashboard', methods=['GET', 'POST'])

def index():
    
    if request.method == 'POST':
        the_form = request.form
        address = the_form["ip_address"]
        print(address)
      

        if request.form["button"] == "Underlay_Monitor":
            loading_inf ='Loading!  Please wait... '
            output=Underlay_Monitor()
           
            print(output)
            err_point = len(output[1])
            err_point1=len(output[2])
            suma = err_point*20 + err_point1*30 
            err_points = 100 - suma 

            return render_template('/index.html' ,template_info=loading_inf, template_ok=output[0], template_err = output[1], template_hand = output[2], template_err_points=err_points)
        
        elif request.form["button"] == "BGP_Configuration":
            output= BGP_Configuration()
            loading_inf ='Loading!  Please wait... '
            err_point=len(output[1])
            suma = err_point*6.25
            err_points = 100-suma 
            return render_template('/index.html', template_ok=output[0], template_hand=output[1], template_info=loading_inf,template_err_points=err_points)
        
        elif request.form["button"]=="Monitor_BGP_Peerings_Core":
            output=Monitor_BGP_Peerings_Core()
            print(output[0])
            print(output[1])
            err_point = len(output[1])
            suma = err_point*9.09
            err_points=100-suma
            loading_inf ='Loading!  Please wait... '
            return render_template('/index.html', template_ok=output[0], template_err=output[1], template_info=loading_inf,template_err_points=err_points)
        
        elif request.form["button"]=='Monitor_eBGP':
            output=Monitor_eBGP()
            loading_inf ='Loading!  Please wait... '
            err_point = len(output[1])
            if 'Something went wrong!...' in output[1]:
                suma = err_point*70
                err_points=100-suma
            else:
                suma=err_point*20
                err_points=100-suma
            return render_template('/index.html', template_ok=output[0], template_err=output[1],tempalte_info=loading_inf,template_err_points=err_points)
            
        elif request.form["button"]=='Connectivity_Test':
            loading_inf ='Loading!  Please wait... '
            
            device = []
            err = []
            err_handl = []
            if not address:
                err.append('Please provide an ip address first!')
                return render_template('/index.html',template_err=err)
            else:
                err_points=100
                try:
                    core_routers = nornir.filter(F(asn=100))
                    
                    
                    ping = core_routers.run(netmiko_send_command ,command_string='ping '+address + ' source loopback0', use_textfsm=True)
                    print_result(ping)

                    for sth in ping.keys():
                        print(sth)
                        response = ping[sth].result
                        print(response)
                        if not '!!!' in response:
                            failed = address
                            
                            fail = sth + ' cannot ping ' + failed
                            err.append(fail)
                            print(fail)
                            err_points=err_points-12.5



                        else:
                            
                            ping_ok = sth + ' ping was succesfull!'
                            print(ping_ok)
                            device.append(ping_ok)
                            err_points=100
                            

                            

                except:
                    NornirExecutionError
                    alert = 'I cannot connect to all devices'
                    err_handl.append(alert)
                    err_points=0

                if len(err)==0 and len(err_handl)==0:
                    device.append('Connectivity test passed!')
                    err_points=100
                nornir.close_connections()

                

                return render_template('/index.html', template_ok=device, template_err=err, template_hand=err_handl, template_info=loading_inf,template_err_points=err_points)

        elif request.form["button"]=="Automate_Interface_Description":
            
            
            loading_inf ='Loading!  Please wait... '
            output=Automate_Interface_Description()
            return render_template('/index.html', template_ok=output, template_info=loading_inf)

        elif request.form["button"]=="fix_ospf":
            fix = fix_ospf()

            err_points=100        

            return render_template('/index.html', template_fix_ospf=fix , template_err_points=err_points)

    else:
        ok=['Welcome to BGP Network Controller']
        return render_template('/index.html',output=ok)



@app.route('/table',methods=['GET', 'POST'])
def table():
    
    #ospf_info = Underlay_Monitor()zzz
    off_routers = []
    on_routers= []
    for ip in range(1,9):
        target = '1.1.1.'+str(ip)
        response =os.system("fping -c 1 "+ target+ "> /dev/null")
        #print(response)
        if response != 0: 
            router = 'R'+str(ip) 
            
            off_routers.append(router)
        else:
            router = 'R'+str(ip) 
            on_routers.append(router)
    
    ospf = Underlay_Monitor()
    #iBGP = Monitor_BGP_Peerings_Core() 
    #eBGP = Monitor_eBGP() 


    
    return render_template('/table.html', template_off_router=off_routers , template_on_router=on_routers,
                                          template_ospf_ok=ospf[4], template_ospf_error=ospf[3])

if __name__ == '__main__':
    app.run(host="10.1.1.4",port=8080,debug=True)






















