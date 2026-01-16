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
    api_calls = []  # Track all API calls made
    
    # 1. Fetch the "Source of Truth" attributes first
    server = Server(PD_CONFIG['host'], port=PD_CONFIG['port'])
    with Connection(server, PD_CONFIG['user'], PD_CONFIG['pass'], auto_bind=True) as conn:
        conn.search(selected_dn, '(objectClass=*)', attributes=['*'])
        sot_entry = conn.entries[0].entry_attributes_as_dict

    # 2. Determine Username Priority
    p1_username = (sot_entry.get('trilogieWorkEmail', [None])[0] or 
                   sot_entry.get('trilogieOtherEmail', [None])[0] or 
                   sot_entry.get('trilogieWorkTel', [None])[0] or 
                   sot_entry.get('trilogieMobile', [''])[0])

    print(f"[DEBUG] Creating PingOne user for username: {p1_username}", file=sys.stdout)

    # 3. Create user in PingOne (initial creation without trilogieLinkID)
    token = get_p1_token()
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    payload = {
        "username": p1_username,
        "email": sot_entry.get('trilogieWorkEmail', [''])[0],
        "name": {
            "given": sot_entry.get('givenName', [''])[0],
            "family": sot_entry.get('sn', [''])[0]
        },
        "population": {"id": P1_CONFIG['pop_id']}
    }
    p1_res = requests.post(f"https://api.pingone.com/v1/environments/{P1_CONFIG['env_id']}/users",
                           headers=headers, json=payload)
    p1_json = p1_res.json()
    
    # Track the create user API call
    api_calls.append({
        'method': 'POST',
        'endpoint': f"https://api.pingone.com/v1/environments/{P1_CONFIG['env_id']}/users",
        'status_code': p1_res.status_code,
        'request_body': payload,
        'response': p1_json
    })

    # 4. Extract PingOne UUID to use as the canonical link_id
    p1_id = p1_json.get('id') or p1_json.get('userId') or p1_json.get('uuid')
    if not p1_id:
        # Fallback: generate a UUID locally (shouldn't be necessary if PingOne returns an id)
        p1_id = str(uuid.uuid4())

    print(f"[DEBUG] Using PingOne ID as trilogieLinkID: {p1_id}", file=sys.stdout)

    # 5. Update all duplicates in PingDirectory to set trilogieLinkID to the PingOne ID (immediately after PingOne user created)
    # Clear any existing trilogieLinkID values first, then set the new one
    server = Server(PD_CONFIG['host'], port=PD_CONFIG['port'])
    with Connection(server, PD_CONFIG['user'], PD_CONFIG['pass'], auto_bind=True) as conn:
        for dn in all_dns:
            try:
                # First, clear any existing values
                try:
                    conn.modify(dn, {'trilogieLinkID': [(MODIFY_DELETE, [])]})
                    print(f"[DEBUG] Cleared existing trilogieLinkID for {dn}", file=sys.stdout)
                except Exception:
                    # Attribute might not exist, continue
                    pass
                
                # Now set the new value
                conn.modify(dn, {'trilogieLinkID': [(MODIFY_REPLACE, [p1_id])]})
                print(f"[DEBUG] Updated {dn} with trilogieLinkID: {p1_id}", file=sys.stdout)
            except Exception as e:
                print(f"[ERROR] Failed to update {dn}: {str(e)}", file=sys.stdout)

    # 6. Update the PingOne user to include trilogieLinkID attribute
    try:
        update_payload = {"trilogieLinkID": p1_id}
        p1_patch_res = requests.patch(f"https://api.pingone.com/v1/environments/{P1_CONFIG['env_id']}/users/{p1_id}",
                                      headers=headers, json=update_payload)
        
        # Track the patch user API call
        api_calls.append({
            'method': 'PATCH',
            'endpoint': f"https://api.pingone.com/v1/environments/{P1_CONFIG['env_id']}/users/{p1_id}",
            'status_code': p1_patch_res.status_code,
            'request_body': update_payload,
            'response': p1_patch_res.json() if p1_patch_res.status_code in [200, 204] else p1_patch_res.text
        })
        
        if p1_patch_res.status_code in [200, 204]:
            print(f"[DEBUG] Successfully patched PingOne user {p1_id} with trilogieLinkID: {p1_id}", file=sys.stdout)
        else:
            print(f"[ERROR] Failed to patch PingOne user: {p1_patch_res.status_code} - {p1_patch_res.text}", file=sys.stdout)
    except Exception as e:
        print(f"[ERROR] Failed to patch PingOne user: {str(e)}", file=sys.stdout)

    # 6a. Re-fetch the PingOne user to get all populated trilogie attributes
    try:
        p1_get_res = requests.get(f"https://api.pingone.com/v1/environments/{P1_CONFIG['env_id']}/users/{p1_id}",
                                  headers=headers)
        if p1_get_res.status_code == 200:
            p1_json = p1_get_res.json()  # Update with complete user data including all trilogie attributes
            print(f"[DEBUG] Re-fetched PingOne user {p1_id} with all attributes", file=sys.stdout)
        else:
            print(f"[WARNING] Failed to re-fetch PingOne user: {p1_get_res.status_code}", file=sys.stdout)
        
        # Track the get user API call
        api_calls.append({
            'method': 'GET',
            'endpoint': f"https://api.pingone.com/v1/environments/{P1_CONFIG['env_id']}/users/{p1_id}",
            'status_code': p1_get_res.status_code,
            'request_body': None,
            'response': p1_json if p1_get_res.status_code == 200 else p1_get_res.text
        })
    except Exception as e:
        print(f"[ERROR] Failed to re-fetch PingOne user: {str(e)}", file=sys.stdout)

    # 7. Re-fetch the updated Trilogie entry to reflect changes in the template
    server = Server(PD_CONFIG['host'], port=PD_CONFIG['port'])
    with Connection(server, PD_CONFIG['user'], PD_CONFIG['pass'], auto_bind=True) as conn:
        conn.search(selected_dn, '(objectClass=*)', attributes=['*'])
        updated_entry = conn.entries[0].entry_attributes_as_dict
        print(f"[DEBUG] Re-fetched updated entry for {selected_dn}", file=sys.stdout)

    return render_template('index.html', success=True, pd_entry=updated_entry, p1_entry=p1_json, link_id=p1_id, api_calls=api_calls)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)