# Admin System Setup & User Guide

## 🎉 What's Been Added

A complete admin system with:
- ✅ Separate admin authentication (username/password)
- ✅ Admin dashboard with statistics
- ✅ User management (view, activate/deactivate, delete)
- ✅ Role-based access (admin and superadmin)
- ✅ Protected admin routes
- ✅ Beautiful admin UI

---

## 🚀 Backend Setup

### 1. Install Dependencies

First, make sure you have `passlib` and `bcrypt` installed for password hashing:

```bash
cd login
pip install passlib[bcrypt]
```

### 2. Update Database Schema

The `Admin` model has been added to the database. Run the application to create the new table:

```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8182
```

The admin table will be created automatically on startup.

### 3. Create Your First Admin Account

Run the setup script to create your initial admin account:

```bash
cd login
python create_admin.py
```

You'll be prompted to enter:
- **Username** (e.g., `admin`)
- **Email** (e.g., `admin@skillscope.com`)
- **Full Name** (optional)
- **Password** (make it secure!)

The first admin created is automatically a **superadmin** with full privileges.

Example:
```
==================================================
CREATE INITIAL ADMIN ACCOUNT
==================================================
Enter admin username: admin
Enter admin email: admin@skillscope.com
Enter admin full name (optional): System Administrator
Enter admin password: ********
Confirm password: ********

==================================================
✅ ADMIN ACCOUNT CREATED SUCCESSFULLY!
==================================================
Username: admin
Email: admin@skillscope.com
Full Name: System Administrator
Role: Superadmin

You can now login at: http://localhost:3000/admin/login
==================================================
```

---

## 🎨 Frontend Setup

### 1. Start the Development Server

```bash
cd NewFrontend
npm run dev
```

### 2. Access Admin Portal

Navigate to: **http://localhost:8080/admin/login**

---

## 📊 Admin Features

### 1. **Admin Login**
- URL: `/admin/login`
- Separate authentication from regular OAuth users
- Username/password based
- JWT token with admin flags

### 2. **Dashboard Statistics**
- **Total Users**: All registered OAuth users
- **Total Candidates**: Users who completed analysis
- **Active Analyses**: Analyses in last 7 days
- **Pending Processing**: CVs awaiting processing
- **Recent Registrations**: New users in last 7 days

### 3. **User Management**
- View all users with pagination
- Search users by name or email
- View user details
- **Toggle Status**: Activate/deactivate user accounts
- **Delete Users**: Remove user accounts (superadmin only)

### 4. **Role-Based Access**
| Feature | Admin | Superadmin |
|---------|-------|------------|
| View Dashboard | ✅ | ✅ |
| View Users | ✅ | ✅ |
| Toggle User Status | ✅ | ✅ |
| Delete Users | ❌ | ✅ |
| Create Admins | ❌ | ✅ |
| View All Admins | ❌ | ✅ |

---

## 🔐 API Endpoints

### Authentication

#### **POST /admin/login**
Login with admin credentials.

**Request:**
```json
{
  "username": "admin",
  "password": "your-password"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "admin": {
    "id": 1,
    "username": "admin",
    "email": "admin@skillscope.com",
    "full_name": "System Administrator",
    "is_superadmin": true,
    "is_active": true
  }
}
```

#### **GET /admin/me**
Get current admin information (requires admin token).

---

### Dashboard

#### **GET /admin/dashboard/stats**
Get dashboard statistics (requires admin token).

**Response:**
```json
{
  "total_users": 150,
  "total_candidates": 89,
  "active_analyses": 23,
  "pending_processing": 5,
  "recent_registrations": 12
}
```

---

### User Management

#### **GET /admin/users**
Get all users with pagination and search.

**Query Parameters:**
- `skip`: Pagination offset (default: 0)
- `limit`: Results per page (default: 50)
- `search`: Search by email or name

**Response:**
```json
{
  "success": true,
  "total": 150,
  "skip": 0,
  "limit": 50,
  "users": [
    {
      "id": 1,
      "email": "user@example.com",
      "name": "John Doe",
      "provider": "google",
      "is_active": true,
      "created_at": "2026-03-01T10:00:00",
      "last_login": "2026-03-07T15:30:00"
    }
  ]
}
```

