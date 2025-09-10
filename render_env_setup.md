# Render Environment Variables Setup

To fix the MongoDB connection issue on Render, you need to set the following environment variables in your Render dashboard:

## Required Environment Variables

1. **MONGODB_URI**
   ```
   mongodb+srv://sanjayvarmacol2:Sanjay1234@cluster01.inf1rib.mongodb.net/?retryWrites=true&w=majority&appName=Cluster01&tls=true&tlsAllowInvalidCertificates=false
   ```
   
   **Alternative (if still having issues):**
   ```
   mongodb+srv://sanjayvarmacol2:Sanjay1234@cluster01.inf1rib.mongodb.net/policiesdb?retryWrites=true&w=majority&appName=Cluster01&ssl=true&authSource=admin
   ```

2. **DB_NAME**
   ```
   policiesdb
   ```

3. **HOST**
   ```
   0.0.0.0
   ```

4. **PORT**
   ```
   10000
   ```

5. **DEBUG**
   ```
   False
   ```

## How to Set Environment Variables in Render

1. Go to your Render dashboard
2. Select your backend service
3. Go to the "Environment" tab
4. Add each environment variable with its value
5. Click "Save Changes"
6. Redeploy your service

## Additional MongoDB Atlas Configuration

Make sure your MongoDB Atlas cluster allows connections from Render's IP addresses:

1. Go to MongoDB Atlas dashboard
2. Navigate to "Network Access"
3. Add IP address `0.0.0.0/0` (allow all IPs) or add Render's specific IP ranges
4. Make sure your database user has proper permissions

## Troubleshooting

If you still get SSL errors, try these alternative MongoDB URI formats:

**Option 1 (with explicit SSL parameters):**
```
mongodb+srv://sanjayvarmacol2:Sanjay1234@cluster01.inf1rib.mongodb.net/policiesdb?retryWrites=true&w=majority&appName=Cluster01&ssl=true&authSource=admin
```

**Option 2 (with different SSL settings):**
```
mongodb+srv://sanjayvarmacol2:Sanjay1234@cluster01.inf1rib.mongodb.net/policiesdb?retryWrites=true&w=majority&appName=Cluster01&tls=true&tlsAllowInvalidCertificates=true
```

The code has been updated to handle these connection issues more robustly with retry logic and better error handling.
