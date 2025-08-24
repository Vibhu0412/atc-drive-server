

Here’s a clean **README.md** draft for your project based on the steps you shared:  

```markdown
# ATC Drive - FastAPI Project

## 🚀 Setup Instructions

### 1. Install Python
Make sure you have **Python 3.10+** installed.  
You can verify with:
```bash
python --version
```

### 2. Install Requirements
Install dependencies from `requirements.txt`:
```bash
pip install -r requirements.txt
```

### 3. Install PostgreSQL
Download and install PostgreSQL (version 13+ recommended).  
Create a database named `drive_db` (or as per your `.env` configuration).

### 4. Create `.env` File
At the root level of your project, create a file named **`.env`** with the following values:

```env
DB_HOST="localhost"
DB_PORT=5432
DB_USER="postgres"
DB_PASSWORD="postgres"
DB_NAME="drive_db"

JWTALGORITHM="HS256"
JWTSECRETKEY=***

ENVIRONMENT="DEV"

AWS_ACCESS_KEY_ID="***"
AWS_SECRET_ACCESS_KEY="***"
AWS_REGION="ap-south-1"
S3_BUCKET_NAME="my-atcdrive-bucket"
```

⚠️ Replace `***` with your actual secret values.

### 5. Allow CORS
Update `main.py` and add your IP/domain in the CORS configuration to avoid browser CORS errors.

### 6. Run Alembic Migrations
Run database migrations before starting the server:
```bash
alembic upgrade head
```

### 7. Run the Project
Start the FastAPI app using Uvicorn:
```bash
uvicorn main:app --port 7007 --reload
```

---

## 📂 Project Info
- **Framework**: FastAPI  
- **Database**: PostgreSQL  
- **Auth**: JWT-based authentication  
- **Storage**: AWS S3 bucket integration  

---

## ✅ Notes
- Ensure PostgreSQL is running before starting the app.  
- Keep your `.env` file private and **do not commit it** to version control.  
```