# Fix npm install Errors - NewFrontend

**Issue:** EBUSY errors with esbuild on Windows + OneDrive  
**Date:** March 5, 2026

---

## 🔧 Quick Fix (Try These in Order)

### Solution 1: Clean Install (Recommended)

```powershell
# 1. Stop any running dev servers (Ctrl+C in all terminals)

# 2. Delete node_modules and lock files
cd NewFrontend
Remove-Item -Recurse -Force node_modules -ErrorAction SilentlyContinue
Remove-Item -Force package-lock.json -ErrorAction SilentlyContinue

# 3. Clear npm cache
npm cache clean --force

# 4. Reinstall
npm install
```

### Solution 2: Pause OneDrive Sync

OneDrive can lock files during sync causing EBUSY errors:

1. **Right-click OneDrive icon in system tray**
2. Click **Pause syncing** → **2 hours**
3. Run the clean install commands above
4. Resume OneDrive sync after successful install

### Solution 3: Close File Locks

```powershell
# Find and stop Node processes
Get-Process node -ErrorAction SilentlyContinue | Stop-Process -Force

# Try install again
npm install
```

### Solution 4: Use Alternative Package Manager

If npm keeps failing, try **pnpm** (faster and handles locks better):

```powershell
# Install pnpm globally
npm install -g pnpm

# Use pnpm instead
cd NewFrontend
pnpm install
```

---

## 🚀 Running the Frontend

Once installed successfully:

### Development Mode

```powershell
# Using npm
npm run dev

# Using pnpm
pnpm dev

# The app will start at http://localhost:5173 (or next available port)
```

### Build for Production

```powershell
# Build
npm run build

# Preview production build
npm run preview
```

---

## ⚙️ Update API Configuration

Before running, ensure the frontend points to your unified backend:

**File:** `src/config/api.ts`

```typescript
// Update base URLs to unified backend
const API_BASE_URL = 'http://localhost:8000';

export const API_ENDPOINTS = {
  // Recommendations
  RECOMMENDATIONS: `${API_BASE_URL}/recommendations`,
  
  // Agent Runtime
  AGENT_RUNTIME: `${API_BASE_URL}/agent-runtime`,
  
  // Authentication
  AUTH: `${API_BASE_URL}/auth`,
  CANDIDATE: `${API_BASE_URL}/candidate`,
  
  // Interview
  INTERVIEW: `${API_BASE_URL}/interview`,
  
  // Skills Validation
  SKILLS_VALIDATION: `${API_BASE_URL}/skills-validation`,
};
```

---

## 🔍 Troubleshooting

### Error: "Port 5173 already in use"

```powershell
# Find process using port 5173
Get-Process -Id (Get-NetTCPConnection -LocalPort 5173).OwningProcess

# Kill the process
Stop-Process -Id <PROCESS_ID> -Force
```

### Error: "Cannot find module '@vitejs/plugin-react'"

```powershell
# Reinstall dependencies
Remove-Item -Recurse -Force node_modules
npm install
```

### Error: "CORS policy: No 'Access-Control-Allow-Origin'"

**Backend is not running!** Start the unified backend first:

```powershell
# In a separate PowerShell window
cd merge-backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

---

## 📋 Complete Startup Checklist

### Step 1: Start Backend (Terminal 1)

```powershell
cd merge-backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Verify:** Open http://localhost:8000/docs (Swagger UI)

### Step 2: Start Frontend (Terminal 2)

```powershell
cd NewFrontend

# If first time or after errors:
Remove-Item -Recurse -Force node_modules -ErrorAction SilentlyContinue
npm cache clean --force
npm install

# Run dev server
npm run dev
```

**Verify:** Open http://localhost:5173

### Step 3: Test Integration

1. Open frontend: http://localhost:5173
2. Click "Login" to test OAuth
3. Navigate to different modules
4. Check browser console for API errors

---

## 🛠️ Alternative: Use Yarn

If npm continues to fail:

```powershell
# Install Yarn globally
npm install -g yarn

# Use Yarn instead
cd NewFrontend
yarn install
yarn dev
```

---

## 📦 Package Manager Comparison

| Manager | Speed | Lock Handling | Recommendation |
|---------|-------|---------------|----------------|
| **npm** | Moderate | Poor on Windows | ✓ Default |
| **pnpm** | Fast | Excellent | ✓✓ Best for OneDrive |
| **yarn** | Fast | Good | ✓ Alternative |

---

## 🎯 Expected Output (Success)

```powershell
PS> npm install

added 1234 packages in 45s

PS> npm run dev

VITE v5.x.x  ready in 500 ms

➜  Local:   http://localhost:5173/
➜  Network: use --host to expose
➜  press h + enter to show help
```

---

## 🔗 Related Files

- **Backend API:** [merge-backend/main.py](../merge-backend/main.py)
- **API Config:** [src/config/api.ts](src/config/api.ts)  
- **Package Info:** [package.json](package.json)
- **Vite Config:** [vite.config.ts](vite.config.ts)

---

## 💡 Tips to Avoid Future Issues

1. **Don't sync node_modules to OneDrive**  
   Add to `.gitignore` (already done):
   ```
   node_modules/
   dist/
   .vite/
   ```

2. **Close VS Code when reinstalling**  
   VS Code can lock files during TypeScript checks

3. **Use one package manager**  
   Don't mix npm, yarn, and pnpm in same project

4. **Keep Node.js updated**  
   Current version: v24.12.0 ✓

---

**Need More Help?**

Check the error log:
```powershell
type C:\Users\Admin\AppData\Local\npm-cache\_logs\2026-03-05T17_17_37_790Z-debug-0.log
```
