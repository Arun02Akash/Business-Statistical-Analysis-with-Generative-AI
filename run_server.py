import uvicorn
from mini_project_app import app

uvicorn.run(app, host="127.0.0.1", port=8000, workers=1)