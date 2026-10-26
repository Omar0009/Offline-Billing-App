# Offline-Billing-App
Its an offline billng app that can generate directly into pdf which specifically made for Green Source BD/EXE Bangladesh which is a solar company.Lang used python.
Run this script first
/usr/local/bin/python3 -m pip install reportlab
#for data visualization
code:& "C:\Users\Omar DP\.local\bin\python3.15.exe" -m pip install matplotlib --break-system-packages
or for Mac code:pip3 install reportlab num2words matplotlib pyinstaller
/usr/local/bin/python3 "/Users/omar/Desktop/Billing App/Billing App.py"
To run the app on Mac: 
pyinstaller --onefile --noconsole billingapp.py

For windows:
cd "C:\Users\Omar DP\Desktop\App" #Omar DP is user account which depends on your pc
python billingapp.py

To make the it exe :
python -m PyInstaller --onefile --noconsole billingapp.py
