from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.responses import RedirectResponse
from pydantic_settings import BaseSettings
from jose import jwt, JWTError
from supabase import create_client
from google import genai
import httpx

class Settings(BaseSettings):
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str
    SUPABASE_JWT_SECRET: str
    GITHUB_CLIENT_ID: str
    GITHUB_CLIENT_SECRET: str
    GITHUB_REDIRECT_URI: str
    GEMINI_API_KEY: str

    class Config:
        env_file = ".env"

settings = Settings()

supabase_admin = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)

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
def github_login(org_id: str):
    url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={settings.GITHUB_CLIENT_ID}"
        f"&redirect_uri={settings.GITHUB_REDIRECT_URI}"
        f"&scope=repo,read:user"
        f"&state={org_id}"
    )
    return RedirectResponse(url)

@app.get("/github/callback")
async def github_callback(code: str, state: str):
    org_id = state

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

    integration = supabase_admin.table("integrations").insert({
        "organization_id": org_id,
        "provider": "github",
        "connected": True
    }).execute()

    integration_id = integration.data[0]["id"]

    supabase_admin.table("oauth_tokens").insert({
        "integration_id": integration_id,
        "access_token": access_token
    }).execute()

    return {"status": "connected", "integration_id": integration_id, "access_token": access_token}

# ---------- GitHub Data ----------

@app.get("/github/repos")
async def github_repos(access_token: str):
    async with httpx.AsyncClient() as client:
        res = await client.get(
            "https://api.github.com/user/repos",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    return res.json()

# ---------- GitHub Agent (AI Summary) ----------

@app.get("/github/summary")
async def github_summary(access_token: str):
    async with httpx.AsyncClient() as client:
        repos_res = await client.get(
            "https://api.github.com/user/repos",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    repos = repos_res.json()

    if not isinstance(repos, list):
        raise HTTPException(status_code=400, detail=f"GitHub API error: {repos}")

    repo_info = [
        {
            "name": r["name"],
            "language": r.get("language"),
            "open_issues": r.get("open_issues_count"),
            "description": r.get("description"),
        }
        for r in repos
    ]

    prompt = f"""You are an AI assistant summarizing a developer's GitHub activity.
Here is their repo data: {repo_info}

Give a short, clear summary covering:
- Total repos
- Which repos have open issues that need attention
- What kind of projects they're working on (languages/themes)
Keep it under 150 words."""

    response = gemini_client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt
    )

    return {"summary": response.text}
