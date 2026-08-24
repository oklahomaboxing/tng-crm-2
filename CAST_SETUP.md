# TNG Google Cast setup

After registering the TNG Custom Web Receiver in the Google Cast SDK Developer Console,
set this DigitalOcean frontend environment variable:

VITE_CAST_APP_ID=YOUR_GOOGLE_CAST_APPLICATION_ID

Receiver URL:
https://tngos.tngboxinggym.com/tng-cast-receiver.html

The Cast picker only appears on supported sender platforms/browsers.
A native iOS sender app is still required for the most reliable iPhone Cast device-picker experience.
