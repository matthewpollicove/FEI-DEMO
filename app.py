import uuid
import requests
import sys
from flask import Flask, render_template, request, jsonify
from ldap3 import Server, Connection, ALL, MODIFY_REPLACE

app = Flask(__name__)

# Configuration Constants
PD_CONFIG = {
    'host': 'win11',
    'port': 389,
    'user': 'cn=dmanager',
    'pass': 'Ping-2025!',
    'base': 'ou=trilogie,dc=matt,dc=lab'
}

P1_CONFIG = {
    'env_id': 'a7f3b70d-7674-444a-86a0-17fadfbeb832',
    'client_id': 'd7749e7a-e378-4230-873a-09a79eb16f22',
    'client_secret': 'njTk5w5IPF.aVvZ5BwH_wkjpOz~EI3wmM~RBpn.nXMPYk0HmbbFD7jruQummvvWq',
    'pop_id': '212c3db5-724d-47a6-8740-f167576ae920'
}

def get_p1_token():
    auth_url = f"https://auth.pingone.com/{P1_CONFIG['env_id']}/as/token"
    res = requests.post(auth_url, auth=(P1_CONFIG['client_id'], P1_CONFIG['client_secret']), 
                        data={'grant_type': 'client_credentials'})
    return res.json().get('access_token')

@app.route('/', methods=['GET', 'POST'])
def index():
    results = []
    if request.method == 'POST' and 'search_term' in request.form:
        search_term = request.form['search_term']
        print(f"[DEBUG] Search Input: {search_term}", file=sys.stdout)
        
        server = Server(PD_CONFIG['host'], port=PD_CONFIG['port'], get_info=ALL)
        with Connection(server, PD_CONFIG['user'], PD_CONFIG['pass'], auto_bind=True) as conn:
            search_filter = f"(|(trilogieMobile={search_term})(trilogieWorkTel={search_term})(trilogieWorkEmail={search_term})(trilogieOtherEmail={search_term}))"
            conn.search(PD_CONFIG['base'], search_filter, attributes=['*'])
            
            for entry in conn.entries:
                results.append({'dn': entry.entry_dn, 'attrs': entry.entry_attributes_as_dict})
                print(f"[DEBUG] Found DN: {entry.entry_dn}", file=sys.stdout)
                
    return render_template('index.html', results=results)

@app.route('/process', methods=['POST'])
def process():
    selected_dn = request.form.get('sot_dn')
    all_dns = request.form.getlist('all_dns')
    link_id = str(uuid.uuid4())
    
    server = Server(PD_CONFIG['host'], port=PD_CONFIG['port'])
    with Connection(server, PD_CONFIG['user'], PD_CONFIG['pass'], auto_bind=True) as conn:
        # 1. Update all duplicates in PingDirectory
        for dn in all_dns:
            conn.modify(dn, {'trilogieLinkID': [(MODIFY_REPLACE, [link_id])]})
        
        # 2. Fetch the "Source of Truth" attributes
        conn.search(selected_dn, '(objectClass=*)', attributes=['*'])
        sot_entry = conn.entries[0].entry_attributes_as_dict

    # 3. Determine Username Priority
    p1_username = (sot_entry.get('trilogieWorkEmail', [None])[0] or 
                   sot_entry.get('trilogieOtherEmail', [None])[0] or 
                   sot_entry.get('trilogieWorkTel', [None])[0] or 
                   sot_entry.get('trilogieMobile', [''])[0])
    
    print(f"[DEBUG] Posting Username to PingOne: {p1_username}", file=sys.stdout)

    # 4. Create in PingOne
    token = get_p1_token()
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    payload = {
        "username": p1_username,
        "email": sot_entry.get('trilogieWorkEmail', [''])[0],
        "name": {
            "given": sot_entry.get('givenName', [''])[0],
            "family": sot_entry.get('sn', [''])[0]
        },
        "population": {"id": P1_CONFIG['pop_id']},
        "trilogieLinkID": link_id
    }
    p1_res = requests.post(f"https://api.pingone.com/v1/environments/{P1_CONFIG['env_id']}/users", 
                           headers=headers, json=payload)
    
    return render_template('index.html', success=True, pd_entry=sot_entry, p1_entry=p1_res.json(), link_id=link_id)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)