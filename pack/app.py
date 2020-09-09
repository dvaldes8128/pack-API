import json
from py3dbp import Item
from pack import pack
# import requests

#event example
#{
#    'items':
#    {
#        'item_i':{
#            'width':1,
#            'height':2,
#            'depth':3,
#            'weight':0.1,
#            'quantity':5
#        }
#    },
#    'fillers':True
#}

def lambda_handler(event, context):
    items=[]
    for it, prop in event['body']['items'].items():
        for i in range(prop['quantity']):
            items.append(Item(
                name=it+f'_{i:0>3d}',
                width=prop['width'],
                height=prop['height'],
                depth=prop['depth'],
                weight=prop['weight']
            ))
    if event['body']['fillers']:
        max_o=.85
    else:
        max_o=1
    dim=pack(items,max_o=max_o)
    
    return {
        "statusCode": 200,
        "body": json.dumps({
            'width':dim[0],
            'height':dim[1],
            'depth':dim[2]
        }),
    }
