# How to Run the Backend

## Quick Start (3 Steps)

### Step 1: Set up MongoDB

**Option A: MongoDB Atlas (Cloud - FREE & EASIEST) ⭐ Recommended**

1. Go to: https://www.mongodb.com/cloud/atlas/register
2. Sign up for a free account
3. Create a FREE cluster (M0 Sandbox)
4. Click "Connect" button
5. Choose "Connect your application"
6. Copy the connection string (looks like: `mongodb+srv://username:password@cluster.mongodb.net/...`)
7. Update `.env` file with your connection string:
   ```
   MONGODB_URL=mongodb+srv://YOUR_USERNAME:YOUR_PASSWORD@cluster.mongodb.net/?retryWrites=true&w=majority
   ```

**Option B: Install MongoDB Locally**

1. Download from: https://www.mongodb.com/try/download/community
2. Install MongoDB Community Server
3. Start MongoDB service from Windows Services
4. Keep `.env` file as: `MONGODB_URL=mongodb://localhost:27017`

### Step 2: Run the Backend Server

Open Command Prompt or PowerShell in the `backend` folder and run:

```bash
uvicorn main:app --reload --port 8000
```

Or use this single command from the project root:

```bash
cd backend
python -m uvicorn main:app --reload --port 8000
```

### Step 3: Verify it's Running

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

Open browser and go to: http://localhost:8000
You should see: `{"message":"Notebook API is running"}`

## Common Issues & Solutions

### Issue 1: "uvicorn: command not found"
**Solution:**
```bash
pip install uvicorn
# OR
python -m pip install uvicorn
```

### Issue 2: "Port 8000 is already in use"
**Solution:** Use a different port
```bash
uvicorn main:app --reload --port 8001
```
Don't forget to update frontend's `API_URL` to `http://localhost:8001`

### Issue 3: "Cannot connect to MongoDB"
**Solution:**
- For MongoDB Atlas: Check your connection string in `.env`
- For Local MongoDB: Make sure MongoDB service is running
- Check Windows Services → MongoDB Server should be "Running"

### Issue 4: "ModuleNotFoundError"
**Solution:** Install dependencies
```bash
pip install -r requirements.txt
```

## API Endpoints (for testing)

Once running, you can test these endpoints:

- **GET** http://localhost:8000/ → Check if API is running
- **GET** http://localhost:8000/projects → Get all projects
- **POST** http://localhost:8000/projects → Create a project
- **PUT** http://localhost:8000/projects/{id} → Update a project
- **DELETE** http://localhost:8000/projects/{id} → Delete a project

## Stop the Server

Press `CTRL + C` in the terminal where the server is running.

## Next Steps

After backend is running:
1. Open a NEW terminal/command prompt
2. Navigate to `frontend` folder
3. Run: `npm run dev`
4. Open browser: http://localhost:5173
