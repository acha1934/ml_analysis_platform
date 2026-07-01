# User Dashboard Setup - Complete Guide

## Overview
You now have **TWO separate dashboards**:
1. **Admin Dashboard** - Purple theme (for admins)
2. **User Dashboard** - Green/Blue theme (for regular users)

Both dashboards use "Projects" terminology instead of "Notebooks".

---

## Features

### Admin Dashboard (`/dashboard`)
- **Color Theme**: Purple gradient (#667eea to #764ba2)
- **Icon**: 📓
- **Title**: "Admin Projects"
- **Access**: Requires password `admin123`
- **Features**:
  - Create/Edit/Delete projects
  - Star/Favorite projects
  - Search projects
  - Beautiful glass-morphism UI
  - Delete confirmation dialog
  - MongoDB integration

### User Dashboard (`/user-dashboard`)
- **Color Theme**: Green/Blue gradient (#43cea2 to #185a9d)
- **Icon**: 💼
- **Title**: "My Projects"
- **Access**: No password required ("Continue as User")
- **Features**:
  - Same functionality as Admin Dashboard
  - Different visual theme
  - Welcome message with username
  - Separate project storage
  - Uses "files" instead of "sources" in metadata

---

## How to Access

### Admin Access:
1. Go to login page
2. Enter password: `admin123`
3. Click "Admin Login"
4. Redirects to `/dashboard` (Purple theme)

### User Access:
1. Go to login page
2. Click "Continue as User"
3. Redirects to `/user-dashboard` (Green theme)

---

## Database Structure

### Admin Projects
```json
{
  "_id": ObjectId,
  "name": "Project Name",
  "date": "Dec 15, 2024",
  "sourceCount": 0,
  "starred": false,
  "type": "admin",
  "createdAt": "ISO timestamp"
}
```

### User Projects
```json
{
  "_id": ObjectId,
  "name": "Project Name",
  "date": "Dec 15, 2024",
  "sourceCount": 0,
  "starred": false,
  "type": "user",
  "userId": "Guest User",
  "createdAt": "ISO timestamp"
}
```

---

## API Endpoints

### Admin Endpoints
- `GET /projects` - Get all admin projects
- `POST /projects` - Create admin project
- `PUT /projects/{id}` - Update admin project
- `DELETE /projects/{id}` - Delete admin project

### User Endpoints
- `GET /user-projects` - Get all user projects
- `POST /user-projects` - Create user project
- `PUT /user-projects/{id}` - Update user project
- `DELETE /user-projects/{id}` - Delete user project

---

## File Structure

```
frontend/src/
├── pages/
│   ├── login.jsx              # Login page
│   ├── dashboard.jsx          # Admin dashboard
│   └── userDashboard.jsx      # User dashboard (NEW)
├── styles/
│   ├── Login.css              # Login styles
│   ├── dashboard.css          # Admin dashboard styles
│   └── userDashboard.css      # User dashboard styles (NEW)
└── App.jsx                    # Routes configuration

backend/
└── main.py                    # API with separate admin/user endpoints
```

---

## Key Differences

| Feature | Admin Dashboard | User Dashboard |
|---------|----------------|----------------|
| **Route** | `/dashboard` | `/user-dashboard` |
| **Theme** | Purple | Green/Blue |
| **Icon** | 📓 | 💼 |
| **Title** | Admin Projects | My Projects |
| **Password** | Required | Not Required |
| **API** | `/projects` | `/user-projects` |
| **Database Type** | `type: "admin"` | `type: "user"` |
| **Metadata** | "sources" | "files" |

---

## Running the Application

### 1. Start Backend:
```bash
cd backend
python -m uvicorn main:app --reload --port 8000
```

### 2. Start Frontend:
```bash
cd frontend
npm run dev
```

### 3. Open Browser:
```
http://localhost:5173
```

---

## What Changed from NotebookLM

✅ Changed "Notebooks" → "Projects" everywhere
✅ Changed "New notebook" → "New Project"
✅ Changed "Your notebooks" → "Your Projects"
✅ Changed "Delete notebook?" → "Delete project?"
✅ Admin dashboard title: "Admin Projects"
✅ User dashboard title: "My Projects"
✅ Created separate user dashboard with different theme
✅ Added user/admin project separation in database

---

## Testing

### Test Admin Flow:
1. Login with password: `admin123`
2. Should see purple dashboard
3. Create a new project
4. Check MongoDB - should have `type: "admin"`

### Test User Flow:
1. Click "Continue as User"
2. Should see green/blue dashboard
3. Create a new project
4. Check MongoDB - should have `type: "user"`

### Verify Separation:
- Admin projects should NOT appear in user dashboard
- User projects should NOT appear in admin dashboard
- Both can have projects with the same name

---

## Customization

### Change User Dashboard Colors:
Edit `frontend/src/styles/userDashboard.css`:
```css
background: linear-gradient(135deg, #YOUR_COLOR_1 0%, #YOUR_COLOR_2 100%);
```

### Change Admin Dashboard Colors:
Edit `frontend/src/styles/dashboard.css`:
```css
background: linear-gradient(135deg, #YOUR_COLOR_1 0%, #YOUR_COLOR_2 100%);
```

### Add Username Input for Users:
Currently users login as "Guest User". You can add a username input field on the login page for personalized experience.

---

## Next Steps

- Add user registration/authentication
- Add JWT tokens for secure authentication
- Add project sharing between users
- Add file upload functionality
- Add project collaboration features
- Add user profile management

---

Enjoy your dual-dashboard system! 🎉
