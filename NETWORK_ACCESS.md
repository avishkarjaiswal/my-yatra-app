# Network Access Instructions

## ✅ Server Configuration Complete!

Your Flask server has been configured to accept connections from other devices on your local network.

### Changes Made:
- Modified `app.py` to run on `host='0.0.0.0'` (all network interfaces)
- Port: `5000` (default Flask port)

---

## 🌐 How to Access from Other Devices

### Your Computer's Local IP Address:
**192.168.1.6**

### On Other Devices (Phone, Tablet, Other Computer):

1. **Make sure the device is connected to the SAME Wi-Fi network** as your computer

2. **Open a web browser** on the other device

3. **Enter one of these URLs:**
   ```
   http://192.168.1.6:5000
   ```

### Example URLs for Different Pages:
- Home Page: `http://192.168.1.6:5000/`
- Register: `http://192.168.1.6:5000/register`
- Gallery: `http://192.168.1.6:5000/catalog`
- Admin: `http://192.168.1.6:5000/admin/login`

---

## 🔄 Restarting the Server

**You need to restart the Flask server** for the changes to take effect:

1. Press `CTRL + C` in the terminal running `python app.py`
2. Run the command again: `python app.py`
3. You should see output like:
   ```
   * Running on all addresses (0.0.0.0)
   * Running on http://127.0.0.1:5000
   * Running on http://192.168.1.6:5000
   ```

---

## 🔒 Important Security Notes:

1. **Firewall:** Windows Firewall may block incoming connections. If other devices can't connect, you may need to:
   - Allow Python through Windows Firewall
   - Or temporarily disable firewall for testing (not recommended for production)

2. **Same Network Only:** This setup only works on your local network. Devices must be connected to the same Wi-Fi router.

3. **Development Only:** This configuration is for development/testing. For production deployment, use a proper web server (like Gunicorn with Nginx).

---

## 🛠️ Troubleshooting:

### If other devices can't connect:

1. **Check Windows Firewall:**
   - Search for "Windows Defender Firewall"
   - Click "Allow an app through firewall"
   - Find Python and check both Private and Public boxes

2. **Verify your IP hasn't changed:**
   - Run: `ipconfig | findstr /i "IPv4"`
   - Use the current IPv4 address

3. **Verify server is running:**
   - Check the terminal for errors
   - Make sure you see "Running on http://192.168.1.6:5000"

4. **Test from your own computer first:**
   - Try accessing `http://192.168.1.6:5000` on your PC
   - If it works locally, the issue is with network/firewall

---

## 📱 Testing:

1. Restart the Flask server
2. On your phone/tablet, connect to the same Wi-Fi
3. Open browser and go to: `http://192.168.1.6:5000`
4. You should see the Dwarka Yatra website!

---

**Note:** Your IP address may change if your router assigns new addresses. If the connection stops working, check your IP again with `ipconfig`.
