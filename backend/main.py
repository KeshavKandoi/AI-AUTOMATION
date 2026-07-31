from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.responses import RedirectResponse
from pydantic_settings import BaseSettings
from jose import jwt, JWTError
import httpx

class Settings(BaseSettings):
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str
    SUPABASE_JWT_SECRET: str
    GITHUB_CLIENT_ID: str
    GITHUB_CLIENT_SECRET: str
    GITHUB_REDIRECT_URI: str

    class Config:
        env_file = ".env"

settings = Settings()

app = FastAPI(title="AI COO Backend")

@app.get("/health")
def health_check():
    return {"status": "ok"}

def get_current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated"
        )
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

@app.get("/me")
def get_me(user: dict = Depends(get_current_user)):
    return {"id": user.get("sub"), "email": user.get("email")}

# ---------- GitHub OAuth ----------

@app.get("/github/login")
def github_login():
    url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={settings.GITHUB_CLIENT_ID}"
        f"&redirect_uri={settings.GITHUB_REDIRECT_URI}"
        f"&scope=repo,read:user"
    )
    return RedirectResponse(url)

@app.get("/github/callback")
async def github_callback(code: str):
    async with httpx.AsyncClient() as client:
        token_res = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": settings.GITHUB_REDIRECT_URI,
            },
        )
        token_data = token_res.json()

    access_token = token_data.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="GitHub auth failed")

    # For now just return it — Phase 2.4 will save it to Supabase
    return {"access_token": access_token}

# ---------- GitHub Data ----------

@app.get("/github/repos")
async def github_repos(access_token: str):
    async with httpx.AsyncClient() as client:
        res = await client.get(
            "https://api.github.com/user/repos",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    return res.json()
