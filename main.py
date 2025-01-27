from fastapi import FastAPI
from apps.member.routers import router as member_router
from apps.result.routers import router as result_router
from apps.resume.routers import router as resume_router
from apps.interview.routers import router as interview_router

app = FastAPI()

app.include_router(member_router,prefix="/members",tags=["Members"])
app.include_router(interview_router,prefix="/apps",tags=["Interviews"])
app.include_router(resume_router)
app.include_router(result_router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Mock Interview Service!"}