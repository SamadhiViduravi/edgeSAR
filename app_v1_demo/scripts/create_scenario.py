"""Author the checked-in Phase 1 fixture; never generates data at runtime."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
def p(x, y): return {"x": x, "y": y}
def ring(x, y, w, h): return [p(x,y),p(x+w,y),p(x+w,y+h),p(x,y+h),p(x,y)]
def route(points): return [p(*v) for v in points]

regions = [
    {"id": f"BLD-{i+1:02}", "label": f"Building {i+1:02}", "kind": "building", "polygon": ring(*rect)}
    for i, rect in enumerate([(300,220,140,130),(720,380,160,100),(320,650,140,160),
      (80,800,100,180),(330,1150,150,170),(620,1220,130,170),(100,1530,170,200),
      (540,1650,190,160),(920,1700,140,160),(1600,800,220,180),(1700,1700,170,170),(1200,60,200,120)])
]
regions += [
 {"id":"WATER-01","label":"Floodplain · overflight allowed","kind":"water","polygon":route([(40,1880),(800,1880),(1180,1510),(1650,1350),(1960,1250),(1960,1450),(1630,1510),(1200,1680),(850,1970),(40,1970),(40,1880)])},
 {"id":"NFZ-01","label":"NFZ-01 · prohibited airspace","kind":"no_fly","polygon":ring(1180,620,370,360)},
 {"id":"DEBRIS-01","label":"Debris field 01","kind":"debris","polygon":ring(620,650,280,280)},
 {"id":"DEBRIS-02","label":"Debris field 02","kind":"debris","polygon":ring(1200,1550,260,220)},
 {"id":"ROAD-01","label":"Blocked road","kind":"blocked_road","polygon":ring(370,930,110,90)},
]
uavs=[{"id":f"UAV-0{i+1}","position":p(x,140),"speed_mps":speed,"battery_percent":battery,"capabilities":caps,"color":color}
 for i,(x,speed,battery,caps,color) in enumerate([(160,18,85,["RGB"],"#51dec5"),(220,16,75,["RGB","THERMAL"],"#bb9bff"),(280,20,90,["RGB"],"#ffc66d")])]
task_specs=[
 ("Search A1","UAV-01","A1",[(160,140),(160,450),(550,450)]),
 ("Search A2","UAV-02","A2",[(220,140),(220,550),(1050,550),(1050,850)]),
 ("Search B1","UAV-03","B1",[(280,140),(650,140),(650,300),(1450,300),(1750,600)]),
 ("Inspect bridge","UAV-01",None,[(550,450),(550,1050),(850,1050),(850,1450),(1150,1450)]),
 ("Search B2","UAV-02","B2",[(1050,850),(1050,1150),(1550,1150),(1750,1550)]),
]
# Sector IDs follow column then row: A1/A2, B1/B2, C1/C2.
task_specs[1]=(task_specs[1][0],"UAV-02","B1",task_specs[1][3])
task_specs[2]=(task_specs[2][0],"UAV-03","C1",task_specs[2][3])
task_specs[4]=(task_specs[4][0],"UAV-02","C2",task_specs[4][3])
# Labels track actual sector IDs to avoid implying incorrect spatial ownership.
task_specs=[(f"Search {s}" if s else label,u,s,pts) for label,u,s,pts in task_specs]
scenario={"schema_version":1,"id":"urban-disaster","version":"1.0.0","name":"Urban Disaster Search","seed":42,
 "width_m":2000,"height_m":2000,"origin":{"longitude":79.86,"latitude":6.92},"base":p(220,80),
 "sectors":[{"id":f"{col}{row+1}","label":f"{col}{row+1}","polygon":ring(i*2000/3,row*1000,2000/3,1000)} for i,col in enumerate("ABC") for row in range(2)],
 "regions":regions,"uavs":uavs,
 "tasks":[{"id":f"TASK-0{i+1}","label":label,"type":"AREA_SEARCH" if sector else "INFRASTRUCTURE_INSPECTION","location":p(*pts[-1]),"assigned_uav_id":uav,"route":route(pts),"service_seconds":12 if sector else 20,"sector_id":sector} for i,(label,uav,sector,pts) in enumerate(task_specs)]}
(ROOT/'scenarios').mkdir(exist_ok=True)
(ROOT/'scenarios/urban-disaster.json').write_text(json.dumps(scenario,indent=2)+'\n')
