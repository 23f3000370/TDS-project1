# main.py
# FastAPI app for LLM Code Deployment project
# Run: uvicorn main:app --reload

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import logging, os, json, shutil, base64, subprocess, datetime
import httpx

app = FastAPI(title="LLM Code Deployment API")

# Environment secrets
EXPECTED_SECRET = os.getenv("TDS_SECRET", "mysecret")
GITHUB_USER = os.getenv("GITHUB_USER")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
AI_PIPE_TOKEN = os.getenv("AI_PIPE_TOKEN")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)


class Attachment(BaseModel):
    name: str
    url: str


class TaskRequest(BaseModel):
    email: str
    secret: str
    task: str
    round: int
    nonce: str
    brief: str
    checks: list[str]
    evaluation_url: str
    attachments: list[Attachment]


async def generate_code_with_ai_pipe(brief: str, attachments: list[Attachment]) -> str:
    """
    Uses AI Pipe to generate HTML/code based on the brief and attachments.
    Handles errors if AI Pipe request fails.
    """
    url = "https://aipipe.org/openrouter/v1/responses"
    headers = {
        "Authorization": f"Bearer {AI_PIPE_TOKEN}",
        "Content-Type": "application/json"
    }

    attachment_info = ""
    if attachments:
        attachment_info = "Attachments provided:\n"
        for att in attachments:
            attachment_info += f"- {att.name}: {att.url}\n"

    prompt = f"Generate minimal HTML for this brief:\n{brief}\n{attachment_info}\n" \
             "Use attachments appropriately in the code if needed."

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=headers, json={"model": "openai/gpt-4.1-nano", "input": prompt}, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            output_text = ""
            if data.get("output"):
                for item in data["output"]:
                    if item.get("content"):
                        for c in item["content"]:
                            if c["type"] == "output_text":
                                output_text += c["text"]
            return output_text or f"<html><body><h1>{brief}</h1></body></html>"
    except Exception as e:
        logging.error("AI Pipe generation failed: %s", e)
        return f"<html><body><h1>{brief} (AI generation failed)</h1></body></html>"


def save_attachments(task_folder: str, attachments: list[Attachment]) -> None:
    os.makedirs(task_folder, exist_ok=True)
    for att in attachments:
        try:
            data = att.url.split(",", 1)[1]  # get base64 part
            content = base64.b64decode(data)
            path = os.path.join(task_folder, att.name)
            with open(path, "wb") as f:
                f.write(content)
            logging.info("Saved attachment: %s", path)
        except Exception as e:
            logging.error("Failed to save attachment %s: %s", att.name, e)


def push_to_github(task_folder: str, repo_name: str):
    """
    Initialize repo, commit, push, enable GitHub Pages.
    Returns (repo_url, pages_url, commit_sha)
    """
    repo_url = f"https://{GITHUB_USER}:{GITHUB_TOKEN}@github.com/{GITHUB_USER}/{repo_name}.git"
    pages_url = f"https://{GITHUB_USER}.github.io/{repo_name}/"

    try:
        if not os.path.exists(os.path.join(task_folder, ".git")):
            subprocess.run(["git", "init"], cwd=task_folder, check=True)

            # ✅ Set Git identity for Render
            subprocess.run(["git", "config", "user.email", "23f3000370@ds.study.iitm.ac.in"], cwd=task_folder, check=True)
            subprocess.run(["git", "config", "user.name", "23f3000370"], cwd=task_folder, check=True)

            subprocess.run(["git", "add", "."], cwd=task_folder, check=True)
            subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=task_folder, check=True)
            subprocess.run(["git", "branch", "-M", "main"], cwd=task_folder, check=True)

        subprocess.run(["git", "remote", "remove", "origin"], cwd=task_folder, check=False)
        subprocess.run(["git", "remote", "add", "origin", repo_url], cwd=task_folder, check=True)
        subprocess.run(["git", "push", "-u", "origin", "main", "--force"], cwd=task_folder, check=True)

        commit_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=task_folder).decode().strip()
        return repo_url, pages_url, commit_sha

    except subprocess.CalledProcessError as e:
        logging.error("GitHub push failed: %s", e)
        raise HTTPException(status_code=500, detail="GitHub push failed")



@app.post("/api-endpoint")
async def api_endpoint(request: TaskRequest):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logging.info("Received request at %s: email=%s, task=%s, round=%d", timestamp, request.email, request.task, request.round)

    # Step 1: verify secret
    if request.secret != EXPECTED_SECRET:
        logging.warning("Invalid secret from %s", request.email)
        raise HTTPException(status_code=403, detail="Secret mismatch")

    # Step 2: save attachments
    task_folder = os.path.join("tasks", request.task)
    save_attachments(task_folder, request.attachments)

    # Step 3: generate/update project files
    generated_html = await generate_code_with_ai_pipe(request.brief, request.attachments)
    index_path = os.path.join(task_folder, "index.html")
    try:
        with open(index_path, "w") as f:
            f.write(generated_html)
        logging.info("Generated index.html using AI Pipe")
    except Exception as e:
        logging.error("Failed to write index.html: %s", e)
        raise HTTPException(status_code=500, detail="Failed to write project files")

    # Step 4: push to GitHub
    repo_url, pages_url, commit_sha = push_to_github(task_folder, request.task)

    # Step 5: log evaluation timestamp
    logging.info("Round %d completed at %s. Commit: %s", request.round, timestamp, commit_sha)

    # Step 6: return success JSON
    return {
        "status": "ok",
        "message": f"Request verified, attachments saved, project scaffolded and pushed",
        "task": request.task,
        "round": request.round,
        "nonce": request.nonce,
        "repo_url": repo_url,
        "pages_url": pages_url,
        "commit_sha": commit_sha,
        "timestamp": timestamp
    }

@app.get("/")
def root():
    return {"message": "LLM Code Deployment API is running!"}