#### **GET /admin/users/{user_id}**
Get detailed user information.

#### **PATCH /admin/users/{user_id}/toggle-active**
Activate or deactivate a user account.

#### **DELETE /admin/users/{user_id}**
Delete a user account (superadmin only).

---

### Admin Management (Superadmin Only)

#### **POST /admin/admins**
Create a new admin account.

**Request:**
```json
{
  "username": "newadmin",
  "email": "newadmin@skillscope.com",
  "password": "securepassword",
  "full_name": "New Admin",
  "is_superadmin": false
}
```

#### **GET /admin/admins**
Get all admin accounts (superadmin only).

---

## 🛡️ Security Features

### 1. **Password Hashing**
- Uses `bcrypt` with automatic salt generation
- Passwords are never stored in plain text

### 2. **JWT Token Authentication**
- Admin tokens include `is_admin` flag
- Regular user tokens cannot access admin routes
- Token expiration configurable via settings

### 3. **Role-Based Access Control**
- Admin middleware checks for valid admin token
- Superadmin-only routes verify `is_superadmin` flag

### 4. **Protected Routes**
- All admin endpoints require authentication
- Invalid or expired tokens return 401 Unauthorized
- Inactive admin accounts cannot access system

---

## 🎯 Usage Flow

### For Admins:

1. **Login**
   - Navigate to `/admin/login`
   - Enter username and password
   - Redirected to dashboard

2. **View Statistics**
   - Dashboard shows real-time stats
   - Monitor system usage and growth

3. **Manage Users**
   - Search for specific users
   - View detailed user profiles
   - Activate/deactivate accounts as needed

4. **Monitor Activity**
   - Track recent registrations
   - See active analyses
   - Identify pending processing tasks

### For Superadmins:

All admin features PLUS:
- Delete user accounts
- Create new admin accounts
- View all admin accounts
- Full system control

---

## 🔧 Configuration

### Environment Variables

Add to your `.env` file:

```env
# Admin Configuration
ADMIN_DEFAULT_PASSWORD=changeme123  # Only for development
```

### Token Expiration

Default: 60 minutes (configurable in `config.py`):

```python
ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
```

---

## 📝 Database Schema

### Admin Table

```sql
CREATE TABLE admins (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    is_superadmin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL
);
```

---

## 🐛 Troubleshooting

### Issue: "Admin table does not exist"

**Solution:**
```bash
# Restart the backend server to create tables
cd login
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8182
```

### Issue: "Invalid username or password"

**Solution:**
- Verify credentials are correct
- Check if admin account exists: Run `python create_admin.py` again
- If you forgot password, recreate admin in database

### Issue: "Session expired" on dashboard

**Solution:**
- Token may have expired (60 min default)
- Login again at `/admin/login`
- Token stored in `localStorage` as `admin_token`

### Issue: "Only superadmins can..."

**Solution:**
- Regular admins cannot perform certain actions
- Need superadmin account for:
  - Deleting users
  - Creating admins
  - Viewing all admins

---

## 🚀 Next Steps

### Recommended Enhancements:

1. **Activity Logging**
   - Track admin actions
   - Audit trail for user changes

2. **Advanced Analytics**
   - User growth charts
   - Analysis completion rates
   - Provider breakdown

3. **Bulk Operations**
   - Batch user activation/deactivation
   - Export user data to CSV

4. **Email Notifications**
   - Notify admins of system events
   - Alert users of account status changes

5. **Admin Settings**
   - Change password
   - Update profile
   - Two-factor authentication

---

## 📞 Support

For issues or questions:
1. Check the troubleshooting section
2. Review API endpoint documentation
3. Check browser console for frontend errors
4. Check terminal for backend errors

---

## ✅ Checklist

- [ ] Backend dependencies installed (`passlib[bcrypt]`)
- [ ] Database tables created (run server once)
- [ ] Initial admin account created (`python create_admin.py`)
- [ ] Backend running on port 8182
- [ ] Frontend running on port 3000
- [ ] Admin login accessible at `/admin/login`
- [ ] Successfully logged in and viewing dashboard

**Congratulations! Your admin system is ready! 🎉**
