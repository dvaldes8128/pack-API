from py3dbp import Bin,Item,Packer
from sympy.utilities.iterables import multiset_permutations,subsets
from joblib import load
from numpy import meshgrid,arange,ceil

def get_region(it):
    size_summary=[]
    for i in it:
        size_summary.append(
            (
                max(i.width,i.depth,i.height),
                min(i.width,i.depth,i.height)
            ))
    upper=sum(x[0] for x in size_summary)
    lower=max(x[1] for x in size_summary)
    side=upper-lower
    return {'upper':float(upper),'lower':float(lower),'side':float(side)}


def get_packed_size(dim,it):
    cont=Bin(f'dim={dim}',*dim,10*10)
    pack=Packer()
    pack.add_bin(cont)
    for i in it:
        pack.add_item(i)
    pack.pack()
    unpacked=0
    for b in pack.bins:
        for item in b.unfitted_items:
            unpacked+=1
    if unpacked==0:
        farthest=[[c+s for c,s in zip(i.position,i.get_dimension())] for i in pack.items]
        return (
            float(max(farthest,key=lambda x: x[0])[0]),
            float(max(farthest,key=lambda x: x[1])[1]),
            float(max(farthest,key=lambda x: x[2])[2])
        )
    else: return None

def get_corners(it,initial,depth=3):
    corners={get_packed_size(initial,it)}
    expanded=set()
    axes_list=list(subsets(range(3)))[1:]
    while depth:
        if corners==expanded:
            break
        n_corners=set()
        for corner in corners:
            if corner and corner not in expanded:
                for axes in axes_list:
                    l=list(initial)
                    for i in axes:
                        n_axis=corner[i]
                        l[i]=(n_axis//.25)*.25 if n_axis%.25!=0 else n_axis-.25
                    n_corners|={
                        get_packed_size(tuple(l),it)
                    }
                expanded|={corner}
        corners|=n_corners
        depth-=1

    #clean non optimal
    corners=[i for i in corners if i!=None]
    main_corners=[]
    def dominate(p1,p2):
        return p1[0]<=p2[0] and p1[1]<=p2[1] and p1[2]<=p2[2]
    while corners:
            b=corners.pop(0)
            for v in corners:
                if dominate(b,v):
                    corners.remove(v)
                elif dominate(v,b):
                    b=v
            main_corners.append(b)
            corners=[x for x in corners if not dominate(b,x)]

    return main_corners
    

def get_init(corners):
    rounded=[tuple(ceil(x[i]*4)/4 for i in range(3)) for x in corners ]
    permuted=set()
    for corner in rounded:
        permuted|=set(tuple(x) for x in multiset_permutations(corner))
    return permuted

def get_grid(p1,p2,step=.25):
    _p1=(min(p1[0],p2[0]),min(p1[1],p2[1]),min(p1[2],p2[2]))
    _p2=(max(p1[0],p2[0]),max(p1[1],p2[1]),max(p1[2],p2[2]))
    xx,yy,zz = meshgrid(arange(_p1[0],_p2[0]+step/2,step),
                    arange(_p1[1],_p2[1]+step/2,step),
                    arange(_p1[2],_p2[2]+step/2,step),
                    )
    return [tuple(i) for i in zip(xx.flat,yy.flat,zz.flat)]

clf=load('OneClassSVM_0.9_yx,zx.model')
beauty=lambda x: clf.decision_function([[x[1]/x[0],x[2]/x[0]]])[0]

def get_o_fn(it):
    volume=float(sum(i.width*i.height*i.depth for i in it))
    return lambda x: volume/(x[1]*x[2]*x[0])

def get_pareto(corners,b_fn,o_fn,max_o=1,never_worst=True):
    min_corner=min(o_fn(p) for p in corners)
    grid=set()
    for corner in corners:
        grid.update(get_grid(corner,(1.1*corner[0],1.1*corner[1],1.1*corner[2])))
    evaluated_grid={p:{'b':b_fn(p),'o':o_fn(p)} for p in grid}

    evaluated_grid={k:v for k,v in evaluated_grid.items() if (v['o']<=max_o and (v['o']>=min_corner if never_worst else True))}
    
    grid_keys=list(evaluated_grid.keys())
    dominant={}

    def dominate(p1,p2):
        return evaluated_grid[p1]['b']>evaluated_grid[p2]['b'] and evaluated_grid[p1]['o']>evaluated_grid[p2]['o']
    while grid_keys:
            b=grid_keys.pop(0)
            for v in grid_keys:
                if dominate(b,v):
                    grid_keys.remove(v)
                elif dominate(v,b):
                    b=v
            dominant[b]=evaluated_grid[b]
            grid_keys=[x for x in grid_keys if not dominate(b,x)]

    return dominant

def select(dominant):
    #abs_max=max(dominant,key=lambda x: dominant[x]['o'])
    #if dominant[abs_max]['b']>=-10**-2:
    #    return abs_max
    best_b  = max((k for k,v in dominant.items() if v['b']>=-10**-2),key=lambda x: dominant[x]['o'])
    best_nb = max((k for k,v in dominant.items() if v['b'] <-10**-2),key=lambda x: dominant[x]['o'])
    best = best_b if dominant[best_b]['o']/dominant[best_nb]['o']>=.8 else best_nb
    return best 

def pack(items,b_fn=beauty,max_o=1,never_worst=True):
    region=get_region(items)
    upper=region['upper']
    corners=get_corners(items,(upper,upper,upper),5)
    init=get_init(corners)
    cand=get_pareto(init,beauty,get_o_fn(items),max_o=max_o)
    dim=select(cand)
    return dim
    
