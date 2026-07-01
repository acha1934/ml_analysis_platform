# MongoDB Integration Setup Instructions

## Prerequisites
1. **MongoDB** - Install MongoDB locally or use MongoDB Atlas (cloud)
2. **Python 3.8+** - For backend
3. **Node.js** - For frontend

## Setup Steps

### 1. Install MongoDB

**Option A: Local MongoDB**
- Download from: https://www.mongodb.com/try/download/community
- Install and start MongoDB service
- Default URL: `mongodb://localhost:27017`

**Option B: MongoDB Atlas (Cloud)**
- Sign up at: https://www.mongodb.com/cloud/atlas
- Create a free cluster
- Get your connection string (replace in `.env` file)

### 2. Backend Setup

Navigate to backend folder:
```bash
cd backend
```

Install Python dependencies:
```bash
pip install -r requirements.txt
```

Or install individually:
```bash
pip install fastapi uvicorn pydantic pymongo python-dotenv motor python-multipart
```

Update `.env` file if needed:
```env
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=notebook_db
ADMIN_PASSWORD=admin123
```

Start the backend server:
```bash
uvicorn main:app --reload --port 8000
```

The API will run on: http://localhost:8000

### 3. Frontend Setup

Navigate to frontend folder:
```bash
cd frontend
```

Install dependencies (if not already done):
```bash
npm install
```

Start the frontend:
```bash
npm run dev
```

The frontend will run on: http://localhost:5173

### 4. Test the Integration

1. Open http://localhost:5173 in your browser
2. Login with password: `admin123`
3. You should see the dashboard with one default notebook
4. Try:
   - Creating new notebooks (click "New notebook")
   - Renaming notebooks (click on the title)
   - Starring notebooks (click star icon)
   - Deleting notebooks (click three dots → Delete)
   - The delete confirmation dialog should appear

## API Endpoints

### Projects API
- `GET /projects` - Get all projects
- `POST /projects` - Create a new project
- `PUT /projects/{project_id}` - Update a project
- `DELETE /projects/{project_id}` - Delete a project

### Authentication
- `POST /admin-login` - Admin login

## Features Implemented

✅ MongoDB integration with Motor (async driver)
✅ Full CRUD operations for projects
✅ Delete confirmation dialog
✅ Real-time UI updates
✅ Error handling
✅ Loading states
✅ Star/favorite functionality
✅ Search functionality
✅ Logout functionality

## Troubleshooting

### Backend won't start
- Make sure MongoDB is running
- Check if port 8000 is available
- Verify all dependencies are installed

### Frontend can't connect to backend
- Make sure backend is running on port 8000
- Check browser console for CORS errors
- Verify API_URL in dashboard.jsx matches backend URL

### Database connection fails
- Check MongoDB is running: `mongosh` (MongoDB shell)
- Verify connection string in `.env` file
- For MongoDB Atlas, whitelist your IP address

## Database Structure

### Collection: `projects`
```json
{
  "_id": ObjectId,
  "name": "string",
  "date": "string",
  "sourceCount": 0,
  "starred": false,
  "createdAt": "ISO timestamp"
}
```

## Next Steps

- Add user authentication with JWT tokens
- Add project details/content management
- Add file upload for sources
- Add collaboration features
- Add project sharing
