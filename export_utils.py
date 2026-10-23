"""Экспорт расписания в XLSX, PDF и JSON без выполнения пользовательских формул."""
import io,json,html
from openpyxl import Workbook
from openpyxl.styles import PatternFill,Font
from reportlab.platypus import SimpleDocTemplate,Paragraph,Table,TableStyle,Spacer
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape,A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

def safe(value):
    value=str(value)
    return "'"+value if value and value[0] in "=+-@" else value
def excel(data):
    wb=Workbook();ws=wb.active;ws.title="Расписание"
    ws.append(["Заявка","Название","Приоритет","Исполнитель","Начало","Длительность","SLA"] )
    for a in data["assignments"]:ws.append([safe(a["task_id"]),safe(a["title"]),a["priority"],safe(a["engineer"]),a["slot"],a["duration"],"В срок" if a["sla_ok"] else "Нарушен"])
    for c in ws[1]:c.font=Font(bold=True,color="FFFFFF");c.fill=PatternFill("solid",fgColor="274C77")
    for col,width in zip("ABCDEFG",[18,56,16,25,12,16,15]):ws.column_dimensions[col].width=width
    ws.freeze_panes="A2";ws.auto_filter.ref=ws.dimensions
    grid=wb.create_sheet("Сетка");grid.append(["Исполнитель"]+[str(i) for i in range(data["num_slots"])])
    for w in data["workers"]:
        row=[w["name"]]+["" for _ in range(data["num_slots"])]
        for a in data["assignments"]:
            if a["engineer"]==w["name"]:
                for s in range(a["slot"],a["slot"]+a["duration"]):row[s+1]=safe(a["task_id"])
        grid.append(row)
    loads=wb.create_sheet("Загрузка");loads.append(["Исполнитель","Уровень","Занято","Лимит","Утилизация %"])
    for w in data["workers"]:loads.append([w["name"],w["level"],data["loads"][w["name"]],w["max_slots"],round(100*data["loads"][w["name"]]/w["max_slots"],1)])
    missed=wb.create_sheet("Не назначенные");missed.append(["Заявка","Причина"])
    for x in data["unassigned"]:missed.append([safe(x["task_id"]),safe(x["reason"])])
    b=io.BytesIO();wb.save(b);return b.getvalue()
def pdf(data):
    pdfmetrics.registerFont(TTFont("DejaVu","/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
    styles=getSampleStyleSheet();styles["Normal"].fontName="DejaVu";styles["Title"].fontName="DejaVu"
    rows=[["Заявка","Название","Исполнитель","Часы","SLA"]]
    for a in data["assignments"]:rows.append([safe(a["task_id"]),safe(a["title"])[:44],safe(a["engineer"]),f'{a["slot"]}–{a["slot"]+a["duration"]}',"OK" if a["sla_ok"] else "!"])
    elements=[Paragraph("Расписание задач",styles["Title"]),Spacer(1,12)]
    tab=Table([[Paragraph(html.escape(str(x)),styles["Normal"]) for x in row] for row in rows],colWidths=[75,290,110,55,40],repeatRows=1)
    tab.setStyle(TableStyle([("GRID",(0,0),(-1,-1),0.3,colors.grey),("BACKGROUND",(0,0),(-1,0),colors.lightgrey),("VALIGN",(0,0),(-1,-1),"TOP")]))
    elements.append(tab);elements.append(Spacer(1,10));elements.append(Paragraph("Неназначенные заявки: "+str(len(data["unassigned"])),styles["Normal"]))
    b=io.BytesIO();SimpleDocTemplate(b,pagesize=landscape(A4)).build(elements);return b.getvalue()
def json_bytes(data):return json.dumps(data,ensure_ascii=False,indent=2).encode("utf-8")
