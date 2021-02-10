from flask import Flask , render_template , redirect, url_for,request ,render_template_string
from main_script import *
import sys
import yaml

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
            loading_inf ='Loading!  Please wait... '
            
            output= BGP_Configuration()
            return render_template('/index.html', template_ok=output[0], template_hand=output[1], template_info=loading_inf)
        
        elif request.form["button"]=="Monitor_BGP_Peerings_Core":
            output=Monitor_BGP_Peerings_Core()
            print(output[1])
            loading_inf ='Loading!  Please wait... '
            return render_template('/index.html', template_ok=output[0], template_err=output[1], template_hand=output[2], template_info=loading_inf)
        
        elif request.form["button"]=='Monitor_eBGP':
            output=Monitor_eBGP()
            loading_inf ='Loading!  Please wait... '

            return render_template('/index.html', template_ok=output[0], template_err=output[1],tempalte_info=loading_inf)
            
        elif request.form["button"]=='Connectivity_Test':
            loading_inf ='Loading!  Please wait... '
            output=Connectivity_Test()

            return render_template('/index.html', template_ok=output[0], template_err=output[1], template_hand=output[2], template_info=loading_inf)

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
    return render_template('table.html')




if __name__ == '__main__':
    app.run(host="10.1.1.4",port=8080,debug=True)
