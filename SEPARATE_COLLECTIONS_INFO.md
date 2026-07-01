# Separate Collections for Admin and User Projects

## Overview
User projects and admin projects are now stored in **completely separate MongoDB collections**, ensuring total data isolation.

---

## Database Structure

### Database: `notebook_db`

#### Collection 1: `projects` (Admin Projects)
- Stores all admin projects
- Accessed via `/projects` API endpoints
- No `type` field needed

**Example Document:**
```json
{
  "_id": ObjectId("..."),
  "name": "Admin Project 1",
  "date": "Dec 15, 2024",
  "sourceCount": 5,
  "starred": true,
  "createdAt": "2024-12-15T10:30:00.000Z"
}
```

#### Collection 2: `user_projects` (User Projects)
- Stores all user projects
- Accessed via `/user-projects` API endpoints
- Completely separate from admin collection

**Example Document:**
```json
{
  "_id": ObjectId("..."),
  "name": "User Project 1",
  "date": "Dec 15, 2024",
  "sourceCount": 3,
  "starred": false,
  "userId": "Guest User",
  "createdAt": "2024-12-15T10:30:00.000Z"
}
```

---

## Benefits of Separate Collections

✅ **Complete Data Isolation**
- Admin projects cannot interfere with user projects
- User projects cannot interfere with admin projects
- Better security and organization

✅ **Independent Scaling**
- Each collection can be optimized independently
- Different indexing strategies can be applied
- Easier to manage and backup

✅ **Cleaner Queries**
- No need for `type` filters
- Simpler and faster database queries
- Reduced complexity in code

✅ **Better Performance**
- Smaller collections = faster queries
- No need to filter by type
- More efficient indexing

---

## API Endpoints

### Admin Endpoints (Collection: `projects`)
```
GET    /projects           → Fetch all admin projects
POST   /projects           → Create admin project
PUT    /projects/{id}      → Update admin project
DELETE /projects/{id}      → Delete admin project
```

### User Endpoints (Collection: `user_projects`)
```
GET    /user-projects      → Fetch all user projects
POST   /user-projects      → Create user project
PUT    /user-projects/{id} → Update user project
DELETE /user-projects/{id} → Delete user project
```

---

## Backend Configuration

### MongoDB Collections Setup:
```python
# MongoDB Client
client = AsyncIOMotorClient(MONGODB_URL)
db = client[DATABASE_NAME]

# Two separate collections
projects_collection = db["projects"]              # Admin projects
user_projects_collection = db["user_projects"]    # User projects
```

---

## How to View Collections in MongoDB

### Using MongoDB Compass:
1. Open MongoDB Compass
2. Connect to your database
3. You'll see:
   - `projects` collection (admin)
   - `user_projects` collection (user)

### Using MongoDB Shell (mongosh):
```bash
# Connect to MongoDB
mongosh "your-connection-string"

# Switch to database
use notebook_db

# View admin projects
db.projects.find()

# View user projects
db.user_projects.find()

# Count documents
db.projects.countDocuments()
db.user_projects.countDocuments()
```

### Using MongoDB Atlas:
1. Go to your cluster
2. Click "Browse Collections"
3. Select `notebook_db` database
4. You'll see both collections

---

## Migration Notes

If you had existing projects with `type` field:

### Option 1: Clean Start (Recommended)
- Delete old data
- Restart with fresh collections
- Backend will create collections automatically

### Option 2: Migrate Existing Data
Run this in MongoDB shell:
```javascript
// Connect to database
use notebook_db

// Move admin projects
db.projects.find({type: "admin"}).forEach(doc => {
  delete doc.type;
  db.projects.insertOne(doc);
});

// Move user projects to new collection
db.projects.find({type: "user"}).forEach(doc => {
  delete doc.type;
  db.user_projects.insertOne(doc);
});

// Delete old mixed data (optional)
db.projects.deleteMany({type: {$exists: true}});
```

---

## Testing

### Test Admin Collection:
1. Login as admin
2. Create a project
3. Check MongoDB:
   ```bash
   use notebook_db
   db.projects.find()
   ```
4. Should see your project in `projects` collection

### Test User Collection:
1. Login as user
2. Create a project
3. Check MongoDB:
   ```bash
   use notebook_db
   db.user_projects.find()
   ```
4. Should see your project in `user_projects` collection

### Verify Separation:
```bash
# Count admin projects
db.projects.countDocuments()

# Count user projects
db.user_projects.countDocuments()

# Both should be independent
```

---

## Collection Statistics

View collection info:
```javascript
// Admin projects stats
db.projects.stats()

// User projects stats
db.user_projects.stats()
```

---

## Indexing (Optional - For Better Performance)

Add indexes for better search performance:

```javascript
// Admin projects indexes
db.projects.createIndex({ "name": "text" })
db.projects.createIndex({ "starred": 1 })
db.projects.createIndex({ "createdAt": -1 })

// User projects indexes
db.user_projects.createIndex({ "name": "text" })
db.user_projects.createIndex({ "userId": 1 })
db.user_projects.createIndex({ "starred": 1 })
db.user_projects.createIndex({ "createdAt": -1 })
```

---

## Backup and Restore

### Backup Admin Projects:
```bash
mongodump --collection=projects --db=notebook_db --out=backup/
```

### Backup User Projects:
```bash
mongodump --collection=user_projects --db=notebook_db --out=backup/
```

### Restore:
```bash
mongorestore --collection=projects --db=notebook_db backup/notebook_db/projects.bson
mongorestore --collection=user_projects --db=notebook_db backup/notebook_db/user_projects.bson
```

---

## Summary

| Aspect | Admin | User |
|--------|-------|------|
| **Collection** | `projects` | `user_projects` |
| **API Path** | `/projects` | `/user-projects` |
| **Dashboard** | `/dashboard` | `/user-dashboard` |
| **Theme** | Purple | Green/Blue |
| **Isolation** | ✅ Complete | ✅ Complete |

---

## Restart Backend

After this change, restart your backend:
```bash
cd backend
python -m uvicorn main:app --reload --port 8000
```

The collections will be created automatically when you create the first project in each dashboard!

---

✅ **Done!** Your data is now completely separated in different MongoDB collections.
