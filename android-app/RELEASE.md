# Android Release

Use Android Studio to generate release builds for Media Flow Android.

## Debug APK

For local testing:

```powershell
.\gradlew.bat :app:assembleDebug
```

Output:

```text
app/build/outputs/apk/debug/app-debug.apk
```

## Release AAB

For Google Play, create a signed Android App Bundle:

1. Open `android-app/` in Android Studio.
2. Select **Build > Generate Signed Bundle / APK**.
3. Choose **Android App Bundle**.
4. Create or select a signing key.
5. Choose the `release` variant.
6. Generate the bundle.

Output:

```text
app/build/outputs/bundle/release/app-release.aab
```

## Versioning

Before each release, update these values in `app/build.gradle`:

```gradle
versionCode 1
versionName "1.0.0"
```

Increase `versionCode` for every Play Store upload.

## Native Library Compatibility

The project uses:

```gradle
com.moizhassan.ffmpeg:ffmpeg-kit-16kb:6.0.0
```

This avoids the Android 15+ 16 KB page-size warning caused by the retired
official FFmpegKit packages.
