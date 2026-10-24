import requests,sys
B=open('/app/frontend/.env').read().split('REACT_APP_BACKEND_URL=')[1].split()[0].rstrip('/')
s=requests.Session()
t=s.post(B+'/api/auth/identify',json={"identifier":"baa","terms_accepted":True,"privacy_accepted":True}).json()
tok=t.get('account_token') or t.get('token'); 
r=s.post(B+'/api/auth/login',json={"account_token":tok,"pin":"130994","remember":True}); print(r.status_code)
if sys.argv[1]=='create':
    r=s.post(B+'/api/users',json={"name":"TEST_Rider55","username":"test_rider55","role":"rider","pin":"551155","whatsapp":"081234567890"}); print(r.status_code,r.text[:200])
