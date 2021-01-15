from flask import Flask , render_template , redirect, url_for,request ,render_template_string
from main_script import *
import sys
import yaml

app=Flask(__name__ )
app.static_folder = 'static'
with open ("hosts.yaml", "r") as f: 
    Devices = yaml.load(f, Loader=yaml.FullLoader)

    

@app.route('/index.html', methods=['GET', 'POST'])
def index():

 
    if request.method == 'POST':
        output=Underlay_Monitor()
        print(output)
        
        if request.form["button"] == "Underlay_Monitor":
            
            return render_template('/index.html',template_ok=output[0], template_err = output[1], template_hand = output[2]) 

    else:
        ok=['Welcome to BGP Network Controller']
        return render_template('/index.html',output=ok)



@app.route('/table.html',methods=['GET', 'POST'])
def table():
    return render_template('table.html')



if __name__ == '__main__':
    app.run(host="0.0.0.0",port=8080,debug=True)
