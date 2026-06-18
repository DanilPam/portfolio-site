import json
import os
from dotenv import load_dotenv 
from fastapi import FastAPI, Request, HTTPException, status, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

load_dotenv()

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

JSON_FILE = "projects.json"


# --- РАБОТА С JSON ---

def load_projects():
    if not os.path.exists(JSON_FILE):
        return []
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_projects(projects):
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(projects, f, ensure_ascii=False, indent=4)


# --- ПРОВЕРКА АВТОРИЗАЦИИ ---

def is_authenticated(request: Request) -> bool:
    return request.cookies.get("session_token") == "active"


# --- ПУБЛИЧНЫЕ МАРШРУТЫ ---

@app.get("/", response_class=HTMLResponse)
async def home_page(request: Request):
    projects = load_projects()
    return templates.TemplateResponse(
        request=request, name="index.html", context={"projects": projects}
    )

@app.get("/projects/{project_id}", response_class=HTMLResponse)
async def project_page(request: Request, project_id: int):
    projects = load_projects()
    project = next((p for p in projects if p["id"] == project_id), None)
    if not project:
        raise HTTPException(status_code=404, detail="Проект не найден")
    return templates.TemplateResponse(
        request=request, name="project_detail.html", context={"project": project}
    )


# --- АВТОРИЗАЦИЯ (ЛОГИН / ЛОГАУТ) ---

@app.get("/admin/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if is_authenticated(request):
        return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(request=request, name="login.html", context={"error": None})

@app.post("/admin/login")
async def login_process(request: Request, username: str = Form(...), password: str = Form(...)):
    if username == os.getenv("ADMIN_USERNAME") and password == os.getenv("ADMIN_PASSWORD"):
        response = RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(key="session_token", value="active", httponly=True)
        return response
    
    return templates.TemplateResponse(
        request=request, name="login.html", context={"error": "Неверный логин или пароль"}
    )

@app.get("/admin/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("session_token")
    return response


# --- ЗАЩИЩЕННАЯ АДМИНКА ---

@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
    
    projects = load_projects()
    return templates.TemplateResponse(
        request=request, name="admin.html", context={"projects": projects}
    )

@app.post("/admin/add")
async def add_project(request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
        
    form_data = await request.form()
    projects = load_projects()
    new_id = max([p["id"] for p in projects], default=0) + 1
    
    new_project = {
        "id": new_id,
        "title": form_data.get("title"),
        "short_desc": form_data.get("short_desc"),
        "full_desc": form_data.get("full_desc")
    }
    
    projects.append(new_project)
    save_projects(projects)
    return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/admin/delete/{project_id}")
async def delete_project(request: Request, project_id: int):
    if not is_authenticated(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
        
    projects = load_projects()
    projects = [p for p in projects if p["id"] != project_id]
    save_projects(projects)
    return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)
