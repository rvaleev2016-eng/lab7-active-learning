"""Учебный MILP-планировщик с проверкой квалификации и дедлайна."""
import pulp
SLA={"critical":1,"high":3,"medium":5,"low":8}
LEVEL={"L1":1,"L2":2,"L3":3}
REQUIRED={"critical":3,"high":2,"medium":1,"low":1}

def schedule(tasks,workers,horizon=8):
    horizon=max(1,min(int(horizon),24))
    model=pulp.LpProblem("TaskScheduling",pulp.LpMinimize)
    x={}
    for i,t in enumerate(tasks):
        for j,w in enumerate(workers):
            if LEVEL[w["level"]]<REQUIRED[t["priority"]]:continue
            for s in range(horizon-int(t["duration"])+1):
                x[i,j,s]=pulp.LpVariable(f"x_{i}_{j}_{s}",cat="Binary")
    for i,t in enumerate(tasks):
        model+=pulp.lpSum(v for (ii,j,s),v in x.items() if ii==i)<=1
    for j,w in enumerate(workers):
        for hour in range(horizon):
            model+=pulp.lpSum(v for (i,jj,s),v in x.items() if jj==j and s<=hour<s+tasks[i]["duration"])<=1
        model+=pulp.lpSum(v*tasks[i]["duration"] for (i,jj,s),v in x.items() if jj==j)<=w["max_slots"]
    # Пропуск заявки дороже просрочки; критичные заявки имеют больший вес
    penalty={"critical":120,"high":80,"medium":45,"low":20}
    missed=pulp.lpSum(penalty[t["priority"]]*(1-pulp.lpSum(v for (ii,j,s),v in x.items() if ii==i)) for i,t in enumerate(tasks))
    late=pulp.lpSum((30 if t["priority"] in ("critical","high") else 12)*max(0,s+t["duration"]-SLA[t["priority"]])*v for (i,j,s),v in x.items() for t in [tasks[i]])
    model+=missed+late
    model.solve(pulp.PULP_CBC_CMD(msg=False,timeLimit=15))
    assignments=[]
    for (i,j,s),v in x.items():
        if pulp.value(v) is not None and pulp.value(v)>0.5:
            t=tasks[i];w=workers[j]
            assignments.append({"task_id":t["id"],"title":t["title"],"priority":t["priority"],"engineer":w["name"],"level":w["level"],"slot":s,"duration":t["duration"],"sla_ok":s+t["duration"]<=SLA[t["priority"]]})
    assigned={a["task_id"] for a in assignments}
    unassigned=[{"task_id":t["id"],"reason":"Нет доступного специалиста/слотов в выбранном горизонте"} for t in tasks if t["id"] not in assigned]
    loads={w["name"]:sum(a["duration"] for a in assignments if a["engineer"]==w["name"]) for w in workers}
    return {"status":pulp.LpStatus[model.status],"assignments":sorted(assignments,key=lambda a:(a["slot"],a["engineer"])),"unassigned":unassigned,"loads":loads,"workers":workers,"num_slots":horizon,"total_penalty":round(float(pulp.value(model.objective) or 0),2)}
