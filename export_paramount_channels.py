import json,os,urllib.parse,urllib.request
server=os.environ['XTREAM_SERVER'].rstrip('/')
def get(action,**kw):
 args={'username':os.environ['XTREAM_USERNAME'],'password':os.environ['XTREAM_PASSWORD'],'action':action,**kw}
 with urllib.request.urlopen(server+'/player_api.php?'+urllib.parse.urlencode(args),timeout=40) as r:return json.load(r)
cats=[c for c in get('get_live_categories') if str(c.get('category_id'))=='1038' and 'PARAMOUNT' in c.get('category_name','').upper() and 'PPV' in c.get('category_name','').upper()]
if len(cats)!=1:raise ValueError('Expected exact Paramount PPV category 1038')
channels=[{'name':x.get('name',''),'stream_id':x.get('stream_id')} for x in get('get_live_streams',category_id='1038') if str(x.get('category_id'))=='1038']
if not channels:raise ValueError('No channels; refusing to publish')
with open('paramount_channels_export.json','w') as f:json.dump({'categories':[{'category_id':'1038','category_name':cats[0]['category_name'],'channels':channels}]},f)
print('Exported',len(channels),'channels')
