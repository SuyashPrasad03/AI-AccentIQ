# Troubleshooting

## Upload Issues

### "File is too large"
Maximum upload size is 50 MB. Try compressing your audio or recording a shorter clip (15-45 seconds).

### "Recording is too short / too long"
Recordings must be between 15 and 45 seconds. The app checks duration both client-side (for instant feedback) and server-side (authoritative).

### "Unsupported file type"
The app accepts: WAV, MP3, MP4/M4A, OGG, FLAC, WebM. It verifies the actual file content, not just the extension — renaming a PDF to .mp3 won't work.

### "Quota exceeded"
Anonymous users get 3 free analyses. Register with your email to get unlimited access.

## Processing Issues

### "Analysis is taking a long time"
Processing typically takes 15-30 seconds. On the free tier, the server may have a cold start delay of up to 60 seconds on the first request. This is normal.

### "Transcription failed"
This can happen with very noisy recordings, completely silent audio, or corrupted files. Try recording again in a quieter environment.

## Account Issues

### "OTP code expired"
Verification codes expire after 10 minutes. Request a new one from the registration screen.

### "Too many verification codes requested"
There's a rate limit of 5 OTP requests per email per hour. Wait an hour before trying again.

### "Invalid email or password"
Double-check your email spelling. Passwords are case-sensitive. If you've forgotten your password, you'll need to register again (password reset coming in a future update).

## Browser Issues

### Microphone not working
Make sure you've granted microphone permissions to the site. Check your browser's address bar for a microphone icon and ensure it's set to "Allow."

### Page not loading
Try clearing your browser cache or using an incognito window. The app requires a modern browser (Chrome, Firefox, Safari, Edge — latest versions).
