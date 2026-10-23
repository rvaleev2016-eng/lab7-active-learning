"""Интерактивная диаграмма Ганта с длительностью и SLA."""
import plotly.graph_objects as go
COLORS={"critical":"#B42318","high":"#E67E22","medium":"#D6A100","low":"#26865C"}
def build_gantt(data):
    fig=go.Figure()
    workers=[w["name"] for w in data["workers"]]
    for priority,color in COLORS.items():
        subset=[a for a in data["assignments"] if a["priority"]==priority]
        fig.add_trace(go.Bar(name=priority,orientation="h",y=[a["engineer"] for a in subset],x=[a["duration"] for a in subset],base=[a["slot"] for a in subset],marker_color=color,text=[a["task_id"]+(" ⚠" if not a["sla_ok"] else "") for a in subset],hovertext=[a["title"] for a in subset],hovertemplate="%{text}<br>%{hovertext}<extra></extra>"))
    fig.update_layout(title="График работ — не назначено: "+str(len(data["unassigned"])),xaxis_title="Часовой слот",yaxis_title="Исполнитель",barmode="overlay",height=420)
    fig.update_xaxes(range=[0,data["num_slots"]],dtick=1,showgrid=True)
    fig.update_yaxes(categoryorder="array",categoryarray=list(reversed(workers)))
    return fig
